"""Render bilingual tables and a scientific effect plot from audited outcomes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ARMS=('role_boundary','neutral_boundary','role_prose','neutral_prose')
CODES=dict(zip(ARMS,('RB','NB','RP','NP')))
KEYS=('role_boundary_minus_neutral_boundary','role_prose_minus_neutral_prose',
      'boundary_minus_prose_role','boundary_minus_prose_neutral')
LABELS=('RB - NB','RP - NP','RB - RP','NB - NP')


def render(summary, records, selection, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    s=json.loads(summary.read_text(encoding='utf-8'))
    rows=[json.loads(line) for line in records.read_text(encoding='utf-8').splitlines() if line.strip()]
    ids=json.loads(selection.read_text(encoding='utf-8'))['assigned_task_ids']
    if len(rows)!=320 or s['assigned_candidates']!=320:raise ValueError('All 320 assigned records are required')
    index={(r['task_id'],r['arm']):r for r in rows}
    out.mkdir(parents=True,exist_ok=True)
    def write(name,lines):(out/name).write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    groups={r['arm']:r for r in s['by_arm']}
    for lang in ('en','ru'):
        en=lang=='en'
        caption=('Independent 80-task extension. RB/NB: role/neutral labels with headings; RP/NP: the same labels in prose. V is mean standard API-equivalent valuation per observed candidate, not an invoice.' if en else
                 'Независимое дополнение на 80 задачах. RB/NB: ролевые/нейтральные обозначения с заголовками; RP/NP: те же обозначения в абзаце. V --- средняя стандартная условная API-стоимость наблюдаемого кандидата, а не платёж.')
        table=['\\begin{table}[t]\\centering\\small','\\caption{'+caption+'}\\label{tab:seg80-groups}',
               r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrrrr}\toprule',
               ('Arm & Generated & Passed/eligible & Pass (\\%) & Tokens & V (USD)\\\\' if en else
                'Режим & Получено & Успех/оценено & Успех (\\%) & Токены & V (USD)\\\\'),r'\midrule']
        for arm in ARMS:
            r=groups[arm]
            table.append(f"{CODES[arm]} & {r['generation_complete']}/80 & {r['passes']}/{r['quality_observed']} & {100*r['pass_rate']:.2f} & {r['mean_total_tokens']:.0f} & {r['mean_api_equivalent_usd']:.6f}\\\\")
        table += [r'\bottomrule\end{tabular*}\end{table}']
        write(f'groups_{lang}.tex',table)
        caption=('The two prespecified role contrasts. Differences and descriptive task-bootstrap 95\\% intervals are in percentage points. W/L counts discordant pairs; Holm correction covers both exact two-sided McNemar tests.' if en else
                 'Два заранее заданных ролевых контраста. Разности и описательные 95\\%-интервалы бутстрэпа по задачам даны в процентных пунктах. W/L --- дискордантные пары; поправка Холма охватывает оба точных двусторонних теста Мак-Немара.')
        table=['\\begin{table}[t]\\centering\\small','\\caption{'+caption+'}\\label{tab:seg80-tests}',
               r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrrrr}\toprule',
               ('Contrast & Pairs & Difference [interval] & W/L & $p$ & $p_{\\rm Holm}$\\\\' if en else
                'Контраст & Пары & Разность [интервал] & W/L & $p$ & $p_{\\rm Holm}$\\\\'),r'\midrule']
        for key,label in zip(KEYS[:2],LABELS[:2]):
            r=s['contrasts'][key];lo,hi=r['quality_bootstrap_95']
            table.append(f"{label} & {r['quality_pairs']} & ${100*r['quality_difference']:+.2f}\\;[{100*lo:+.2f},{100*hi:+.2f}]$ & {r['wins']}/{r['losses']} & {r['exact_two_sided_mcnemar_p']:.4f} & {r['holm_p']:.4f}\\\\")
        table += [r'\bottomrule\end{tabular*}\end{table}'];write(f'tests_{lang}.tex',table)
        # All 80 tasks are listed, using two 40-row panels; no candidate is suppressed.
        cap=('All 80 assigned tasks in the original random allocation order. P/F: eligible pass/fail; CP/CF: native pass/fail with unavailable control, excluded from quality inference; M: missing generation/evaluation. IDs abbreviate BigCodeBench/n. Each half has columns RB, NB, RP, NP.' if en else
             'Все 80 назначенных задач в исходном случайном порядке. P/F: оцениваемый успех/неуспех; CP/CF: нативный успех/неуспех при непригодном контроле, вне статистики качества; M: нет генерации/оценки. Идентификаторы сокращают BigCodeBench/n. В каждой половине столбцы RB, NB, RP, NP.')
        table=['\\begin{table}[htbp]\\centering\\scriptsize','\\caption{'+cap+'}\\label{tab:seg80-all}',
               r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}rccccrcccc}\toprule',
               r'ID & RB & NB & RP & NP & ID & RB & NB & RP & NP\\\midrule']
        def taskrow(t):
            cells=[]
            for a in ARMS:
                r=index[t,a]
                if r['outcome_type']=='control_unavailable':
                    cells.append('CP' if r['native_status']=='pass' else 'CF' if r['native_status'] in ('fail','timeout') else 'M')
                else:
                    cells.append('P' if r['quality'] is True else 'F' if r['quality'] is False else 'M')
            return ' & '.join([t.split('/')[-1],*cells])
        for i in range(40):table.append(taskrow(ids[i])+' & '+taskrow(ids[i+40])+r'\\')
        table += [r'\bottomrule\end{tabular*}\end{table}'];write(f'tasks_{lang}.tex',table)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(7.1,3.1),layout='constrained')
    for j,(ax,metric,scale,label) in enumerate(zip(axes,('quality','api_equivalent_usd'),(100,100),('Quality difference (percentage points)','Mean valuation difference (US cents)'))):
        ax.axvline(0,color='#888888',lw=.8,zorder=0)
        for i,key in enumerate(KEYS):
            r=s['contrasts'][key]
            mean=r['quality_difference'] if metric=='quality' else r[metric]['mean_difference']
            lo,hi=r['quality_bootstrap_95'] if metric=='quality' else r[metric]['descriptive_bootstrap_95']
            color='#145c75' if i<2 else '#707070'
            ax.plot([lo*scale,hi*scale],[i,i],color=color,lw=1.6)
            ax.plot(mean*scale,i,'o',color=color,ms=5)
        ax.set_yticks(range(4),LABELS);ax.invert_yaxis();ax.set_xlabel(label);ax.grid(axis='x',alpha=.18)
        ax.set_title(('A. Quality','B. Resources')[j],loc='left',fontweight='bold')
    fig.savefig(out/'effects.pdf',metadata={'CreationDate':None,'ModDate':None});fig.savefig(out/'effects.png',dpi=180);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('summary','records','selection','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();render(a.summary,a.records,a.selection,a.out)
