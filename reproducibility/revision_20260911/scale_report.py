"""Post-finish descriptive report for the frozen scale1000 ledger.

This is a separate report path.  It reads the 15,000-row ledger, the frozen
summary and the control gate, writes a new report directory exactly once, and
does not modify the frozen analysis or manuscript.  Until the generation
status is explicitly ``generation_finished`` it emits a readiness report
without outcome claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

ARMS = ("direct", "single_roles", "single_neutral", "multi_roles", "multi_neutral")
REPEATS = (101, 102, 103)
CONTRASTS = {
    "single_roles_minus_single_neutral": ("single_roles", "single_neutral"),
    "multi_roles_minus_multi_neutral": ("multi_roles", "multi_neutral"),
    "multi_neutral_minus_single_neutral": ("multi_neutral", "single_neutral"),
    "multi_roles_minus_single_roles": ("multi_roles", "single_roles"),
}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validate_records(records: list[dict[str, Any]], strict: bool = True):
    required = {"task_id", "arm", "replicate_id", "quality", "generation_complete"}
    index = {}
    tasks = []
    for row in records:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"ledger row missing fields: {sorted(missing)}")
        if row["arm"] not in ARMS or row["replicate_id"] not in REPEATS:
            raise ValueError("invalid arm or replicate_id")
        if row["quality"] is not None and type(row["quality"]) is not bool:
            raise ValueError("quality must be bool or null")
        if type(row["generation_complete"]) is not bool:
            raise ValueError("generation_complete must be bool")
        key = (row["task_id"], row["arm"], row["replicate_id"])
        if key in index:
            raise ValueError(f"duplicate ledger cell: {key}")
        index[key] = row
        if row["task_id"] not in tasks:
            tasks.append(row["task_id"])
    if strict:
        if len(records) != 15000 or len(tasks) != 1000:
            raise ValueError(f"expected 15,000 rows and 1,000 tasks, got {len(records)} and {len(tasks)}")
        expected = {(task, arm, rep) for task in tasks for arm in ARMS for rep in REPEATS}
        if set(index) != expected:
            raise ValueError("ledger is not the complete unique 1,000 x 5 x 3 matrix")
    return tasks, index


def _quality_value(row: dict[str, Any] | None):
    if row is None or row.get("generation_complete") is not True or row.get("quality") is None:
        return None
    return int(row["quality"])


def _bounds(tasks, index, left: str, right: str):
    lo_total = hi_total = 0.0; unknown_tasks = 0
    for task in tasks:
        def extent(arm):
            values = [_quality_value(index.get((task, arm, rep))) for rep in REPEATS]
            known = [v for v in values if v is not None]
            return sum(known) / 3, (sum(known) + 3 - len(known)) / 3, int(len(known) < 3)
        lo_l, hi_l, miss_l = extent(left); lo_r, hi_r, miss_r = extent(right)
        lo_total += lo_l - hi_r; hi_total += hi_l - lo_r; unknown_tasks += int(miss_l or miss_r)
    n = len(tasks)
    return {"task_count": n, "task_clusters_with_unknown_endpoint": unknown_tasks,
            "lower_difference": lo_total / n, "upper_difference": hi_total / n,
            "lower_difference_pp": 100 * lo_total / n, "upper_difference_pp": 100 * hi_total / n}


def _category(row: dict[str, Any], eligible: set[str]):
    if row["task_id"] not in eligible or row.get("outcome_type") == "control_ineligible":
        return "native_ineligible"
    if row.get("generation_complete") is not True or row.get("outcome_type") in {
        "generation_unavailable", "transport_failure", "quota_failure", "authentication_failure",
        "provenance_failure", "model_workflow_failure", "native_unavailable", "untouched",
    }:
        return "submitted_unavailable"
    if row.get("outcome_type") in {"model_format_failure", "format_failure"} or row.get("format_extracted") is False:
        return "format_failure"
    return "observed_native_or_other"


def _session_label(row: dict[str, Any]):
    for key in ("session", "session_label", "assignment_session", "resume_session", "attempt_type"):
        if row.get(key) is not None:
            value = str(row[key]).lower()
            if "resume" in value:
                return "resume"
            if "original" in value or "initial" in value:
                return "original"
    return "unknown"


def _tex_escape(value: Any) -> str:
    return str(value).replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")


def render_tex(report: dict[str, Any], language: str) -> str:
    """Render compact EN/RU fragments from a report dict; safe on synthetic reports."""
    ready = report.get("analysis_status") == "generation_finished"
    title = "Scale1000 missingness and execution report" if language == "en" else "Пропуски и выполнение в серии Scale1000"
    if not ready:
        prose = ("The generation ledger is not marked generation_finished; this fragment reports readiness only and makes no outcome claim."
                 if language == "en" else
                 "Ledger не отмечен как generation_finished; этот фрагмент сообщает только готовность и не содержит вывода об исходах.")
        return f"\\subsection*{{{title}}}\n{prose}\n"
    prose = ("This descriptive report uses the retained 15,000-assignment ledger and the frozen 985-task control gate. Bounds are assignment-denominator identification ranges with three repeats averaged within task; they are not confidence intervals or non-inferiority evidence."
             if language == "en" else
             "Этот описательный отчёт использует сохранённый реестр из 15\,000 назначений и фиксированное контрольное множество из 985 задач. Границы задают идентификационный диапазон для знаменателя назначений; три повтора усреднены внутри задачи. Это не доверительные интервалы и не проверка не меньшей эффективности.")
    ru_labels = {"single_roles_minus_single_neutral": "Роли--нейтральный",
                 "multi_roles_minus_multi_neutral": "Мульти-роли--мульти-нейтр.",
                 "multi_neutral_minus_single_neutral": "Мульти-нейтр.--нейтр.",
                 "multi_roles_minus_single_roles": "Мульти-роли--роли"}
    rows = []
    for name, value in report["missingness_bounds"]["all_assigned"].items():
        if name not in CONTRASTS:
            continue
        gate = report["missingness_bounds"]["control_eligible"][name]
        label = name if language == "en" else ru_labels[name]
        rows.append(f"{_tex_escape(label)} & [{gate['lower_difference_pp']:+.2f},{gate['upper_difference_pp']:+.2f}] & [{value['lower_difference_pp']:+.2f},{value['upper_difference_pp']:+.2f}] \\\\")
    caption = ("Missingness identification bounds (percentage points)." if language == "en"
               else "Идентификационные границы пропусков (процентные пункты).")
    header = ("Contrast & 985 gate-eligible tasks & All 1,000 assigned tasks" if language == "en"
              else "Контраст & 985 задач контрольной группы & Все 1\\,000 задач")
    return (f"\\subsection*{{{title}}}\n{prose}\n"
            "\\begin{table}[!htbp]\\centering\\small\n"
            f"\\caption{{{caption}}}\\label{{tab:scale1000-missingness-bounds}}\n"
            "\\begin{tabular*}{\\textwidth}{@{\\extracolsep{\\fill}}lrr}\\toprule\n"
            f"{header} \\\\ \\midrule\n" + "\n".join(rows) +
            "\\bottomrule\\end{tabular*}\\end{table}\n")


def build_report(records_path: Path, summary_path: Path, gate_path: Path, out: Path,
                 status_path: Path | None = None, selection_path: Path | None = None) -> dict[str, Any]:
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing report directory: {out}")
    records = _load_records(records_path); summary = _read(summary_path); gate = _read(gate_path)
    status = _read(status_path) if status_path else {"state": summary.get("generation_state", "unknown")}
    generation_state = status.get("state")
    out.mkdir(parents=True, exist_ok=False)
    payload: dict[str, Any] = {
        "schema": "scale1000-descriptive-report-v1", "analysis_status": generation_state,
        "source_sha256": {"records": _sha(records_path), "summary": _sha(summary_path), "gate": _sha(gate_path)},
        "source_rows": len(records), "summary_schema": summary.get("schema"),
        "gate_eligible_count": len(gate.get("evaluable_task_ids", [])),
        "claims_policy": "No outcome claims unless generation state is generation_finished.",
    }
    if generation_state != "generation_finished":
        payload["readiness"] = "not_ready_for_outcome_claims"
        payload["limitations"] = ["generation is not marked generation_finished", "no bounds or outcome summaries emitted"]
    else:
        tasks, index = _validate_records(records, strict=True)
        assigned = set(gate.get("assigned_task_ids", tasks)); eligible = set(gate.get("evaluable_task_ids", []))
        if len(assigned) != 1000 or assigned != set(tasks) or len(eligible) != 985 or not eligible <= assigned:
            raise ValueError("gate must match 1,000 assignment tasks and contain 985 eligible IDs")
        payload["missingness_bounds"] = {
            "control_eligible": {name: _bounds(sorted(eligible), index, *pair) for name, pair in CONTRASTS.items()},
            "all_assigned": {name: _bounds(tasks, index, *pair) for name, pair in CONTRASTS.items()},
        }
        categories = Counter(_category(row, eligible) for row in records)
        sessions = Counter(_session_label(row) for row in records)
        payload["assignment_breakdown"] = {"submitted_unavailable": categories["submitted_unavailable"],
                                            "format_failure": categories["format_failure"],
                                            "native_ineligible": categories["native_ineligible"],
                                            "observed_native_or_other": categories["observed_native_or_other"]}
        payload["session_breakdown"] = dict(sessions)
        payload["session_mapping_note"] = "Original/resume is reported only when an explicit session field exists; timestamps alone are not treated as a reliable session mapping."
        payload["selection"] = _read(selection_path) if selection_path else None
    payload["summary_excerpt"] = {key: summary.get(key) for key in ("tasks", "planned_candidates", "missingness", "inference") if key in summary}
    (out / "scale_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "scale_report_en.tex").write_text(render_tex(payload, "en"), encoding="utf-8")
    (out / "scale_report_ru.tex").write_text(render_tex(payload, "ru"), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--records", type=Path, required=True); parser.add_argument("--summary", type=Path, required=True); parser.add_argument("--gate", type=Path, required=True); parser.add_argument("--out", type=Path, required=True); parser.add_argument("--status", type=Path); parser.add_argument("--selection", type=Path)
    args = parser.parse_args(); result = build_report(args.records, args.summary, args.gate, args.out, args.status, args.selection)
    print(json.dumps({"analysis_status": result["analysis_status"], "out": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__": main()
