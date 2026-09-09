import json,hashlib
from pathlib import Path
from reproducibility.benchmark_bridge import _prepare_output_row
root=Path('.'); ids=['BigCodeBench/325','BigCodeBench/322','BigCodeBench/1036']; src=root/'reproducibility/data/bigcodebench-v0.1.4.jsonl'
raw={}; rows={}
for line in src.read_bytes().splitlines():
    if not line.strip(): continue
    row=json.loads(line); tid=str(row['task_id'])
    if tid in ids: raw[tid]=line; rows[tid]=row
if set(raw)!=set(ids): raise SystemExit(f'input ID mismatch: {list(raw)}')
out=root/'reproducibility/runs/scc-dev3-v1/native-preparation'
(out/'evaluator_dataset.jsonl').write_bytes(b''.join(raw[t]+b'\n' for t in ids))
prepared=[_prepare_output_row(rows[t]) for t in ids]
(out/'prepared.jsonl').write_bytes(b''.join(json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()+b'\n' for x in prepared))
gold=[]; incorrect=[]
for t in ids:
    solution=str(rows[t]['code_prompt'])+str(rows[t]['canonical_solution'])
    gold.append({'task_id':t,'solution':solution})
    incorrect.append({'task_id':t,'solution':solution+'\n\n# Deliberately incorrect SCC control.\ndef task_func(*args, **kwargs):\n    return None\n'})
for name,data in [('gold.jsonl',gold),('incorrect.jsonl',incorrect)]:
    (out/name).write_bytes(b''.join(json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()+b'\n' for x in data))
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
selection={'schema':'scc-dev3-selection-v1','role':'development only','assigned_task_ids':ids,'selection_rule':'fixed archived SCC dev pilot IDs; no outcome selection','source_dataset_sha256':h(src),'evaluator_dataset_sha256':h(out/'evaluator_dataset.jsonl'),'model_input_sha256':h(out/'prepared.jsonl'),'source_row_sha256':{t:hashlib.sha256(raw[t]).hexdigest() for t in ids},'controls_complete':False,'evaluable_task_ids':[]}
(out/'selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'ids':ids,'selection_sha256':h(out/'selection.json'),'dataset_sha256':h(out/'evaluator_dataset.jsonl'),'prepared_sha256':h(out/'prepared.jsonl')},sort_keys=True))
