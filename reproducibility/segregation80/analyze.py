"""Pre-generation fixed task-paired inference for the independent 80-task extension."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import binom, binomtest

ARMS=('role_boundary','neutral_boundary','role_prose','neutral_prose')
PRIMARY={'role_boundary_minus_neutral_boundary':('role_boundary','neutral_boundary'),
         'role_prose_minus_neutral_prose':('role_prose','neutral_prose')}
SECONDARY={'boundary_minus_prose_role':('role_boundary','role_prose'),
           'boundary_minus_prose_neutral':('neutral_boundary','neutral_prose')}


def interval(values):
    if len(values)<2:return None
    x=np.asarray(values,dtype=float)
    rng=np.random.default_rng(20260908)
    boot=x[rng.integers(0,len(x),size=(10000,len(x)))].mean(axis=1)
    return np.quantile(boot,[.025,.975]).tolist()


def holm(values):
    order=sorted(values,key=values.get)
    result={};prev=0
    for i,k in enumerate(order):
        prev=max(prev,min(1,(len(order)-i)*values[k]));result[k]=prev
    return result


def summarize(records, ids):
    if len(ids)!=80 or len(set(ids))!=80:raise ValueError('Exactly 80 unique assigned tasks required')
    index={}
    for row in records:
        key=(row['task_id'],row['arm'])
        if key in index or key[0] not in ids or key[1] not in ARMS:raise ValueError('Duplicate or unassigned record')
        if row['quality'] is not None and type(row['quality']) is not bool:raise ValueError('Quality must be boolean or unknown')
        index[key]=row
    groups=[]
    for arm in ARMS:
        rows=[index[(t,arm)] for t in ids if (t,arm) in index]
        known=[r for r in rows if r['quality'] is not None]
        passed=sum(r['quality'] for r in known)
        resources=[r for r in rows if r.get('total_tokens') is not None]
        groups.append({'arm':arm,'assigned':80,'generation_complete':len(resources),'quality_observed':len(known),'passes':passed,
                       'pass_rate':passed/len(known) if known else None,'assigned_rate_bounds':[passed/80,(passed+80-len(known))/80],
                       **{f'mean_{metric}':float(np.mean([r[metric] for r in resources])) if resources else None
                          for metric in ('total_tokens','api_equivalent_usd','uncached_sensitivity_usd')}})
    contrasts={}
    for name,(a,b) in {**PRIMARY,**SECONDARY}.items():
        pairs=[(index[t,a],index[t,b]) for t in ids if (t,a) in index and (t,b) in index]
        quality=[(x['quality'],y['quality']) for x,y in pairs if x['quality'] is not None and y['quality'] is not None]
        differences=[int(x)-int(y) for x,y in quality]
        wins=sum(x and not y for x,y in quality);losses=sum(y and not x for x,y in quality)
        entry={'quality_pairs':len(quality),'wins':wins,'losses':losses,
               'quality_difference':float(np.mean(differences)) if differences else None,'quality_bootstrap_95':interval(differences)}
        if name in PRIMARY:
            entry['exact_two_sided_mcnemar_p']=float(binomtest(wins,wins+losses,.5).pvalue) if wins+losses else 1.
        for metric in ('total_tokens','api_equivalent_usd','uncached_sensitivity_usd'):
            resource=[(x[metric],y[metric]) for x,y in pairs if x.get(metric) is not None and y.get(metric) is not None]
            delta=[x-y for x,y in resource]
            den=sum(y for x,y in resource)
            entry[metric]={'pairs':len(resource),'mean_difference':float(np.mean(delta)) if delta else None,
                           'descriptive_bootstrap_95':interval(delta),'ratio_of_means':sum(x for x,y in resource)/den if den else None}
        contrasts[name]=entry
    corrected=holm({k:contrasts[k]['exact_two_sided_mcnemar_p'] for k in PRIMARY})
    for k,p in corrected.items():contrasts[k]['holm_p']=p
    interaction=[]
    for t in ids:
        if all((t,a) in index and index[t,a]['quality'] is not None for a in ARMS):
            v={a:int(index[t,a]['quality']) for a in ARMS}
            interaction.append(v['role_boundary']-v['neutral_boundary']-v['role_prose']+v['neutral_prose'])
    return {'schema':'segregation80-analysis-v1','assigned_tasks':80,'assigned_candidates':320,
            'primary_family_size':2,'familywise_alpha':.05,'by_arm':groups,'contrasts':contrasts,
            'quality_interaction':{'pairs':len(interaction),'mean':float(np.mean(interaction)) if interaction else None,'descriptive_bootstrap_95':interval(interaction)},
            'noninferiority':'not assessed; no justified margin','money_advantage':'descriptive paired valuation only; no joint quality-cost claim'}


def power_grid():
    # Exact unconditional power: D~Binomial(n,discordance), wins|D~Binomial(D,(d+delta)/(2d)).
    # alpha .025 is the conservative first Holm threshold for the two-test family.
    rows=[]
    for d in (.15,.30,.50):
        for delta in (.02,.05,.10,.15):
            if delta>d:continue
            power=0.
            for discordant in range(1,81):
                pwin=(d+delta)/(2*d)
                rejected=[w for w in range(discordant+1) if binomtest(w,discordant,.5).pvalue<=.025]
                power+=float(binom.pmf(discordant,80,d)*sum(binom.pmf(w,discordant,pwin) for w in rejected))
            rows.append({'n':80,'discordance':d,'quality_difference':delta,'two_sided_alpha':.025,'power':power})
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--records',type=Path)
    p.add_argument('--selection',type=Path)
    p.add_argument('--power',action='store_true')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Refusing to overwrite analysis')
    value=power_grid() if a.power else summarize(json.loads(a.records.read_text(encoding='utf-8')),json.loads(a.selection.read_text(encoding='utf-8'))['assigned_task_ids'])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
