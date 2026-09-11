"""Render the post-review sensitivity diagnostics as two EN/RU TeX sections.

The renderer is deliberately separate from the statistical computation.  It
reads the checked JSON/CSV outputs in this directory and writes only the two
new section files under ``sections/``.  It does not alter primary tables or
the manuscript entry points.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / "batch_missingness_results.json"
PAIRED = HERE / "batch_paired_contrasts.csv"
SECTIONS = ROOT / "sections"


def tex(value: object) -> str:
    s = str(value)
    return (s.replace("\\", r"\textbackslash{}").replace("&", r"\&")
            .replace("%", r"\%").replace("_", r"\_").replace("#", r"\#"))


def pp(value: float) -> str:
    return f"{value:+.2f}"


def ci_pair(raw: str) -> tuple[float, float]:
    lo, hi = json.loads(raw)
    return float(lo), float(hi)


def table_bounds(result: dict, language: str) -> str:
    labels_en = {"SR-SN": "SR$-$SN", "MR-MN": "MR$-$MN", "MN-SN": "MN$-$SN", "MR-SR": "MR$-$SR"}
    labels_ru = {"SR-SN": "SR$-$SN", "MR-MN": "MR$-$MN", "MN-SN": "MN$-$SN", "MR-SR": "MR$-$SR"}
    labels = labels_en if language == "en" else labels_ru
    cap = ("Missingness identification bounds (percentage points)."
           if language == "en" else
           "Границы парных разностей при неизвестных исходах (процентные пункты).")
    note = ("Unknown endpoints range independently over 0 and 1; bounds are identification ranges, not confidence intervals."
            if language == "en" else
            "Каждый неизвестный исход может принимать значение 0 или 1. Показаны границы возможных значений, а не доверительные интервалы.")
    rows = []
    for name in ("SR-SN", "MR-MN", "MN-SN", "MR-SR"):
        c = result["missingness_identification_bounds"][name]
        e, a = c["control_eligible_193"], c["all_assigned_200"]
        rows.append(f"{labels[name]} & $[{pp(e['lower_difference_pp'])},{pp(e['upper_difference_pp'])}]$ & $[{pp(a['lower_difference_pp'])},{pp(a['upper_difference_pp'])}]$ \\\\")
    head = ("Contrast & 193 control-eligible tasks & All 200 assigned tasks" if language == "en"
            else "Контраст & 193 оцениваемые задачи & Все 200 задач")
    label = "tab:heldout-sensitivity-bounds"
    return (f"\\begin{{table}}[!htbp]\\centering\\small\n"
            f"\\caption{{{cap}}}\\label{{{label}}}\n"
            f"\\begin{{tabular*}}{{\\textwidth}}{{@{{\\extracolsep{{\\fill}}}}lrr}}\\toprule\n"
            f"{head} \\\\\\ \\midrule\n" + "\n".join(rows) +
            f"\\bottomrule\\end{{tabular*}}\\par\\smallskip\\footnotesize {note}\\end{{table}}\n")


def table_batch(rows: list[dict], language: str) -> str:
    cap = ("Within-batch quality sensitivity (percentage points)."
           if language == "en" else
           "Чувствительность качества внутри партий (процентные пункты).")
    head = ("Batch & Contrast & $N$ & Difference & Descriptive task-bootstrap 95\\% interval"
            if language == "en" else
            "Партия & Контраст & $N$ & Разность & 95\\%-интервал бутстрэпа")
    label = "tab:heldout-sensitivity-batch"
    ordered = [("original", "SR-SN"), ("original", "MR-MN"), ("original", "MN-SN"), ("original", "MR-SR"),
               ("continuation", "SR-SN"), ("continuation", "MR-MN"), ("continuation", "MN-SN"), ("continuation", "MR-SR")]
    by_key = {(r["batch"], r["contrast"]): r for r in rows}
    out = []
    for batch, contrast in ordered:
        r = by_key[(batch, contrast)]
        lo, hi = ci_pair(r["quality_difference_descriptive_ci95_pp"])
        b = "Original" if batch == "original" else "Continuation"
        if language == "ru":
            b = "Исходная" if batch == "original" else "Продолжение"
        out.append(f"{b} & {contrast.replace('-', '$-$')} & {r['complete_task_pairs']} & {pp(float(r['quality_difference_pp']))} & $[{pp(lo)},{pp(hi)}]$ \\\\")
    note = ("Intervals quantify conditional task-sampling uncertainty for the observed complete-pair subset; they exclude provider/time variation and missingness mechanisms. Native timeouts are observed failures under the frozen rules. The four primary McNemar/Holm tests are unchanged."
            if language == "en" else
            "Интервалы описывают выборочную неопределённость по задачам среди наблюдаемых полных пар; они не учитывают изменения сервиса во времени и механизм пропусков. Превышение времени нативной проверки считается наблюдаемым неуспехом согласно исходному протоколу.")
    return (f"\\begin{{table}}[!htbp]\\centering\\scriptsize\n"
            f"\\caption{{{cap}}}\\label{{{label}}}\n"
            f"\\begin{{tabular*}}{{\\textwidth}}{{@{{\\extracolsep{{\\fill}}}}llrrr}}\\toprule\n"
            f"{head} \\\\\\ \\midrule\n" + "\n".join(out) +
            f"\\bottomrule\\end{{tabular*}}\\par\\smallskip\\footnotesize {note}\\end{{table}}\n")


def prose(language: str) -> str:
    if language == "en":
        return ("A post hoc diagnostic uses retained records only. "
                "Batch membership was recovered from cell IDs in the continuation manifest: 460 assigned cells are original and 540 are continuation; 996 candidate records are retained and four submitted-incomplete cells are unavailable. "
                "First-batch-only estimates are therefore not treated as an unbiased counterfactual for a complete original execution. "
                "The bounds table reports finite-sample identification limits for unknown binary endpoints, while the batch table reports descriptive within-batch contrasts on complete task pairs. "
                "Task bootstrap intervals quantify conditional task-sampling uncertainty in those observed subsets; they do not quantify provider or time variation, batch assignment, or missingness mechanisms. "
                "The cross-batch complete-pair counts are 2, 1, 0, and 1 for SR--SN, MR--MN, MN--SN, and MR--SR, respectively; singleton bounds remain sampling-uncertain despite having zero identification width. "
                "These counts do not identify provider drift or a causal batch effect. This supplement does not alter the four predeclared McNemar tests or their Holm correction.")
    return ("Дополнительный анализ чувствительности выполнен после получения результатов и использует сохранённые записи. "
            "Принадлежность к партии восстановлена по идентификаторам назначений в манифесте продолжения: 460 назначений относятся к исходной партии, 540 --- к продолжению; сохранены 996 программ, четыре отправленных назначения не завершены. "
            "Таблица~\\ref{tab:heldout-sensitivity-bounds} показывает границы парных разностей при всех возможных значениях неизвестных бинарных исходов. "
            "Совпадение нижней и верхней границ означает отсутствие неопределённости из-за пропусков в данном наборе, но не устраняет выборочную неопределённость. "
            "В табл.~\\ref{tab:heldout-sensitivity-batch} приведены разности внутри партий на полных парах задач. "
            "Бутстрэп по задачам описывает выборочную неопределённость в этих наблюдаемых поднаборах; он не учитывает изменения сервиса во времени, распределение назначений между партиями и механизм пропусков. "
            "Число полных пар, чьи условия выполнены в разных партиях, равно 2, 1, 0 и 1 для SR--SN, MR--MN, MN--SN и MR--SR соответственно. "
            "Различия между партиями зависят также от состава задач и не устанавливают причинное влияние времени или провайдера. "
            "Поэтому результат исходной партии нельзя считать несмещённой оценкой того, что получилось бы при выполнении всех назначений в ней. "
            "Четыре заранее заданных теста Мак-Немара и поправка Холма сохранены.")


def main() -> None:
    result = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(PAIRED.open(encoding="utf-8", newline="")))
    for language in ("en", "ru"):
        body = "\\subsection*{" + ("Sensitivity to missing outcomes and execution batches" if language == "en" else "Чувствительность к пропущенным исходам и партиям выполнения") + "}\n"
        body += prose(language) + "\n\n"
        body += table_bounds(result, language) + "\n"
        body += table_batch(rows, language) + "\n"
        # Normalize row-break delimiters so generated Springer tables contain
        # exactly ``\\`` before rules (rather than an accidental third slash).
        body = body.replace(r"\\\ \midrule", r"\\ \midrule")
        body = body.replace(r"\\\bottomrule", "\\\\\n" + r"\bottomrule")
        (SECTIONS / f"heldout_sensitivity_{language}.tex").write_text(body.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
