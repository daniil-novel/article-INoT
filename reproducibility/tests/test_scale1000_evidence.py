import json
import pytest
from reproducibility import codex_subscription as c
from reproducibility.scale1000.dispatch import completed_empty
from reproducibility.scale1000.collect import raw_usage,event_parse_errors


def stream(folder,text=''):
    events=[{'type':'thread.started','thread_id':'fixture'}, {'type':'turn.started'},
            {'type':'item.completed','item':{'id':'x','type':'agent_message','text':text}},
            {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':20,'output_tokens':10}}]
    (folder/'events.jsonl').write_bytes(b'\n'.join(c.canonical(e) for e in events)+b'\n')
    (folder/'prompt.txt').write_text('fixture');(folder/'argv.json').write_text('[]');(folder/'stderr.txt').write_text('')
    c.save(folder/'status.json',{'state':'blocked','reason':'One completed turn and one complete answer required'})


def test_completed_empty_is_failure_data_without_changing_original_stream(tmp_path):
    stream(tmp_path);before=(tmp_path/'events.jsonl').read_bytes()
    result=completed_empty(tmp_path)
    assert result['final_text']=='' and result['empty_model_response'] is True
    assert result['usage']['input_tokens']==100
    assert (tmp_path/'events.jsonl').read_bytes()==before
    assert c.read(tmp_path/'status.json')['state']=='blocked'


def test_empty_after_timeout_is_not_accepted(tmp_path):
    stream(tmp_path)
    c.save(tmp_path/'status.json',{'state':'blocked','reason':'CLI timeout; usage may be incomplete, no automatic retry'})
    with pytest.raises(ValueError,match='terminal empty'):completed_empty(tmp_path)
    assert raw_usage(tmp_path)['input_tokens']==100


def test_completed_turn_with_no_message_is_retained_as_empty_model_failure(tmp_path):
    stream(tmp_path)
    events=[json.loads(x) for x in (tmp_path/'events.jsonl').read_text().splitlines()]
    (tmp_path/'events.jsonl').write_bytes(b'\n'.join(c.canonical(e) for e in events if e.get('type')!='item.completed'))
    assert completed_empty(tmp_path)['final_text']==''


def test_torn_event_is_explicit_and_duplicate_completions_rejected(tmp_path):
    stream(tmp_path)
    with (tmp_path/'events.jsonl').open('ab') as f:f.write(b'{torn')
    assert event_parse_errors(tmp_path)==['invalid_event_line_5']
    assert raw_usage(tmp_path)['output_tokens']==10
    with pytest.raises(json.JSONDecodeError):completed_empty(tmp_path)
    stream(tmp_path)
    with (tmp_path/'events.jsonl').open('ab') as f:f.write(c.canonical({'type':'turn.completed','usage':{'input_tokens':1,'cached_input_tokens':0,'output_tokens':1}}))
    with pytest.raises(ValueError,match='Multiple usage'):raw_usage(tmp_path)


def test_cached_usage_cannot_exceed_input(tmp_path):
    (tmp_path/'events.jsonl').write_text(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'cached_input_tokens':2,'output_tokens':1}}))
    with pytest.raises(ValueError,match='Invalid usage'):raw_usage(tmp_path)


def test_raw_response_export_native_join_and_usage_replay(tmp_path,monkeypatch):
    from reproducibility.scale1000 import collect as module
    from reproducibility.scale1000 import dispatch
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
    # A changed exported program must fail before a native status can be trusted.
    (predictions/'single_roles-r101.jsonl').write_text('[]\n')
    with pytest.raises(ValueError,match='Export differs'):module.collect(archive,inputs,gate,manifest,predictions,tmp_path/'native',tmp_path/'tampered')
