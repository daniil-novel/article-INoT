import hashlib
import json
from pathlib import Path

import pytest

from reproducibility import codex_subscription as c
from reproducibility.segregation80.collect import _verify_turn


def fixture(tmp_path):
    archive=tmp_path/'copied-archive';turn=archive/'turns'/'a';turn.mkdir(parents=True)
    prompt='frozen prompt'
    cell={'id':'a','task_id':'x','arm':'role_boundary','prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
    runtime={'version':c.CLI_VERSION,'prefix':['node','old/codex.js']}
    argv=c.cli_command(runtime['prefix'],Path('/original/empty'),Path('/original/instructions.txt'))
    (archive/'instructions.txt').write_bytes(c.BASE.encode())
    (turn/'prompt.txt').write_bytes(prompt.encode())
    (turn/'stderr.txt').write_bytes(b'')
    c.save(turn/'argv.json',argv);c.save(turn/'status.json',{'state':'completed'})
    events=[{'type':'thread.started'},{'type':'turn.started'},
            {'type':'item.completed','item':{'type':'agent_message','text':'```python\nx=1\n```'}},
            {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':0,'output_tokens':10}}]
    (turn/'events.jsonl').write_bytes(b''.join(c.canonical(e)+b'\n' for e in events))
    parsed=c.parse_events((turn/'events.jsonl').read_bytes())
    parsed['files_sha256']={name:hashlib.sha256((turn/name).read_bytes()).hexdigest() for name in ['prompt.txt','argv.json','events.jsonl','stderr.txt']}
    c.save(turn/'result.json',parsed)
    record={**cell,**parsed,'generation_complete':True,'total_tokens':110}
    return archive,cell,record,prompt,runtime


def test_portable_archive_does_not_read_original_absolute_instructions(tmp_path):
    args=fixture(tmp_path)
    assert _verify_turn(*args)['instruction_sha256']==hashlib.sha256(c.BASE.encode()).hexdigest()


def test_equal_but_wrong_cli_configuration_is_rejected(tmp_path):
    args=fixture(tmp_path)
    archive,cell,record,prompt,runtime=args
    turn=archive/'turns'/'a'
    argv=json.loads((turn/'argv.json').read_text())
    argv[argv.index('--model')+1]='wrong-model'
    c.save(turn/'argv.json',argv)
    saved=json.loads((turn/'result.json').read_text())
    saved['files_sha256']['argv.json']=hashlib.sha256((turn/'argv.json').read_bytes()).hexdigest()
    c.save(turn/'result.json',saved)
    with pytest.raises(ValueError,match='configuration'):_verify_turn(*args)


def test_altered_cell_assignment_is_rejected(tmp_path):
    args=list(fixture(tmp_path));args[2]={**args[2],'arm':'neutral_boundary'}
    with pytest.raises(ValueError,match='labels'):_verify_turn(*args)
