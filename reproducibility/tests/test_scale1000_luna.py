import json
import pytest
from pathlib import Path

from reproducibility import codex_luna_subscription as c
from reproducibility.scale1000_luna import dispatch


def _tasks(n=2):
    return [{"task_id": f"BigCodeBench/{i}", "model": "fixture", "arm": "direct", "seed": 1,
             "prompt": "Implement task", "context": "provided context"} for i in range(n)]


def test_luna_price_model_and_cli_arguments():
    assert c.MODEL == "gpt-5.6-luna"
    assert c.PRICES == {"input": .20, "cached_input": .02, "output": 1.20}
    command = c.cli_command(["node", "codex.js"], Path("empty"), Path("instructions.txt"))
    assert command[command.index("--model") + 1] == c.MODEL
    assert "model_reasoning_effort=\"medium\"" in command
    assert c.CLI_VERSION == "codex-cli 0.153.4"


def test_manifest_has_three_repeats_and_expected_turn_boundary():
    manifest = c.make_manifest(_tasks(), [101, 102, 103], list(c.ARMS))
    assert manifest["schema"] == "codex-luna-subscription-v1"
    assert manifest["model_requested"] == c.MODEL
    assert manifest["replicate_ids"] == [101, 102, 103]
    assert manifest["planned_generations"] == 30
    assert manifest["planned_cli_turns"] == 54
    assert all(cell["replicate_id"] in {101, 102, 103} for cell in manifest["cells"])


def test_raw_event_replay_preserves_luna_usage_valuation():
    usage = {"input_tokens": 100, "cached_input_tokens": 25, "output_tokens": 10}
    events = [
        {"type": "thread.started"}, {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "```python\npass\n```"}},
        {"type": "turn.completed", "usage": usage},
    ]
    parsed = c.parse_events(b"".join(c.canonical(row) + b"\n" for row in events))
    assert parsed["usage"] == usage
    expected = ((100 - 25) * .20 + 25 * .02 + 10 * 1.20) / 1e6
    assert parsed["api_equivalent_usd"] == expected
    assert (100 * c.PRICES["input"] + 10 * c.PRICES["output"]) / 1e6 == .000032


def test_circuit_breaker_and_failure_preservation_are_in_new_dispatch():
    actual="The 'gpt-5.4-mini' model is not supported when using Codex with a ChatGPT account."
    assert dispatch.circuit_reason(actual,1)=='unsupported_or_deprecated_model'
    assert dispatch.circuit_reason('Model metadata for x not found',1)=='unsupported_or_deprecated_model'
    assert dispatch.circuit_reason('connection reset',7) is None
    assert dispatch.circuit_reason('connection reset',8)=='eight_consecutive_failures'
    assert dispatch.circuit_reason('rate_limit exceeded',1)=='quota_or_auth'
    assert dispatch.circuit_reason('',1,'unknown cache-write accounting')=='unpriceable_or_invalid_usage'


def test_nonzero_cache_writes_cannot_be_silently_underpriced(tmp_path):
    from reproducibility.scale1000_luna.collect import raw_usage
    usage={'input_tokens':100,'cached_input_tokens':0,'output_tokens':10,'cache_write_input_tokens':50}
    (tmp_path/'events.jsonl').write_text(json.dumps({'type':'turn.completed','usage':usage}))
    with pytest.raises(ValueError,match='cache-write'):raw_usage(tmp_path)


def test_luna_raw_response_export_native_join_and_usage_replay(tmp_path,monkeypatch):
    from reproducibility.scale1000_luna import collect as module
    from reproducibility.scale1000_luna import dispatch
    from reproducibility.tests.test_scale1000_evidence import stream
    archive=tmp_path/'generation';inputs=tmp_path/'inputs';gate=tmp_path/'controls'
    archive.mkdir();(inputs/'input').mkdir(parents=True);gate.mkdir()
    task={'task_id':'t0','prompt':'Return one.','context':'','benchmark':'bigcodebench','metadata':{}}
    (inputs/'input/prepared.jsonl').write_bytes(c.canonical(task)+b'\n')
    c.save(inputs/'selection.json',{'assigned_task_ids':['t0']})
    c.save(gate/'heldout200_control_gate.json',{'evaluable_task_ids':['t0']})
    cell={'id':'fixture-cell','task_id':'t0','arm':'single_roles','replicate_id':101,'cli_turns':1}
    frozen={'inner_manifest':{'cells':[cell]}}
    manifest=tmp_path/'manifest.json';c.save(manifest,frozen);c.save(archive/'manifest.json',frozen)
    monkeypatch.setattr(dispatch,'plan',lambda *args:frozen)
    c.save(archive/'tasks.json',[task]);c.save(archive/'status.json',{'state':'generation_finished'})
    (archive/'instructions.txt').write_bytes(c.BASE.encode())
    c.save(archive/'runtime.json',{'prefix':['fixture-codex'],'version':c.CLI_VERSION})
    folder=archive/'turns/fixture-cell-0';folder.mkdir(parents=True)
    answer='```python\ndef task_func():\n    return 1\n```'
    stream(folder,answer)
    (folder/'prompt.txt').write_bytes(c.prompt_for(task,cell,0,[]).encode())
    c.save(folder/'argv.json',c.cli_command(['fixture-codex'],tmp_path/'empty',archive/'instructions.txt'))
    result=c.parse_events((folder/'events.jsonl').read_bytes())
    result['files_sha256']={n:dispatch.sha(folder/n) for n in ('prompt.txt','argv.json','events.jsonl','stderr.txt')}
    c.save(folder/'result.json',result);c.save(folder/'status.json',{'state':'completed'})
    c.save(archive/'cells/fixture-cell.json',{**cell,**result,'total_tokens':110})
    predictions=tmp_path/'predictions';module.export(archive,inputs,gate,manifest,predictions)
    monkeypatch.setattr(module,'environment_from_gate',lambda *args:{})
    monkeypatch.setattr(module,'validate_native',lambda folder,expected,env:{'ok':True,'statuses':{t:'pass' for t in expected}})
    out=tmp_path/'analysis';module.collect(archive,inputs,gate,manifest,predictions,tmp_path/'native',out)
    row=json.loads((out/'candidate_records.jsonl').read_text())
    assert row['quality'] is True and row['total_tokens']==110
    ledger=c.read(out/'turn_usage.json');assert ledger[0]['api_equivalent_usd']==c.value_usage(result['usage'])
    assert ledger[0]["uncached_sensitivity_usd"] == .000032
    # A changed exported program must fail before a native status can be trusted.
    (predictions/'single_roles-r101.jsonl').write_text('[]\n')
    with pytest.raises(ValueError,match='Export differs'):module.collect(archive,inputs,gate,manifest,predictions,tmp_path/'native',tmp_path/'tampered')
