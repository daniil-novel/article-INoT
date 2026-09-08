"""Freeze 200 prior IDs plus 800 previously unused IDs before reference controls."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from ..heldout200.prepare_inputs import read_source_rows, write_jsonl, sha256_file
from ..benchmark_bridge import _prepare_output_row

ROOT=Path(__file__).resolve().parents[2]

def prepare(output: Path) -> dict:
    source=ROOT/'reproducibility/data/bigcodebench-v0.1.4.jsonl'
    split_path=ROOT/'reproducibility/data/bigcodebench-split/prepare_manifest.json'
    split=json.loads(split_path.read_text(encoding='utf-8'))
    if sha256_file(source)!=split['source_sha256']:raise ValueError('Frozen dataset changed')
    prior_path=ROOT/'reproducibility/revision/heldout200_selection.json'
    extension_path=ROOT/'reproducibility/segregation80/inputs-v2/selection.json'
    prior=json.loads(prior_path.read_text(encoding='utf-8'))['assigned_task_ids']
    extension=json.loads(extension_path.read_text(encoding='utf-8'))['assigned_task_ids']
    excluded=set(split['dev_task_ids']) | set(extension) | {f'BigCodeBench/{i}' for i in range(8)}
    fresh=[t for t in split['confirmatory_task_ids'] if t not in excluded and t not in prior]
    if len(prior)!=200 or len(fresh)<800 or set(prior)&excluded:raise ValueError('Insufficient disjoint allocation')
    new=fresh[:800];assigned=prior+new
    if len(set(assigned))!=1000:raise ValueError('Duplicate assigned ID')
    rows,raw=read_source_rows(source);by_id={r['task_id']:r for r in rows}
    output.mkdir(parents=True,exist_ok=False)
    inp=output/'input';eva=output/'evaluator';inp.mkdir();eva.mkdir()
    model=[_prepare_output_row(by_id[t]) for t in assigned]
    write_jsonl(inp/'prepared.jsonl',model)
    (eva/'evaluator_dataset.jsonl').write_bytes(b''.join(raw[t]+b'\n' for t in assigned))
    gold=[{'task_id':t,'solution':str(by_id[t]['code_prompt'])+str(by_id[t]['canonical_solution'])} for t in assigned]
    bad=[{'task_id':r['task_id'],'solution':r['solution']+'\n\n# Deliberately incorrect control.\ndef task_func(*args, **kwargs):\n    return None\n'} for r in gold]
    write_jsonl(eva/'gold.jsonl',gold);write_jsonl(eva/'incorrect.jsonl',bad)
    prompt_hashes={t:hashlib.sha256(by_id[t]['instruct_prompt'].encode()).hexdigest() for t in assigned}
    duplicates={h:[t for t in assigned if prompt_hashes[t]==h] for h in set(prompt_hashes.values()) if list(prompt_hashes.values()).count(h)>1}
    selection={'schema':'scale1000-selection-v1','assigned_task_ids':assigned,'prior_primary_task_ids':prior,
               'new_task_ids':new,'replicate_ids':[101,102,103],'source_task_count':len(rows),
               'selection_rule':'all prior 200 plus first 800 unused IDs in the original frozen random reserved order; exclude dev40, segregation80 and examples /0-/7',
               'fresh_pool_size':len(fresh),'excluded_task_ids':sorted(excluded),
               'source_dataset_sha256':sha256_file(source),'source_split_sha256':sha256_file(split_path),
               'prior_selection_sha256':sha256_file(prior_path),'extension_selection_sha256':sha256_file(extension_path),
               'model_input_sha256':sha256_file(inp/'prepared.jsonl'),'evaluator_dataset_sha256':sha256_file(eva/'evaluator_dataset.jsonl'),
               'source_row_sha256':{t:hashlib.sha256(raw[t]).hexdigest() for t in assigned},
               'duplicate_exact_instruction_groups':list(duplicates.values()),
               'independence_note':'1000 unique task IDs are task clusters, not proof of semantic independence or unseen training data',
               'model_outputs_present':False,'controls_complete':False}
    (output/'selection.json').write_text(json.dumps(selection,indent=2)+'\n',encoding='utf-8',newline='\n')
    files={p.relative_to(output).as_posix():sha256_file(p) for p in output.rglob('*') if p.is_file()}
    (output/'input_manifest.json').write_text(json.dumps({'schema':'scale1000-input-v1','files':files},indent=2)+'\n',encoding='utf-8',newline='\n')
    return {'assigned':1000,'prior':200,'new':800,'fresh_pool':len(fresh),'exact_duplicate_groups':len(duplicates)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().output)))
