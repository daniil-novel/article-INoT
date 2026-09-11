"""Run the pinned SCC session with audited transport and isolated generated tests.

This adapter deliberately preserves upstream prompts, extraction and transitions.
It is a development integration, not a confirmatory experiment dispatcher.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from .. import codex_luna_subscription as cli
from ..record_codex_runtime import capture

HERE = Path(__file__).resolve().parent
VENDOR = HERE / 'vendor/scc_2024'
IMAGE = 'sha256:afeb8d78b76f6a7b1fbf427d78a55bd35dbfcf58387711b47f8a8ba00e16b580'
INSTRUCTIONS = (
    'Continue the supplied serialized conversation as its next assistant message. '
    'Honor the role instructions inside that conversation. Return only that message. '
    'Do not use tools, read local files, browse or delegate. '
    'Any execution feedback inside the conversation is supplied by the external workflow.'
)


class TransportAbort(BaseException):
    """Escape upstream broad Exception handlers without fabricating model output."""


def verify_vendor():
    manifest = cli.read(VENDOR / 'SOURCE_MANIFEST.json')
    for name, expected in manifest['files'].items():
        if hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Upstream source changed: ' + name)
    return manifest


def load_upstream():
    verify_vendor()
    # Upstream uses absolute imports. Never collide with a different host package.
    for name in ('core', 'roles', 'session', 'utils'):
        if name in sys.modules:
            path = Path(sys.modules[name].__file__).resolve()
            if not path.is_relative_to(VENDOR):
                raise ValueError('Conflicting upstream module: ' + name)
    sys.path.insert(0, str(VENDOR)) if str(VENDOR) not in sys.path else None
    return importlib.import_module('session'), importlib.import_module('core.interface')


def serialize_messages(messages):
    if not messages or any(set(m) != {'role', 'content'} or
                           m['role'] not in ('system', 'user', 'assistant') or
                           not isinstance(m['content'], str) for m in messages):
        raise ValueError('Unsupported upstream message surface')
    payload = 'CONVERSATION_JSON\n' + json.dumps(messages, ensure_ascii=False) + '\nNEXT_ASSISTANT_MESSAGE\n'
    if len(payload.encode('utf-8')) > 65536:
        raise TransportAbort('Full conversation exceeds byte guard; no shortening')
    return payload


def run_session(requirement, model_call, execute, max_round=2, before_func=''):
    upstream, interface = load_upstream()
    prompts = importlib.import_module('roles.rule_descriptions_actc')
    original_call, original_execute = interface.call_chatgpt, upstream.unsafe_execute
    interface.call_chatgpt = model_call
    upstream.unsafe_execute = execute
    try:
        session = upstream.Session(prompts.TEAM, prompts.ANALYST,
                                   prompts.PYTHON_DEVELOPER, prompts.TESTER,
                                   requirement, model=cli.MODEL, majority=1,
                                   max_round=max_round, before_func=before_func)
        return session.run_session()
    finally:
        interface.call_chatgpt = original_call
        upstream.unsafe_execute = original_execute


def docker_execute(folder, code, report):
    """Execute the original unsafe_execute inside Docker, never in the host."""
    verify_vendor()
    folder.mkdir(parents=True, exist_ok=False)
    cli.save(folder / 'input.json', {'code': code, 'report': report})
    # Only the execution-helper tail of the verified source is loaded in Docker.
    # Its original reliability guard and swallowed stdout remain unchanged.
    driver = (
        "import json,pathlib\n"
        "s=pathlib.Path('/upstream/session.py').read_text()\n"
        "ns={};exec('import contextlib\\n'+s.split('\\nimport contextlib\\n',1)[1],ns)\n"
        "p=json.loads(pathlib.Path('/input/input.json').read_text())\n"
        "result=ns['unsafe_execute'](p['code'],p['report'])\n"
        "print(json.dumps({'report':result}))\n"
    )
    name = 'scc-check-' + uuid.uuid4().hex[:16]
    command = ['docker', '--context', 'default', 'run', '--rm', '--name', name,
               '--network', 'none', '--read-only', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--user', '65532:65532',
               '--memory', '3g', '--cpus', '2', '--pids-limit', '256',
               '--tmpfs', '/tmp:rw,noexec,nosuid,size=512m',
               '--mount', f'type=bind,source={VENDOR},target=/upstream,readonly',
               '--mount', f'type=bind,source={folder.resolve()},target=/input,readonly',
               '--entrypoint', 'python', IMAGE, '-c', driver]
    cli.save(folder / 'argv.json', command)
    started = time.time()
    terminal = {'state': 'started', 'started_unix': started}
    cli.save(folder/'status.json', terminal)
    try:
        with (folder/'stdout.txt').open('xb') as out, (folder/'stderr.txt').open('xb') as err:
            result = subprocess.run(command, stdout=out, stderr=err, timeout=45)
        if result.returncode:
            raise TransportAbort('Generated-test container failed; inspect raw logs')
        data = cli.read(folder/'stdout.txt')
        if set(data) != {'report'} or not isinstance(data['report'], str):
            raise TransportAbort('Invalid generated-test response')
        terminal.update(state='completed', report=data['report'], exit_code=result.returncode)
        return data['report']
    except (Exception, TransportAbort) as exc:
        terminal.update(state='infrastructure_failure', reason=str(exc), exception_type=type(exc).__name__)
        raise TransportAbort(str(exc)) from exc
    finally:
        try:
            cleanup = subprocess.run(['docker', '--context', 'default', 'rm', '-f', name],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            terminal['cleanup_exit_code'] = cleanup.returncode
        except Exception as exc:
            terminal['cleanup_error'] = str(exc)
        terminal['finished_unix'] = time.time()
        cli.save(folder/'status.json', terminal)


def pilot(task, out, npm_root):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cli.save(out/'status.json', {'state':'initializing', 'task_id':task.get('task_id'),
                               'started_unix':time.time()})
    (out/'empty').mkdir()
    (out/'instructions.txt').write_text(INSTRUCTIONS, encoding='utf-8')
    manifest = verify_vendor()
    cli.save(out/'task.json', task)
    cli.save(out/'upstream.json', manifest)
    prefix = [shutil.which('node'), str(npm_root.resolve()/'node_modules/@openai/codex/bin/codex.js')]
    if not prefix[0]:
        raise ValueError('Node runtime unavailable')
    version = subprocess.check_output(prefix+['--version'], text=True).strip()
    if version != cli.CLI_VERSION:
        raise ValueError('Pinned CLI version unavailable')
    cli.save(out/'runtime.json', {'prefix': prefix, 'version': version})
    capture(out, npm_root, Path(__file__))
    cli.save(out/'transport_source.json', {'sha256': hashlib.sha256(Path(cli.__file__).read_bytes()).hexdigest()})
    command = cli.cli_command(prefix, out/'empty', out/'instructions.txt')
    calls, checks = [], []

    def model_call(messages, **kwargs):
        folder = out/'turns'/f'{len(calls):03d}'
        record = {'messages': copy.deepcopy(messages), 'upstream_kwargs': kwargs}
        calls.append(record)
        try:
            payload = serialize_messages(messages)
            result = cli.archive_turn(folder, command, payload, 600)
            cli.save(folder/'upstream_request.json', record)
            record['result'] = result
            return [result['final_text']]
        except Exception as exc:
            raise TransportAbort(str(exc)) from exc

    def execute(code, report):
        folder = out/'generated_tests'/f'{len(checks):03d}'
        checks.append(str(folder.relative_to(out)))
        return docker_execute(folder, code, report)

    try:
        code, history = run_session(task['prompt']+'\n'+task.get('context',''), model_call, execute)
        (out/'candidate.py').write_text(code, encoding='utf-8')
        cli.save(out/'session_history.json', history)
        status = {'state': 'completed', 'upstream_format_failure': code == 'error'}
    except TransportAbort as exc:
        status = {'state': 'paused', 'reason': str(exc)}
    except Exception as exc:
        status = {'state': 'infrastructure_failure', 'reason': str(exc),
                  'exception_type': type(exc).__name__}
    finally:
        cli.save(out/'requests.json', calls)
    status.update({'task_id': task['task_id'], 'calls_attempted': len(calls),
                   'generated_test_runs': checks, 'role': 'development only',
                   'known_api_equivalent_usd': sum(x['result']['api_equivalent_usd'] for x in calls if 'result' in x),
                   'unknown_usage_calls': sum('result' not in x for x in calls)})
    cli.save(out/'status.json', status)
    return status


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--npm-root', type=Path, default=Path('tmp/codex-runtime'))
    a = p.parse_args()
    preexisting = a.out.exists()
    try:
        status = pilot(cli.read(a.task), a.out, a.npm_root)
    except Exception as exc:
        # Initialization errors must also leave a terminal record, without
        # replacing an earlier attempt supplied by mistake.
        status_path = a.out/'status.json'
        if not preexisting and status_path.exists() and cli.read(status_path).get('state') == 'initializing':
            cli.save(status_path, {'state':'infrastructure_failure', 'reason':str(exc),
                                   'exception_type':type(exc).__name__})
        raise
    print(json.dumps(status))


if __name__ == '__main__':
    main()
