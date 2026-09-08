"""Render development result tables and figures from reconciled native records."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'reproducibility/results/20260908_codex_mini_dev40/analysis'
ARMS = ('direct', 'single_neutral', 'single_roles', 'multi_neutral', 'multi_roles')
CODES = dict(zip(ARMS, ('D', 'SN', 'SR', 'MN', 'MR')))


def main():
    s = json.loads((DATA / 'summary.json').read_text(encoding='utf-8'))
    rows = [json.loads(x) for x in (DATA / 'candidate_records.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows) == s['recorded_attempts'] == 400
    groups = {x['arm']: x for x in s['by_arm']}
    bykey = {(r['task_id'], r['arm'], r['replicate_id']): r for r in rows}
    ids = sorted({r['task_id'] for r in rows}, key=lambda x: int(x.split('/')[-1]))
    contrast_order = ['roles_minus_neutral_single', 'roles_minus_neutral_multi',
                      'multi_minus_single_neutral', 'multi_minus_single_roles',
                      'single_neutral_minus_direct', 'multi_roles_minus_direct']
    labels = ['SR - SN', 'MR - MN', 'MN - SN', 'MR - SR', 'SN - D', 'MR - D']
    for lang in ('en', 'ru'):
        cap = ('Development results: 80 assigned candidates per condition, two repeats on 40 tasks. Quality uses 78 evaluable attempts; resource means use all 80. Missingness ranges use the full assignment denominator and are not confidence intervals.'
               if lang == 'en' else 'Результаты на выборке разработки: по 80 назначений на условие, два повтора на 40 задачах. Качество рассчитано по 78 оцениваемым попыткам, ресурсы --- по всем 80. Границы пропусков относятся ко всем назначениям и не являются доверительными интервалами.')
        header = ('Arm & Passes & Rate (\\%) & Range (\\%) & Tokens & USD & No cache\\\\'
                  if lang == 'en' else 'Усл. & Прошло & Доля (\\%) & Границы (\\%) & Токены & USD & Без кеша\\\\')
        text = ['\\begin{table}[htbp]\\centering\\small', '\\caption{' + cap + '}\\label{tab:dev40-main}',
                '\\begin{tabular}{lrrrrrr}\\toprule', header, '\\midrule']
        for arm in ARMS:
            r = groups[arm]
            text.append(f"{CODES[arm]} & {r['passes']}/{r['evaluable_attempts']} & {100*r['evaluable_only_rate']:.2f} & {100*r['pessimistic_lower_bound']:.2f}--{100*r['optimistic_upper_bound']:.2f} & {r['mean_total_tokens']:,.0f}".replace(',', '\\,')
                        + f" & {r['mean_api_equivalent_usd']:.5f} & {r['mean_uncached_sensitivity_usd']:.5f}\\\\")
        text += ['\\bottomrule\\end{tabular}\\end{table}']
        (ROOT / f'sections/dev40_table_{lang}.tex').write_text('\n'.join(text)+'\n', encoding='utf-8')

        caption = ('Every development task and both repeats. Each pair of letters gives repeats 2 and 3 in order: P = pass, F = fail, U = unavailable. These are original test statuses after the reference eligibility gate; disputed tests have not been deleted.'
                   if lang == 'en' else 'Все задачи разработки и оба повтора. В каждой паре буквы обозначают повторы 2 и 3: P --- тесты пройдены, F --- не пройдены, U --- качество недоступно. Приведены исходные оценки с учётом эталонного контроля; спорные тесты не удалены.')
        text = ['\\begin{table}[!htbp]\\centering\\footnotesize', '\\caption{'+caption+'}\\label{tab:dev40-all}',
                '\\begin{tabular*}{\\textwidth}{@{\\extracolsep{\\fill}}rrrrrr}\\toprule', 'ID & D & SN & SR & MN & MR\\\\\\midrule']
        for task in ids:
            values = []
            for arm in ARMS:
                values.append(''.join('U' if bykey[task, arm, rep]['analysis_status'] is None else 'P' if bykey[task, arm, rep]['analysis_status'] == 'pass' else 'F' for rep in (2, 3)))
            text.append(task.split('/')[-1]+' & '+' & '.join(values)+'\\\\')
        text += ['\\bottomrule\\end{tabular*}\\end{table}']
        (ROOT / f'sections/dev40_tasks_{lang}.tex').write_text('\n'.join(text)+'\n', encoding='utf-8')

        cap = ('Paired development contrasts. Quality differences and descriptive 95\\% task-bootstrap intervals are percentage points over 39 complete task clusters; resource ratios use 40. The last two comparisons are exploratory. No confirmatory p-value or non-inferiority test is assigned.'
               if lang == 'en' else 'Парные сравнения на выборке разработки. Разности качества и описательные 95\\%-интервалы бутстрэпа по задачам даны в процентных пунктах для 39 полных пар; отношения ресурсов --- для 40 задач. Последние два сравнения поисковые. Подтверждающие p-значения и тест неухудшения не применяются.')
        header = ('Contrast & Quality difference [interval] & Token ratio & USD ratio\\\\' if lang == 'en' else 'Контраст & Разность качества [интервал] & Токены, отн. & USD, отн.\\\\')
        text = ['\\begin{table}[htbp]\\centering\\small', '\\caption{'+cap+'}\\label{tab:dev40-contrasts}',
                '\\begin{tabular}{lrrr}\\toprule', header, '\\midrule']
        for key, label in zip(contrast_order, labels):
            r = s['paired_contrasts'][key]; q = r['quality']; lo, hi = q['descriptive_task_bootstrap_95_interval']
            text.append(f"{label} & ${100*q['mean_paired_difference']:+.2f}\;[{100*lo:+.2f},{100*hi:+.2f}]$ & {r['total_tokens']['ratio_of_paired_means']:.3f} & {r['api_equivalent_usd']['ratio_of_paired_means']:.3f}\\\\")
        text += ['\\bottomrule\\end{tabular}\\end{table}']
        (ROOT / f'sections/dev40_contrasts_{lang}.tex').write_text('\n'.join(text)+'\n', encoding='utf-8')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'pdf.fonttype': 42})
    fig, ax = plt.subplots(figsize=(6.7, 3.6), layout='constrained')
    for index, arm in enumerate(ARMS):
        r = groups[arm]
        ax.scatter(100*r['mean_api_equivalent_usd'], 100*r['evaluable_only_rate'], s=65, color=['#0c6470','#536e8a','#378b70','#a66d38','#946396'][index])
        ax.annotate(CODES[arm], (100*r['mean_api_equivalent_usd'],100*r['evaluable_only_rate']),xytext=(5,-16) if arm == 'multi_roles' else (5,5),textcoords='offset points')
    ax.set(xlabel='Mean API-equivalent valuation (US cents / candidate)', ylabel='Original-test success (%)', ylim=(0, 100), xlim=(0, 3.2))
    ax.spines[['top','right']].set_visible(False); ax.grid(alpha=.18)
    out = ROOT / 'figures'; out.mkdir(exist_ok=True)
    fig.savefig(out/'dev40_cost_quality.pdf'); fig.savefig(out/'dev40_cost_quality.png', dpi=180); plt.close(fig)


if __name__ == '__main__':
    main()
