"""Render primary and exploratory result artifacts from reconciled archives."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARMS=('direct','single_neutral','single_roles','multi_neutral','multi_roles')
CODES=dict(zip(ARMS,('D','SN','SR','MN','MR')))
KEYS=('roles_minus_neutral_single','roles_minus_neutral_multi','multi_minus_single_neutral','multi_minus_single_roles')
LABELS=('SR - SN','MR - MN','MN - SN','MR - SR')


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def rows(path):return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def tex(path,lines):path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
def interval(q):
    lo,hi=q['descriptive_task_bootstrap_95_interval']
    return f"${100*q['mean_paired_difference']:+.2f}\\;[{100*lo:+.2f},{100*hi:+.2f}]$"


def render(primary,inot,paired,selection):
    s=read(primary/'summary.json'); b=read(inot/'summary.json'); e=read(paired)
    p_rows=rows(primary/'candidate_records.jsonl'); b_rows=rows(inot/'candidate_records.jsonl')
    ids=read(selection)['assigned_task_ids']
    if len(ids)!=200 or len(set(ids))!=200 or s['assigned_attempts']!=1000 or b['assigned']!=200:
        raise ValueError('Wrong study allocation')
    if s['recorded_attempts']!=len(p_rows) or b['generated']!=len(b_rows):raise ValueError('Record count mismatch')
    groups={r['arm']:r for r in s['by_arm']}
    all_groups=[]
    for arm in ARMS:
        r=groups[arm]
        all_groups.append({'code':CODES[arm],'generated':r['recorded_attempts'],'n':r['evaluable_attempts'],
                           'passes':r['passes'],'rate':r['evaluable_only_rate'],
                           'bounds':[r['pessimistic_lower_bound'],r['optimistic_upper_bound']],
                           'format_failures':r['format_extraction_failures'],
                           **{k:r['mean_'+k] for k in ('total_tokens','api_equivalent_usd','uncached_sensitivity_usd')}})
    all_groups.append({'code':'INoT*','generated':b['generated'],'n':b['evaluable'],'passes':b['passes'],
                       'rate':b['evaluable_only_rate'],'bounds':b['missingness_bounds'],'format_failures':b['format_failures'],
                       **{k:b['completed_candidate_totals'][k]/b['generated'] for k in ('total_tokens','api_equivalent_usd','uncached_sensitivity_usd')}})
    for group,records in zip(all_groups,[[r for r in p_rows if r['arm']==arm] for arm in ARMS]+[b_rows]):
        if len(records)!=group['generated']:raise ValueError('Component denominator differs')
        for key in ('input_tokens','cached_input_tokens','output_tokens'):
            group[key]=sum(r['usage'][key] for r in records)/len(records)
        if abs(group['input_tokens']+group['output_tokens']-group['total_tokens'])>1e-8:
            raise ValueError('Token components do not reconcile')
        reasoning=[r['usage'].get('reasoning_output_tokens') for r in records]
        group['reasoning_subset_observed_candidates']=sum(x is not None for x in reasoning)
        group['mean_reasoning_output_subset']=sum(reasoning)/len(reasoning) if all(x is not None for x in reasoning) else None
    indexed={(r['task_id'],r['arm']):r for r in p_rows}
    ib={r['task_id']:r for r in b_rows}
    tests={t['contrast']:t for t in s['four_predeclared_quality_tests']}
    def status(r):
        if r is None:return 'M'
        if r['analysis_status'] is None:return 'U'
        return {'pass':'P','fail':'F','timeout':'T'}[r['analysis_status']]
    for lang in ('en','ru'):
        en=lang=='en'
        cap=('Main sample: 200 assignments per condition. Quality uses eligible observed programs; ranges retain all 200 assignments and are not confidence intervals. INoT* is a separate exploratory algorithm replication.' if en else
             'Основная выборка: по 200 назначений на условие. Качество рассчитано по наблюдаемым оцениваемым программам; границы учитывают все 200 назначений и не являются доверительными интервалами. INoT* --- отдельная поисковая репликация алгоритма.')
        out=['\\begin{table}[htbp]\\centering\\small','\\caption{'+cap+'}\\label{tab:heldout-quality}',
             '\\begin{tabular}{lrrrrr}\\toprule',
             ('Arm & Generated & Passes & Rate (\\%) & Range (\\%) & Format errors\\\\' if en else
              'Усл. & Получено & Прошло & Доля (\\%) & Границы (\\%) & Формат, ошибки\\\\'),'\\midrule']
        for r in all_groups:
            lo,hi=r['bounds']
            out.append(f"{r['code']} & {r['generated']} & {r['passes']}/{r['n']} & {100*r['rate']:.2f} & {100*lo:.2f}--{100*hi:.2f} & {r['format_failures']}\\\\")
        tex(ROOT/f'sections/heldout_quality_{lang}.tex',out+['\\bottomrule\\end{tabular}\\end{table}'])
        cap=('Resource means over completed candidates, including reference-ineligible tasks. Costs are API-equivalent USD; no-cache valuation removes the input cache discount. Interrupted-attempt usage is additionally reported in the submitted-turn ledger.' if en else
             'Средние ресурсы завершённых программ, включая задачи с отказом эталона. Денежные оценки даны в эквиваленте API, USD; чувствительность без кеша убирает скидку за кеш входа. Использование прерванных попыток дополнительно приведено в реестре отправленных вызовов.')
        out=['\\begin{table}[htbp]\\centering\\small','\\caption{'+cap+'}\\label{tab:heldout-resources}',
             '\\begin{tabular}{lrrrr}\\toprule',
             ('Arm & Candidates & Tokens & USD & No cache, USD\\\\' if en else
              'Усл. & Программы & Токены & USD & Без кеша, USD\\\\'),'\\midrule']
        for r in all_groups:
            out.append(f"{r['code']} & {r['generated']} & {r['total_tokens']:,.0f}".replace(',','\\,')+f" & {r['api_equivalent_usd']:.5f} & {r['uncached_sensitivity_usd']:.5f}\\\\")
        tex(ROOT/f'sections/heldout_resources_{lang}.tex',out+['\\bottomrule\\end{tabular}\\end{table}'])
        cap=('Four predeclared quality comparisons under amended execution. Differences and descriptive 95\\% task-bootstrap intervals are percentage points. W/L are discordant pairs in favour of the first/second condition. Holm adjusts the exact two-sided McNemar tests across all four comparisons.' if en else
             'Четыре заранее заданных сравнения качества при изменённом протоколе исполнения. Разности и описательные 95\\%-интервалы бутстрэпа по задачам даны в процентных пунктах. W/L --- несогласованные пары в пользу первого/второго условия. Поправка Холма применяется к точным двусторонним тестам Мак-Немара по четырём сравнениям.')
        out=['\\begin{table}[htbp]\\centering\\small','\\caption{'+cap+'}\\label{tab:heldout-tests}',
             '\\begin{tabular}{lrrrrr}\\toprule',
             ('Contrast & Pairs & Difference [interval] & W/L & $p$ & $p_{\\rm Holm}$\\\\' if en else
              'Контраст & Пары & Разность [интервал] & W/L & $p$ & $p_{\\rm Holm}$\\\\'),'\\midrule']
        for key,label in zip(KEYS,LABELS):
            q=s['paired_contrasts'][key]['quality'];t=tests[key]
            out.append(f"{label} & {t['complete_task_pairs']} & {interval(q)} & {t['a_only_passes']}/{t['b_only_passes']} & {t['exact_two_sided_mcnemar_p']:.4f} & {t['holm_adjusted_p']:.4f}\\\\")
        tex(ROOT/f'sections/heldout_tests_{lang}.tex',out+['\\bottomrule\\end{tabular}\\end{table}'])
        cap=('Descriptive paired resource contrasts. Ratios divide paired means; uncertainty is a 95\\% task-bootstrap interval for the paired mean difference in API-equivalent USD, not for the ratio.' if en else
             'Описательные парные ресурсные контрасты. Отношения делят парные средние; 95\\%-интервал бутстрэпа по задачам относится к средней парной разности в эквиваленте API, USD, а не к отношению.')
        out=['\\begin{table}[htbp]\\centering\\small','\\caption{'+cap+'}\\label{tab:heldout-resource-contrasts}',
             '\\begin{tabular}{lrrrr}\\toprule',
             ('Contrast & Pairs & Token ratio & USD ratio & USD difference [interval]\\\\' if en else
              'Контраст & Пары & Токены, отн. & USD, отн. & Разность USD [интервал]\\\\'),'\\midrule']
        for key,label in zip(KEYS,LABELS):
            r=s['paired_contrasts'][key];v=r['api_equivalent_usd'];lo,hi=v['descriptive_task_bootstrap_95_interval']
            out.append(f"{label} & {v['complete_task_clusters']} & {r['total_tokens']['ratio_of_paired_means']:.3f} & {v['ratio_of_paired_means']:.3f} & ${v['mean_paired_difference']:+.4f}\\;[{lo:+.4f},{hi:+.4f}]$\\\\")
        tex(ROOT/f'sections/heldout_resource_contrasts_{lang}.tex',out+['\\bottomrule\\end{tabular}\\end{table}'])
        exploratory=[('SN - D',s['paired_contrasts']['single_neutral_minus_direct']),('MR - D',s['paired_contrasts']['multi_roles_minus_direct']),
                     ('INoT* - D',e['paired_contrasts']['inot_minus_direct']),('INoT* - SR',e['paired_contrasts']['inot_minus_single_roles'])]
        cap=('Exploratory comparisons outside the four-test family. Intervals are descriptive 95\\% task bootstraps. Quality/resource columns give their respective complete-pair counts. INoT* was dispatched in a separate batch.' if en else
             'Поисковые сравнения вне семейства четырёх тестов. Интервалы --- описательный 95\\%-бутстрэп по задачам. Для качества и ресурсов указаны отдельные числа полных пар. INoT* запущен отдельной серией.')
        out=['\\begin{table}[htbp]\\centering\\small','\\caption{'+cap+'}\\label{tab:heldout-exploratory}',
             '\\begin{tabular}{lrrrr}\\toprule',
             ('Contrast & Pairs Q/R & Quality difference [interval] & Tokens, ratio & USD, ratio\\\\' if en else
              'Контраст & Пары Q/R & Разность качества [интервал] & Токены, отн. & USD, отн.\\\\'),'\\midrule']
        for label,r in exploratory:
            q=r['quality'];n=q.get('complete_task_clusters',q.get('complete_task_pairs'))
            v=r['api_equivalent_usd'];nr=v.get('complete_task_clusters',v.get('complete_task_pairs'))
            out.append(f"{label} & {n}/{nr} & {interval(q)} & {r['total_tokens']['ratio_of_paired_means']:.3f} & {v['ratio_of_paired_means']:.3f}\\\\")
        tex(ROOT/f'sections/heldout_exploratory_{lang}.tex',out+['\\bottomrule\\end{tabular}\\end{table}'])
        ids_sorted=sorted(ids,key=lambda t:int(t.split('/')[-1]));out=[]
        for offset in range(0,200,40):
            cap=(f'All main task outcomes, part {offset//40+1}/5. P = pass, F = fail, T = native timeout, U = unavailable by control, M = no complete generation. INoT* is the separate replication. Original scores are retained; no task is removed.' if en else
                 f'Все исходы основных задач, часть {offset//40+1}/5. P --- успех, F --- отказ, T --- превышение времени теста, U --- недоступно по контролю, M --- нет полной генерации. INoT* --- отдельная репликация. Исходные оценки сохранены; задачи не удалены.')
            out+=['\\begin{table}[!htbp]\\centering\\footnotesize','\\caption{'+cap+'}',
                  '\\begin{tabular*}{\\textwidth}{@{\\extracolsep{\\fill}}rrrrrrr}\\toprule','ID & D & SN & SR & MN & MR & INoT*\\\\\\midrule']
            for task in ids_sorted[offset:offset+40]:
                values=[status(indexed.get((task,arm))) for arm in ARMS]+[status(ib.get(task))]
                out.append(task.split('/')[-1]+' & '+' & '.join(values)+'\\\\')
            out+=['\\bottomrule\\end{tabular*}\\end{table}','\\clearpage']
        tex(ROOT/f'sections/heldout_tasks_{lang}.tex',out)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42})
    fig,ax=plt.subplots(figsize=(6.7,3.7),layout='constrained')
    colors=['#0c6470','#536e8a','#378b70','#a66d38','#946396','#333333']
    for r,color in zip(all_groups,colors):
        ax.scatter(100*r['api_equivalent_usd'],100*r['rate'],s=60,color=color,marker='s' if r['code']=='INoT*' else 'o')
        ax.annotate(r['code'],(100*r['api_equivalent_usd'],100*r['rate']),xytext=(5,-15) if r['code'] in ('MR','SN') else (5,5),textcoords='offset points')
    ax.set(xlabel='Mean API-equivalent valuation (US cents / candidate)',ylabel='Original-test success (%)',ylim=(0,100),xlim=(0,max(r['api_equivalent_usd'] for r in all_groups)*120))
    ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.18)
    fig.savefig(ROOT/'figures/heldout_cost_quality.pdf');fig.savefig(ROOT/'figures/heldout_cost_quality.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.7,3.6),layout='constrained')
    x=list(range(len(all_groups)));base=[0.0]*len(x)
    parts=[('Uncached input',[r['input_tokens']-r['cached_input_tokens'] for r in all_groups],'#476b85'),
           ('Cached input',[r['cached_input_tokens'] for r in all_groups],'#9dc4d4'),
           ('Output (includes reasoning)',[r['output_tokens'] for r in all_groups],'#bf813e')]
    for label,values,color in parts:
        scaled=[value/1000 for value in values]
        ax.bar(x,scaled,bottom=base,label=label,color=color,width=.65)
        base=[a+b for a,b in zip(base,scaled)]
    ax.set(xticks=x,xticklabels=[r['code'] for r in all_groups],ylabel='Mean thousand tokens / completed candidate',ylim=(0,max(base)*1.23))
    ax.legend(frameon=False,fontsize=8,loc='upper left',ncol=3)
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.savefig(ROOT/'figures/heldout_token_components.pdf');fig.savefig(ROOT/'figures/heldout_token_components.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.7,3.1),layout='constrained')
    for y,(key,label) in enumerate(zip(KEYS,LABELS)):
        q=s['paired_contrasts'][key]['quality'];lo,hi=q['descriptive_task_bootstrap_95_interval'];mean=q['mean_paired_difference']
        ax.plot([100*lo,100*hi],[y,y],color='#0c6470',lw=2)
        ax.scatter(100*mean,y,color='#0c6470',s=40,zorder=3)
    ax.axvline(0,color='#777777',ls='--',lw=1)
    ax.set(yticks=range(4),yticklabels=LABELS,xlabel='Paired test-success difference (percentage points)',ylim=(3.5,-.5))
    ax.spines[['top','right','left']].set_visible(False);ax.grid(axis='x',alpha=.18)
    fig.savefig(ROOT/'figures/heldout_quality_effects.pdf');fig.savefig(ROOT/'figures/heldout_quality_effects.png',dpi=180);plt.close(fig)
    (ROOT/'reproducibility/revision/heldout_rendered_values.json').write_text(json.dumps({'groups':all_groups,'source_summary':str(primary/'summary.json'),'source_inot':str(inot/'summary.json')},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('primary','inot','paired','selection'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();render(a.primary,a.inot,a.paired,a.selection)
