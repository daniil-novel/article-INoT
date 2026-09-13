"""Render the verified SCC-2000 archive as a bilingual presentation package.

The renderer is deliberately downstream-only: it reads the completed archive,
does not rerun analysis, and never turns an absent endpoint into a failure.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any
from reproducibility.evidence_manifest import verify as verify_evidence

METHODS = ("single_neutral", "single_roles", "scc_author_2024_codex_transport")
LABELS = dict(zip(METHODS, ('SN', 'SR', 'SCC')))
CONTRASTS = tuple('scc_author_2024_codex_transport-minus-'+right for right in ('single_roles', 'single_neutral'))
REPLICATES = (101, 102, 103)
CSV_FIELDS = ("id", "task_id", "method", "replicate_id", "selected", "control_eligible",
              "generation_complete", "observed_candidate", "availability", "format_extracted",
              "format_status", "native_status", "status_state", "quality", "outcome_type", "display_code")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _value(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def display_code(row: dict[str, Any]) -> str:
    """Return P/F/T/X/G/U/N while preserving unknown as unknown."""
    q = row.get("quality")
    candidate = _value(row, "observed_candidate", "candidate_available")
    eligible = row.get("control_eligible")
    native = row.get("native_status")
    extracted = _value(row, "format_extracted", "format_extracted_recorded")
    if q is not None and type(q) is not bool:
        raise ValueError("quality must be boolean or null")
    if type(candidate) is not bool or type(eligible) is not bool:
        raise ValueError("candidate and control eligibility must be boolean")
    if not candidate:
        if q is not None or native is not None:
            raise ValueError("unavailable candidate has an observed endpoint")
        return "G"
    if not eligible:
        if q is not None:
            raise ValueError("control-ineligible task has an observed endpoint")
        return "U"
    if q is None:
        if native in {"pass", "fail", "timeout"}:
            raise ValueError("eligible candidate has native evidence but unknown quality")
        return "N"
    if q:
        if native != "pass" or extracted is not True:
            raise ValueError("success contradicts native or format evidence")
        return "P"
    if extracted is False:
        return "X"
    if native == "fail":
        return "F"
    if native == "timeout":
        return "T"
    raise ValueError("failure lacks native or format evidence")


def _manifest_paths(archive: Path) -> tuple[Path, Path, Path, Path]:
    # The amended analysis is the final analysis for the frozen 6,000-cell prefix.
    summary = archive / "amended-analysis" / "summary.json"
    evidence = archive / "EVIDENCE_MANIFEST.json"
    generation = archive / "generation" / "manifest.json"
    selection = archive / "amendment" / "selection_manifest.json"
    missing = [str(p.relative_to(archive)) for p in (summary, evidence, generation, selection) if not p.is_file()]
    if missing:
        raise ValueError("completed final analysis/manifest is missing: " + ", ".join(missing))
    status = archive / "generation" / "status.json"
    continuation = archive / "generation" / "continuation_status.json"
    if not continuation.is_file() or _read(continuation).get("state") != "completed":
        raise ValueError("presentation requires completed generation/continuation_status.json")
    try:
        verify_evidence(archive)
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("archive EVIDENCE_MANIFEST.json does not verify") from exc
    return summary, evidence, generation, selection


def _records(archive: Path, selected: set[str]) -> list[dict[str, Any]]:
    paths = (archive / "selected_assignment_records.jsonl", archive / "candidate_records.jsonl")
    path = next((p for p in paths if p.is_file()), None)
    if path is None:
        raise ValueError("completed archive lacks assignment ledger")
    rows = [_read_json_line(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if str(r.get("id", r.get("cell_id", ""))) in selected]
    if len(rows) != 6000 or len({str(r.get("id", r.get("cell_id", ""))) for r in rows}) != 6000:
        raise ValueError("selected presentation ledger must contain exactly 6,000 unique rows")
    return rows


def _read_json_line(line: str) -> dict[str, Any]:
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("ledger rows must be objects")
    return value


def project_rows(archive: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load the selected 6,000 rows and summary from a verified archive."""
    archive = archive.resolve()
    summary_path, _, _, selection_path = _manifest_paths(archive)
    selection = _read(selection_path)
    ids = [str(x) for x in selection.get("selected_ids", [])]
    if len(ids) != 6000 or len(set(ids)) != 6000:
        raise ValueError("selection manifest must contain exactly 6,000 selected IDs")
    cells = selection.get("selected_cells")
    if not isinstance(cells, list) or len(cells) != 6000:
        raise ValueError("selection manifest must contain 6,000 selected identity triples")
    cells_by_id = {c['id']: c for c in cells}
    if len(cells_by_id) != 6000 or [c['id'] for c in cells] != ids:
        raise ValueError('frozen selected cells do not match ordered selected IDs')
    rows = _records(archive, set(ids))
    by_id = {str(r.get("id", r.get("cell_id"))): r for r in rows}
    if set(by_id) != set(ids):
        raise ValueError("selected ledger IDs differ from frozen selection")
    gate = archive / "controls" / "heldout200_control_gate.json"
    gate_data = _read(gate)
    eligible = set(gate_data['evaluable_task_ids'])
    selected_tasks = {c['task_id'] for c in cells}
    if gate_data.get('controls_complete') is not True or len(eligible & selected_tasks) != 941:
        raise ValueError('selected control eligibility differs from the frozen 941 tasks')
    summary = _read(summary_path)
    if summary.get('schema') != 'scc2000-analysis-v1' or summary.get('selected_rows') != 6000 or summary.get('task_count') != 956 or summary.get('eligible_task_count') != 941:
        raise ValueError('final amended summary has the wrong study scope')
    if set(summary.get('contrasts', {})) != set(CONTRASTS) or set(summary.get('resources', {})) != set(CONTRASTS):
        raise ValueError('final amended summary lacks both primary contrasts and resources')
    projected = []
    for r in rows:
        ident = str(r.get("id", r.get("cell_id")))
        task = str(r.get("task_id")); method = str(r.get("method")); rep = int(r.get("replicate_id"))
        candidate = r.get('observed_candidate')
        if type(candidate) is not bool or type(r.get('generation_complete')) is not bool or candidate != r['generation_complete']:
            raise ValueError('completed archive has inconsistent candidate availability')
        if candidate and type(r.get('format_extracted')) is not bool:
            raise ValueError('completed candidate lacks a format assessment')
        q = r.get("quality")
        expected = cells_by_id.get(ident)
        if expected is None or str(expected.get("task_id")) != task or str(expected.get("method")) != method or int(expected.get("replicate_id")) != rep:
            raise ValueError("selected row identity differs from frozen task/method/repeat triple")
        item = {"id": ident, "task_id": task, "method": method, "replicate_id": rep,
                "selected": True, "control_eligible": task in eligible,
                "generation_complete": r.get("generation_complete"), "observed_candidate": candidate,
                "availability": _value(r, "availability", "availability_recorded"),
                "format_extracted": _value(r, "format_extracted", "format_extracted_recorded"),
                "format_status": r.get("format_status"), "native_status": r.get("native_status"),
                "status_state": r.get("status_state"),
                "quality": q, "outcome_type": r.get("outcome_type")}
        item["display_code"] = display_code(item)
        projected.append(item)
    if len({x["task_id"] for x in projected}) != 956:
        raise ValueError("selected presentation must contain the frozen 956 tasks")
    return projected, summary


def _cell(row: dict[str, Any] | None) -> str:
    return "—" if row is None else row["display_code"]


def appendix_table(rows: list[dict[str, Any]], language: str, rows_per_table: int = 40) -> str:
    """Create a 9-method-repeat-column task appendix; em dash means unselected."""
    if language not in {"en", "ru"} or rows_per_table < 1:
        raise ValueError("language must be en or ru")
    tasks = sorted({r["task_id"] for r in rows}, key=lambda x: int(x.rsplit("/", 1)[-1]))
    index = {(r["task_id"], r["method"], r["replicate_id"]): r for r in rows}
    title = "SCC comparison: selected task-repeat outcomes" if language == "en" else "Сравнение SCC: исходы выбранных повторов"
    control = "Control" if language == "en" else "Контроль"
    legend = ('P: pass; F: test failure; T: timeout; X: format failure; G: incomplete generation; N: missing native outcome; U: control-ineligible. A dash means outside the selected prefix.' if language == 'en' else
              'P: успех; F: неуспех теста; T: тайм-аут; X: ошибка формата; G: незавершённая генерация; N: нет нативной оценки; U: непригодность по контролю. Тире означает назначение вне выбранной серии.')
    text = []
    for start in range(0, len(tasks), rows_per_table):
        text += [r'\begin{table}[p]\centering\small',
                 r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}rc*{9}{c}@{}}\toprule',
                 'ID & '+control+' & '+' & '.join(r'\multicolumn{3}{c}{'+LABELS[m]+'}' for m in METHODS)+r'\\',
                 r'\cmidrule(lr){3-5}\cmidrule(lr){6-8}\cmidrule(lr){9-11}',
                 ' & & '+' & '.join(str(rep) for _ in METHODS for rep in REPLICATES)+r'\\\midrule']
        for task in tasks[start:start + rows_per_table]:
            present = [index.get((task, m, rep)) for m in METHODS for rep in REPLICATES]
            eligible = next((r["control_eligible"] for r in present if r), False)
            gate = ("yes" if eligible else "no") if language == "en" else ("да" if eligible else "нет")
            text.append(" & ".join([task.rsplit("/", 1)[-1], gate] + [_cell(r) for r in present]) + r"\\")
        part = start // rows_per_table + 1; total = (len(tasks) + rows_per_table - 1) // rows_per_table
        part_title = f'part {part} of {total}' if language == 'en' else f'часть {part} из {total}'
        text += [r'\bottomrule\end{tabular*}', f'\\caption{{{title}, {part_title}. {legend}}}', r'\end{table}', r'\clearpage']
    return "\n".join(text) + "\n"


def _fmt(x: Any, scale: float = 1, places: int = 2) -> str:
    if x is None:
        return '---'
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        if not math.isfinite(x):
            raise ValueError('non-finite presentation value')
        return str(x) if isinstance(x, int) and scale == 1 else f'{x*scale:.{places}f}'
    return str(x).replace('_', r'\_')


def _short_label(name: str) -> str:
    for method, label in LABELS.items():
        name = name.replace(method, label)
    return name.replace('-minus-', ' -- ')


def _interval(values: Any, scale: float = 1) -> str:
    if values is None:
        return '---'
    if len(values) != 2:
        raise ValueError('interval requires exactly two bounds')
    return '$['+', '.join(_fmt(x, scale) for x in values)+']$'


def _probability(value: float | None) -> str:
    if value is None:
        return '---'
    if not 0 <= value <= 1:
        raise ValueError('probability outside the unit interval')
    if value == 0:
        return r'\textit{underflow}'
    if value >= .0001:
        return f'{value:.4f}'
    mantissa, exponent = f'{value:.2e}'.split('e')
    return '$'+mantissa+r'\times10^{'+str(int(exponent))+'}$'


def _table(caption: str, label: str, headers: list[str], rows: list[list[str]], footnote: str) -> str:
    return '\n'.join([r'\begin{table}[htbp]\centering\small',
        r'\caption{'+caption+'}', r'\label{'+label+'}',
        r'\begin{tabular}{l'+('r'*(len(headers)-1))+r'}\toprule',
        ' & '.join(headers)+r'\\\midrule',
        *[' & '.join(row)+r'\\' for row in rows],
        r'\bottomrule\end{tabular}', r'\par\smallskip\noindent '+footnote,
        r'\end{table}', ''])


def summary_tables(summary: dict[str, Any], language: str) -> str:
    """Format saved estimands without pooling different task or repeat subsets."""
    if language not in ('en', 'ru'):
        raise ValueError('unknown presentation language')
    en = language == 'en'
    totals = {method: Counter() for method in METHODS}
    for row in summary['restart_diagnostics']['known_subtotals_by_method_segment']:
        for field in ('assigned', 'generation_complete', 'quality_observed', 'passes'):
            totals[row['method']][field] += row[field]
    rows = []
    for method in METHODS:
        row = totals[method]
        if row['assigned'] != 2000:
            raise ValueError('method assignment denominator differs from selected blocks')
        known = row['quality_observed']
        rows.append([LABELS[method], str(row['assigned']), str(row['generation_complete']),
            str(known), str(row['passes']), _fmt(100*row['passes']/known if known else None)])
    parts = [_table('SCC comparison: observed outcomes.' if en else 'Сравнение SCC: наблюдаемые исходы.',
        'tab:scc2000-quality',
        ['Method', 'Assigned', 'Generated', 'Observed', 'Passes', 'Success (\\%)'] if en else
        ['Метод', 'Назначено', 'Получено', 'Оценено', 'Успехов', 'Успех (\\%)'], rows,
        'Observed counts are eligible repeat outcomes. The percentage is passes divided by observed repeats; it is not a task-weighted contrast. Interrupted workflows remain unavailable.' if en else
        'Оценено: пригодные исходы отдельных повторов. Процент равен числу успехов, делённому на число оценённых повторов; он не является парной оценкой с равными весами задач. Прерванные процессы остаются недоступными.')]
    rows = []
    for name in CONTRASTS:
        row = summary['contrasts'][name]
        p = row['holm_adjusted_p'] if row['p_two_sided'] is not None else None
        rows.append([_short_label(name), str(row['n_tasks']), _fmt(row['mean_difference'], 100),
            _interval(row['bootstrap']['ci95'], 100), _probability(p)])
    parts.append(_table('Paired quality differences (percentage points).' if en else 'Парные разности качества (процентные пункты).',
        'tab:scc2000-contrasts', ['Contrast', 'Tasks', 'Difference', '95\\% interval', 'Holm $p$'] if en else
        ['Сравнение', 'Задачи', 'Разность', '95\\% интервал', '$p$ Холма'], rows,
        'Selected matched repeats are averaged within each task; tasks have equal weight. The two tests form a separate Holm family. The 95\\% bootstrap intervals are descriptive. A dash denotes an unavailable or unestimable quantity.' if en else
        'Выбранные парные повторы сначала усредняются внутри каждой задачи; веса задач равны. Два теста образуют отдельное семейство Холма. Бутстрэп-интервалы 95\\% являются описательными. Тире обозначает недоступную или неоцениваемую величину.'))
    rows = []
    for name in CONTRASTS:
        for scope in ('eligible_selected', 'all_selected'):
            row = summary['bounds'][scope][name]
            scope_label = ('Eligible' if en else 'Пригодные') if scope == 'eligible_selected' else ('All selected' if en else 'Все выбранные')
            rows.append([_short_label(name)+' ('+scope_label+')', str(row['task_count']),
                _interval([row['lower'], row['upper']], 100), str(row['unknown_task_pairs'])])
    parts.append(_table('Bounds over assigned outcomes (percentage points).' if en else 'Границы по назначенным исходам (процентные пункты).',
        'tab:scc2000-bounds', ['Comparison and scope', 'Tasks', 'Bounds', 'Tasks with unknowns'] if en else
        ['Сравнение и выборка', 'Задачи', 'Границы', 'С пропусками'], rows,
        'Each task retains its number of selected assigned repeats in the denominator. These are identification bounds, not confidence intervals.' if en else
        'В знаменателе каждой задачи сохраняется число выбранных назначенных повторов. Это границы возможных эффектов, а не доверительные интервалы.'))
    for estimator in ('pooled', 'mean_ratio'):
        rows = []
        for name in CONTRASTS:
            row = summary['resources'][name]
            if estimator == 'pooled':
                point, ci, n = row['ratio_of_paired_means'], row['ratio_of_means_bootstrap']['ci95'], row['complete_task_pairs']
            else:
                point, ci, n = row['mean_task_ratio']['mean'], row['mean_task_ratio']['ci95'], row['positive_ratio_denominator_pairs']
            rows.append([_short_label(name).replace(' -- ', ' / '), str(n), _fmt(point, places=3), _interval(ci)])
        title = ('Ratio of paired task-mean valuations.' if en else 'Отношение средних парных оценок стоимости.') if estimator == 'pooled' else ('Mean of task-level valuation ratios.' if en else 'Среднее отношений стоимости по задачам.')
        parts.append(_table(title, 'tab:scc2000-resource-'+estimator,
            ['Comparison', 'Tasks', 'Ratio', '95\\% interval'] if en else ['Сравнение', 'Задачи', 'Отношение', '95\\% интервал'], rows,
            'Only matched complete workflows with valid counters enter these descriptive estimates. API-equivalent valuations are not subscription payments; partial known totals are accounted for separately.' if en else
            'В описательные оценки входят только парные завершённые процессы с полными счётчиками. Оценка по API-тарифам не равна платежу по подписке; известные частичные расходы учитываются отдельно.'))
    rows = []
    family_labels = {'union_070_code_exact': 'Code + prompt 0.70', 'prompt_050': 'Prompt 0.50', 'prompt_070': 'Prompt 0.70', 'prompt_090': 'Prompt 0.90'}
    for family, values in summary['source_component_bootstrap'].items():
        for name in CONTRASTS:
            row = values[name]
            rows.append([family_labels[family]+'; '+_short_label(name), str(row['component_count']),
                str(row['task_count']), _interval(row.get('ci95'), 100)])
    parts.append(_table('Source-group sensitivity (percentage points).' if en else 'Чувствительность к группам сходных задач (процентные пункты).',
        'tab:scc2000-source', ['Grouping and contrast', 'Groups', 'Tasks', '95\\% interval'] if en else
        ['Группировка и сравнение', 'Группы', 'Задачи', '95\\% интервал'], rows,
        'Whole groups are resampled while retaining equal task weights. These intervals do not introduce additional hypothesis tests.' if en else
        'Целиком перевыбираются группы с сохранением равных весов задач. Эти интервалы не образуют дополнительных тестов гипотез.'))
    segments = {'before': ('Before', 'До'), 'after': ('After', 'После'), 'spanning': ('Spanning', 'На границе')}
    rows = []
    for segment, values in summary['restart_diagnostics']['matched_quality_effects_descriptive'].items():
        for name in CONTRASTS:
            row = values[name]
            rows.append([segments[segment][0 if en else 1]+'; '+_short_label(name), str(row['task_count']), _fmt(row['mean_difference'], 100)])
    parts.append(_table('Timing diagnostic (percentage points).' if en else 'Диагностика этапов выполнения (процентные пункты).',
        'tab:scc2000-timing', ['Segment and contrast', 'Tasks', 'Difference'] if en else
        ['Этап и сравнение', 'Задачи', 'Разность'], rows,
        'Segments refer to the original 2,000-block amendment, not the later transport resumptions. They are descriptive and do not identify a causal time effect.' if en else
        'Этапы определены относительно исходной поправки о 2000 блоках, а не последующих возобновлений транспорта. Это описательные оценки; они не выделяют причинный эффект времени.'))
    return '\n'.join(parts)


def render(archive: Path, output: Path) -> dict[str, Any]:
    archive, output = archive.resolve(), output.resolve()
    if archive in output.parents or output == archive:
        raise ValueError("presentation output must be outside immutable archive")
    rows, summary = project_rows(archive)
    if output.exists():
        raise FileExistsError(f"refusing existing presentation output: {output}")
    output.mkdir(parents=True)
    with (output / "selected_6000_rows.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS); writer.writeheader()
        for row in rows:
            writer.writerow({k: ("unknown" if row.get(k) is None else str(row[k]).lower() if isinstance(row[k], bool) else row[k]) for k in CSV_FIELDS})
    for lang in ("en", "ru"):
        (output / f"appendix_{lang}.tex").write_text(appendix_table(rows, lang), encoding="utf-8")
        (output / f"summary_{lang}.tex").write_text(summary_tables(summary, lang), encoding="utf-8")
    counts = dict(sorted(Counter(r["display_code"] for r in rows).items()))
    report = {"schema": "scc2000-presentation-v1", "selected_rows": len(rows),
              "tasks": len({r["task_id"] for r in rows}), "display_code_counts": counts,
              "summary_schema": summary.get("schema"), "outside_prefix_is_em_dash": True}
    (output / "provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.archive, args.output), ensure_ascii=False))
