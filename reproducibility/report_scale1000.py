"""Render completed primary evidence into bilingual manuscript tables and figures."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'reproducibility/results/20260912_scale1000_luna_full'
ORDER=('direct','single_neutral','single_roles','multi_neutral','multi_roles')
LABELS=dict(zip(ORDER,('D','SN','SR','MN','MR')))
CONTRASTS=('single_roles_minus_single_neutral','multi_roles_minus_multi_neutral','multi_neutral_minus_single_neutral','multi_roles_minus_single_roles')
NAMES=('SR -- SN','MR -- MN','MN -- SN','MR -- SR')

def interval(values,scale=1):return '$['+', '.join(f'{v*scale:.2f}' for v in values)+']$'
def probability(p):
    if p>=.0001:return f'{p:.4f}'
    base,exponent=f'{p:.2e}'.split('e');return '$'+base+r'\times10^{'+str(int(exponent))+'}$'

def table(caption,label,columns,header,rows,footnote):
    return '\n'.join([r'\begin{table}[htbp]\centering\small',r'\caption{'+caption+'}',r'\label{'+label+'}',
        r'\begin{tabular}{'+columns+r'}\toprule',header+r'\\\midrule',
        *[r' & '.join(row)+r'\\' for row in rows],r'\bottomrule\end{tabular}',
        r'\par\smallskip\noindent '+footnote,r'\end{table}',''])

def main():
    summary=json.loads((ARCHIVE/'analysis/summary.json').read_text(encoding='utf-8'))
    arms={r['arm']:r for r in summary['by_arm']}
    for lang in ('en','ru'):
        en=lang=='en'
        rows=[]
        for name in ORDER:
            r=arms[name]
            assert abs(r['passes']/r['known_repeat_outcomes']-r['pass_rate_observed'])<1e-12
            rows.append([LABELS[name],str(r['assigned']),str(r['generation_complete']),str(r['known_repeat_outcomes']),str(r['passes']),f"{100*r['pass_rate_observed']:.2f}"])
        text=table('Luna factorial study: assignment and observation counts.' if en else 'Факторный эксперимент Luna: назначения и наблюдаемые исходы.',
            'tab:scale-quality','lrrrrr',
            'Condition & Assigned & Generated & Observed & Passes & Success (\%)' if en else 'Условие & Назначено & Получено & Оценено & Успехов & Успех (\%)',rows,
            'Observed means eligible native quality endpoints, not distinct tasks. Success divides passes by observed repeat outcomes. Each condition has three assigned repeats per task.' if en else 'Оценено: доступные исходы качества после контроля пригодности, а не число разных задач. Процент успеха равен числу успехов, делённому на число оценённых повторов. В каждом условии назначены три повтора на задачу.')
        (ROOT/f'sections/scale1000_quality_{lang}.tex').write_text(text,encoding='utf-8')
        rows=[]
        for name,label in zip(CONTRASTS,NAMES):
            r=summary['contrasts'][name]
            rows.append([label,str(r['eligible_tasks']),f"${r['mean_difference']*100:+.2f}$",interval(r['bootstrap_95'],100),probability(r['holm_p']),interval(r['full_assignment_quality_difference_bounds'],100)])
        text=table('Luna factorial quality contrasts. Differences and bounds are percentage points.' if en else 'Сравнения качества в эксперименте Luna. Разности и границы указаны в процентных пунктах.',
            'tab:scale-contrasts','lrrrrr',
            'Contrast & Tasks & Difference & 95\% interval & Holm $p$ & Assigned bounds' if en else 'Сравнение & Задач & Разность & 95\%-й интервал & $p$ Холма & Границы',rows,
            'Tasks require three observed repeats in each compared condition. Assigned bounds use all 1,000 tasks and every assigned repeat; they are not confidence intervals.' if en else 'Для включения задачи нужны три наблюдаемых повтора в каждом из сравниваемых условий. Границы учитывают все 1\,000 задач и все назначенные повторы; это не доверительные интервалы.')
        (ROOT/f'sections/scale1000_contrasts_{lang}.tex').write_text(text,encoding='utf-8')
        rows=[]
        for name,label in zip(CONTRASTS,NAMES):
            r=summary['resource_contrasts'][name];u=r['api_equivalent_usd'];t=r['total_tokens']
            rows.append([label,str(u['eligible_tasks']),f"{t['ratio_of_task_mean_sums']:.3f}",f"{u['ratio_of_task_mean_sums']:.3f}",interval(u['ratio_bootstrap_95']),f"{r['uncached_sensitivity_usd']['ratio_of_task_mean_sums']:.3f}"])
        text=table('Luna factorial resource ratios: first condition divided by second.' if en else 'Отношения расхода ресурсов в эксперименте Luna: первое условие делится на второе.',
            'tab:scale-resources','lrrrrr',
            'Contrast & Tasks & Tokens & Valuation & 95\% interval & No cache' if en else 'Сравнение & Задач & Токены & Оценка & 95\%-й интервал & Без кэша',rows,
            'Ratios divide sums of three-repeat task means on complete resource pairs. The displayed interval is for the API-equivalent valuation ratio. No cache removes its input-cache discount; subscription billing is not estimated.' if en else 'Отношения делят суммы средних по трём повторам на задачах с полными ресурсными записями в обоих условиях. Интервал относится к отношению денежных оценок по тарифам API. Последний столбец убирает скидку за кэш входа; платежи за подписку не оцениваются.')
        (ROOT/f'sections/scale1000_resources_{lang}.tex').write_text(text,encoding='utf-8')
        plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42})
        fig,ax=plt.subplots(figsize=(6.6,2.65),layout='constrained')
        for i,name in enumerate(CONTRASTS):
            r=summary['contrasts'][name];point=r['mean_difference']*100;lo,hi=[v*100 for v in r['bootstrap_95']]
            ax.errorbar(point,3-i,xerr=[[point-lo],[hi-point]],fmt='o',color='#173f5f',capsize=4)
        ax.axvline(0,color='#777777',linewidth=.8,linestyle='--')
        ax.set_yticks([3,2,1,0],[n.replace(' -- ',' − ') for n in NAMES])
        ax.set_xlabel('Quality difference (percentage points)' if en else 'Разность качества (процентные пункты)')
        ax.set_xlim(-6.5,3.3);ax.set_ylim(-.6,3.6);ax.grid(axis='x',alpha=.15)
        ax.spines[['top','right']].set_visible(False)
        suffix='' if en else '_ru'
        fig.savefig(ROOT/f'figures/scale1000_quality_effects{suffix}.pdf');plt.close(fig)
    print('Rendered six tables and two vector figures from verified primary summary.')

if __name__=='__main__':main()
