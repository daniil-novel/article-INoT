"""Retrospective precision/temporal diagnostics; no model calls or new decisions."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.stats import t

CONTRASTS = {
 'SR--SN': ('single_roles','single_neutral'),
 'MR--MN': ('multi_roles','multi_neutral'),
 'MN--SN': ('multi_neutral','single_neutral'),
 'MR--SR': ('multi_roles','single_roles'),
}
REPEATS = (101,102,103)

def read_rows(path):
 return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]

def bootstrap(x, seed=20261003):
 values=np.asarray(x,dtype=float)
 if len(values)<2: raise ValueError('Insufficient task units')
 rng=np.random.Generator(np.random.PCG64(seed))
 draws=np.empty(10000,dtype=float)
 for start in range(0,10000,250):
  stop=min(start+250,10000)
  draws[start:stop]=values[rng.integers(0,len(values),size=(stop-start,len(values)))].mean(axis=1)
 return [float(v) for v in np.quantile(draws,[.025,.975],method='linear')]

def analyze(ledger, phase_path):
 rows=read_rows(ledger)
 index={}
 for row in rows:
  key=(row['task_id'],row['arm'],row['replicate_id'])
  if key in index: raise ValueError('Duplicate assigned endpoint')
  index[key]=row
 if len(rows)!=15000: raise ValueError('Expected original15000 assigned endpoints')
 tasks=sorted({r['task_id'] for r in rows})
 phases=read_rows(phase_path)
 phase_index={r['id']:r['phase'] for r in phases}
 if len(phase_index)!=len(phases): raise ValueError('Duplicate generation phase ID')
 complete_ids={r['id'] for r in rows if r['generation_complete']}
 if set(phase_index)!=complete_ids: raise ValueError('Phase IDs do not exactly cover completed candidates')
 if set(phase_index.values())!={'first_completed_session','later_sessions'}: raise ValueError('Unexpected phase')
 result={'status':'retrospective_descriptive','seed':20261003,'draws':10000,
         'ledger_sha256':hashlib.sha256(ledger.read_bytes()).hexdigest(),
         'phase_sha256':hashlib.sha256(phase_path.read_bytes()).hexdigest(),
         'interval_family':'four Bonferroni98.75percent Student t intervals; conditional approximate simultaneous95percent',
         'precision':{},'phases':{},'resource_scale':{}}
 for name,(a,b) in CONTRASTS.items():
  result['resource_scale'][name]={}
  for metric in ('api_equivalent_usd','total_tokens'):
   differences=[]
   for task in tasks:
    left=[index[(task,a,r)] for r in REPEATS]
    right=[index[(task,b,r)] for r in REPEATS]
    endpoints=left+right
    valid=all(v['generation_complete'] is True and isinstance(v.get(metric),(int,float)) and not isinstance(v.get(metric),bool) and math.isfinite(float(v[metric])) for v in endpoints)
    if valid:
     differences.append(float(np.mean([v[metric] for v in left]))-float(np.mean([v[metric] for v in right])))
   result['resource_scale'][name][metric]={'tasks':len(differences),'mean_difference':float(np.mean(differences))}
  diff=[]
  for task in tasks:
   pairs=[(index[(task,a,r)],index[(task,b,r)]) for r in REPEATS]
   if all(type(v['quality']) is bool for pair in pairs for v in pair):
    diff.append(float(np.mean([int(x['quality'])-int(y['quality']) for x,y in pairs])))
  x=np.asarray(diff);n=len(x);mean=float(x.mean());se=float(x.std(ddof=1)/math.sqrt(n));critical=float(t.ppf(1-.05/(2*4),n-1))
  result['precision'][name]={'tasks':n,'mean':mean,'standard_error':se,'bonferroni_interval':[mean-critical*se,mean+critical*se]}
  result['phases'][name]={}
  for phase in ('first_completed_session','later_sessions'):
   values=[];matched=0
   for task in tasks:
    differences=[]
    for r in REPEATS:
     left,right=index[(task,a,r)],index[(task,b,r)]
     if type(left['quality']) is bool and type(right['quality']) is bool and phase_index[left['id']]==phase_index[right['id']]==phase:
      differences.append(int(left['quality'])-int(right['quality']))
    if differences: values.append(float(np.mean(differences)));matched+=len(differences)
   result['phases'][name][phase]={'tasks':len(values),'matched_repeat_pairs':matched,'mean':float(np.mean(values)),'bootstrap95':bootstrap(values)}
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--ledger',type=Path,default=Path('primary/assignment_outcomes.jsonl'))
 parser.add_argument('--phases',type=Path,default=Path('primary/generation_phases.jsonl'))
 parser.add_argument('--expected',type=Path)
 parser.add_argument('--output',type=Path,default=Path('revision_diagnostics.json'))
 args=parser.parse_args();result=analyze(args.ledger,args.phases)
 if args.expected:
  expected=json.loads(args.expected.read_text(encoding='utf-8'))
  if result!=expected: raise AssertionError('Diagnostics differ from frozen checkpoint')
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()