"""Join audited complete CLI traces to independently executed pilot test results."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
try:
    from . import codex_subscription as c
    from .audit_codex_pilot import audit
    from .benchmark_bridge import _extract_fenced_block
    from .bcb_pilot_evaluator import analysis_outcome, quality_summary
except ImportError:
    import codex_subscription as c
    from audit_codex_pilot import audit
    from benchmark_bridge import _extract_fenced_block
    from bcb_pilot_evaluator import analysis_outcome, quality_summary


def join(archive, evaluations):
    summary=audit(archive)
    rows=[json.loads(s) for s in (archive/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    ids=[t['task_id'] for t in c.read(archive/'tasks.json')]
    fingerprints=[]
    for group in summary['by_arm']:
        arm=group['arm'];path=evaluations/arm/'pilot-predictions.json';result=c.read(path)
        fingerprints.append({k:result[k] for k in ('upstream_commit','dataset_sha256','prepared_split_sha256','vendor_tree_sha256','requirements_sha256','dockerfile_sha256','image_id','limits','pip_freeze')})
        records=result['records']
        modelrows=[r for r in records if r['control']=='prediction']
        if len(modelrows)!=len(ids) or {r['task_id'] for r in modelrows}!=set(ids):raise ValueError('Evaluator omitted or duplicated an assigned task')
        for prediction in modelrows:
            task_id=prediction['task_id']
            candidates=[r for r in rows if r['arm']==arm and r['task_id']==task_id]
            if len(candidates)!=1:raise ValueError('Expected exactly one replicate in development pilot')
            solution,_=_extract_fenced_block(candidates[0]['final_text'],'bigcodebench')
            if prediction['solution_sha256']!=hashlib.sha256(solution.encode()).hexdigest():raise ValueError('Evaluated solution differs from complete archived final answer')
            controls=[r for r in records if r['task_id']==task_id and r['control'] in {'gold','incorrect'}]
            if len(controls)!=2 or {r['control'] for r in controls}!={'gold','incorrect'}:raise ValueError('Missing or duplicated controls')
            expected=analysis_outcome(prediction['status'],{r['control']:r for r in controls})
            if prediction['analysis_status']!=expected:raise ValueError('Evaluator status does not match control gate')
        quality=quality_summary(records,ids)
        if result['prediction_analysis']!=quality:raise ValueError('Quality summary differs from original test records')
        group['quality']=quality
        group['evaluation_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    if any(f!=fingerprints[0] for f in fingerprints):raise ValueError('Evaluation environments differ across arms')
    summary['evaluation_environment']=fingerprints[0]
    summary['quality_status']='upstream-core development pilot with original tests; not the full official CLI score'
    groupmap={g['arm']:g for g in summary['by_arm']}
    summary['mean_token_ratios']={
        'roles_over_neutral_single':groupmap['single_roles']['mean_total_tokens']/groupmap['single_neutral']['mean_total_tokens'],
        'roles_over_neutral_multi':groupmap['multi_roles']['mean_total_tokens']/groupmap['multi_neutral']['mean_total_tokens'],
        'multi_over_single_neutral':groupmap['multi_neutral']['mean_total_tokens']/groupmap['single_neutral']['mean_total_tokens'],
        'multi_over_single_roles':groupmap['multi_roles']['mean_total_tokens']/groupmap['single_roles']['mean_total_tokens']}
    summary['inference']='descriptive development observations on eight tasks; no significance, non-inferiority or benchmark-wide claim'
    return summary


def write_tables(summary, out):
    out.mkdir(parents=True,exist_ok=True)
    names={'single_neutral':('1 / neutral','1 / нейтр.'),'single_roles':('1 / roles','1 / роли'),
           'multi_neutral':('3 / neutral','3 / нейтр.'),'multi_roles':('3 / roles','3 / роли'),
           'direct':('Direct','Прямой')}
    for lang,index in [('en',0),('ru',1)]:
        caption=('Observed development results: eight assigned tasks per condition. Costs are mean API-equivalent USD per candidate; tokens include CLI overhead. The quality interval is the range under unresolved outcomes, not a confidence interval.' if lang=='en' else
                 'Наблюдаемые результаты разработки: восемь назначенных задач на режим. Стоимость --- средняя условная цена решения по API, токены включают накладные расходы CLI. Диапазон качества отражает неразрешённые исходы, а не доверительный интервал.')
        header=('Condition & Tokens & USD & Pass/evaluable & Range' if lang=='en' else 'Режим & Токены & USD & Успех/оценено & Диапазон')
        lines=[r'\begin{table}[htbp]',r'\centering\small',r'\caption{'+caption+'}',r'\label{tab:codexpilot}',r'\begin{tabular}{lrrrr}',r'\toprule',header+r' \\',r'\midrule']
        for g in summary['by_arm']:
            q=g['quality']
            lines.append(f"{names[g['arm']][index]} & {g['mean_total_tokens']:.0f} & {g['mean_api_equivalent_usd']:.5f} & {q['pass_count']}/{q['evaluable_tasks']} & {q['pessimistic_lower_bound']:.3f}--{q['optimistic_upper_bound']:.3f}"+r' \\')
        lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}']
        (out/f'codex_pilot_table_{lang}.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--evaluations',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--tables',type=Path,required=True)
    args=p.parse_args();result=join(args.archive,args.evaluations)
    c.save(args.output,result);write_tables(result,args.tables)
    print(json.dumps({k:result[k] for k in ('generations','cli_turns','total_tokens','total_api_equivalent_usd','mean_token_ratios')},indent=2))


if __name__=='__main__': main()
