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
