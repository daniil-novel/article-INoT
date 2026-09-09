"""Replay a completed SCC development archive using raw answers and test reports.

No model requests or execution of generated programs takes place during replay.
"""
import argparse
import hashlib
import json
from pathlib import Path

from . import scc
from .. import codex_luna_subscription as cli
from ..scale_env.validate_native import validate_native


def audit(folder):
    status = cli.read(folder/'status.json')
    if status['state'] != 'completed':
        raise ValueError('Incomplete development run; retain outside complete-run replay')
    if cli.read(folder/'upstream.json') != scc.verify_vendor():
        raise ValueError('Different upstream revision')
    provenance = cli.read(folder/'runtime_provenance.json')
    source = folder/'runner_source.py'
    # Published pilot predates failure-status hardening; its successful session
    # transitions, messages and extraction are unchanged and replayed below.
    pilot_v1_hash = '1e980509b9d81ca075e1a2df6aa81a691c05169bf3e5623e2549fdba6d42f389'
    if (hashlib.sha256(source.read_bytes()).hexdigest() != pilot_v1_hash and
            source.read_bytes() != Path(scc.__file__).read_bytes().replace(b'\r\n',b'\n')):
        raise ValueError('Replay adapter changed')
    if (folder/'instructions.txt').read_text(encoding='utf-8') != scc.INSTRUCTIONS:
        raise ValueError('Instructions changed')
    turns = sorted((folder/'turns').iterdir())
    if [p.name for p in turns] != [f'{i:03d}' for i in range(status['calls_attempted'])]:
        raise ValueError('Unexpected turn inventory')
    requests = cli.read(folder/'requests.json')
    if len(requests) != len(turns):
        raise ValueError('Request count differs')
    parsed = []
    for i, turn in enumerate(turns):
        raw = cli.parse_events((turn/'events.jsonl').read_bytes())
        stored = cli.read(turn/'result.json')
        if any(raw[k] != stored[k] for k in raw):
            raise ValueError('Stored result differs from raw response')
        if stored != requests[i]['result']:
            raise ValueError('Request resource record differs')
        for name, digest in stored['files_sha256'].items():
            if hashlib.sha256((turn/name).read_bytes()).hexdigest() != digest:
                raise ValueError('Turn evidence changed')
        prefix = cli.read(folder/'runtime.json')['prefix']
        # Original absolute runtime paths remain provenance, even after publication.
        argv = cli.read(turn/'argv.json')
        empty = Path(provenance['empty_working_directory'])
        instructions = Path(provenance['instructions_path'])
        if argv != cli.cli_command(prefix, empty, instructions):
            raise ValueError('CLI treatment differs')
        parsed.append(raw)
    call_index, check_index = 0, 0
    checks = sorted((folder/'generated_tests').iterdir()) if (folder/'generated_tests').exists() else []

    def model_call(messages, **kwargs):
        nonlocal call_index
        turn = turns[call_index]
        expected = {'messages': messages, 'upstream_kwargs': kwargs}
        if cli.read(turn/'upstream_request.json') != expected:
            raise ValueError('Upstream request differs on replay')
        if (turn/'prompt.txt').read_text(encoding='utf-8') != scc.serialize_messages(messages):
            raise ValueError('Serialized messages differ')
        answer = parsed[call_index]['final_text']
        call_index += 1
        return [answer]

    def execute(code, report):
        nonlocal check_index
        check = checks[check_index]
        if cli.read(check/'input.json') != {'code': code, 'report': report}:
            raise ValueError('Generated-test input differs on replay')
        data = cli.read(check/'stdout.txt')
        if data['report'] != cli.read(check/'status.json')['report']:
            raise ValueError('Generated-test feedback differs')
        check_index += 1
        return data['report']

    task = cli.read(folder/'task.json')
    code, history = scc.run_session(task['prompt']+'\n'+task.get('context',''), model_call, execute)
    if code != (folder/'candidate.py').read_text(encoding='utf-8') or history != cli.read(folder/'session_history.json'):
        raise ValueError('Final candidate/session differs from native upstream replay')
    if call_index != len(turns) or check_index != len(checks):
        raise ValueError('Unconsumed evidence')
    valuation = sum(x['api_equivalent_usd'] for x in parsed)
    if abs(valuation-status['known_api_equivalent_usd']) > 1e-12 or status['unknown_usage_calls']:
        raise ValueError('Cost accounting differs')
    return {'task_id':task['task_id'], 'model_calls':len(turns), 'generated_test_runs':len(checks),
            'input_tokens':sum(x['usage']['input_tokens'] for x in parsed),
            'cached_input_tokens':sum(x['usage']['cached_input_tokens'] for x in parsed),
            'output_tokens':sum(x['usage']['output_tokens'] for x in parsed),
            'api_equivalent_usd':valuation, 'upstream_replay':'matched',
            'quality':'requires separate native report'}


def audit_pilot(root):
    selection = cli.read(root/'native-preparation/selection.json')
    ids = selection['assigned_task_ids']
    if ids != ['BigCodeBench/325','BigCodeBench/322','BigCodeBench/1036']:
        raise ValueError('Pilot allocation differs')
    rows = [audit(root/'generation'/f'task-{i}') for i in range(3)]
    if [r['task_id'] for r in rows] != ids:
        raise ValueError('Generation allocation differs')
    meta = cli.read(root/'native-controls/gold/run-metadata.json')
    env = {**meta, **meta['provenance'], 'upstream_commit':meta['upstream_commit_verified']}
    if env['image_id'] != scc.IMAGE or env['upstream_commit'] != '09dd993f46c3fbf3a799465bb96d524edcb0b199':
        raise ValueError('Native software differs')
    dataset = [json.loads(line) for line in (root/'native-preparation/evaluator_dataset.jsonl').read_text(encoding='utf-8').splitlines()]
    if [r['task_id'] for r in dataset] != ids:
        raise ValueError('Evaluator allocation differs')
    gold = {r['task_id']:r['code_prompt']+r['canonical_solution'] for r in dataset}
    negative = {t:s+'\n\n# Deliberately incorrect SCC control.\ndef task_func(*args, **kwargs):\n    return None\n' for t,s in gold.items()}
    candidates = {t:(root/'generation'/f'task-{i}'/'candidate.py').read_text(encoding='utf-8') for i,t in enumerate(ids)}
    reports = {}
    for name, expected in [('gold',gold),('negative',negative),('candidates',candidates)]:
        result = validate_native(root/'native-controls'/name, expected, env)
        if not result['ok']:
            raise ValueError(str(result['errors']))
        reports[name] = result['statuses']
    if set(reports['gold'].values()) != {'pass'} or set(reports['negative'].values()) != {'fail'}:
        raise ValueError('Pilot reference controls failed')
    for row in rows:
        row['quality'] = reports['candidates'][row['task_id']]
    return {'role':'development feasibility only', 'assigned':3, 'generated':3,
            'native_checked':3, 'rows':rows,
            'model_calls':sum(r['model_calls'] for r in rows),
            'total_tokens':sum(r['input_tokens']+r['output_tokens'] for r in rows),
            'api_equivalent_usd':sum(r['api_equivalent_usd'] for r in rows),
            'passed':sum(r['quality']=='pass' for r in rows), 'controls':reports}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder',type=Path)
    p.add_argument('--whole-pilot',action='store_true')
    args=p.parse_args()
    print(json.dumps((audit_pilot if args.whole_pilot else audit)(args.folder),ensure_ascii=False))
