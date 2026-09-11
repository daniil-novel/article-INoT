"""Present every repeated assignment from a completed, published study archive.

This renderer preserves the recorded endpoints. It does not recompute inference
or replace the archive's full raw-response/native-report/statistical replay.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

from reproducibility.evidence_manifest import verify
from reproducibility.revision_20260911.plot_quality_effects import chart_rows

REPEATS = (101, 102, 103)
CONDITIONS = {
    "factorial": (("direct", "D"), ("single_neutral", "SN"),
                  ("single_roles", "SR"), ("multi_neutral", "MN"), ("multi_roles", "MR")),
    "scc": (("single_neutral", "SN"), ("single_roles", "SR"),
            ("scc_author_2024_codex_transport", "SCC")),
}
FIELDS = ("study", "assignment_id", "task_id", "condition", "replicate_id",
          "control_eligible", "generation_complete", "candidate_available",
          "availability_recorded", "format_extracted_recorded", "format_status",
          "native_status", "quality", "outcome_type", "display_code")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_code(row: dict) -> str:
    """Unknown remains unknown, even when another diagnostic flag is false."""
    q, candidate, eligible = row["quality"], row["candidate_available"], row["control_eligible"]
    native, extracted = row["native_status"], row["format_extracted_recorded"]
    if q is not None and type(q) is not bool:
        raise ValueError("Quality must be an observed boolean or null")
    if not candidate:
        if q is not None or native is not None:
            raise ValueError("Unavailable candidate has an observed endpoint")
        return "G"
    if not eligible:
        if q is not None:
            raise ValueError("Control-ineligible task has a quality endpoint")
        return "U"
    if q is None:
        if native in ("pass", "fail", "timeout"):
            raise ValueError("Eligible candidate has native evidence but no recorded endpoint")
        return "N"
    if q:
        if native != "pass" or extracted is not True:
            raise ValueError("Recorded success contradicts native/format evidence")
        return "P"
    if extracted is False:
        return "X"
    if native == "fail":
        return "F"
    if native == "timeout":
        return "T"
    raise ValueError("Recorded failure lacks native or format support")


def project_rows(records: list[dict], task_ids: list[str], eligible: set[str], study: str) -> list[dict]:
    """Validate and preserve a complete task x condition x repeat matrix."""
    conditions = [name for name, _ in CONDITIONS[study]]
    if len(set(task_ids)) != len(task_ids) or not eligible <= set(task_ids):
        raise ValueError("Duplicate tasks or control IDs outside the assignment list")
    if any(not re.fullmatch(r"BigCodeBench/\d+", task) for task in task_ids):
        raise ValueError("Unexpected task identifier")
    expected = {(t, c, r) for t in task_ids for c in conditions for r in REPEATS}
    actual, identifiers, projected = set(), set(), []
    for source in records:
        condition = source["arm" if study == "factorial" else "method"]
        key = (source["task_id"], condition, source["replicate_id"])
        if key not in expected or key in actual or source["id"] in identifiers:
            raise ValueError("Repeated, relabelled or unexpected assignment")
        actual.add(key); identifiers.add(source["id"])
        generation = source["generation_complete"]
        candidate = source.get("observed_candidate") if study == "scc" else generation
        extracted = source.get("format_extracted")
        if type(generation) is not bool or type(candidate) is not bool:
            raise ValueError("Invalid generation or candidate flag")
        if candidate != generation or (extracted is not None and type(extracted) is not bool):
            raise ValueError("Candidate/format flag contradicts the completed-study schema")
        if candidate and extracted is None:
            raise ValueError("Completed candidate lacks its format assessment")
        row = {"study": study, "assignment_id": source["id"], "task_id": key[0],
               "condition": condition, "replicate_id": key[2], "control_eligible": key[0] in eligible,
               "generation_complete": generation, "candidate_available": candidate,
               "availability_recorded": source.get("availability"),
               "format_extracted_recorded": extracted,
               "format_status": "not_assessed" if not candidate else ("valid" if extracted else "invalid"),
               "native_status": source.get("native_status"), "quality": source["quality"],
               "outcome_type": source["outcome_type"]}
        row["display_code"] = display_code(row)
        projected.append(row)
    if actual != expected:
        raise ValueError("Assignment matrix is incomplete; no missing row may be dropped")
    return sorted(projected, key=lambda x: (int(x["task_id"].split("/")[1]),
                                           conditions.index(x["condition"]), x["replicate_id"]))


def load_archive(archive: Path):
    status = read(archive / "generation/status.json")
    if status.get("state") != "generation_finished" or (archive / "generation/DISPATCH.lock").exists():
        raise ValueError("Only a completed published archive can be rendered")
    inventory = verify(archive)
    study, _ = chart_rows(read(archive / "analysis/summary.json"))
    if study == "factorial":
        records_path = archive / "analysis/candidate_records.jsonl"
        selection_path = archive / "inputs/scale1000-v1/selection.json"
        gate_path = archive / "controls/controls-v3/heldout200_control_gate.json"
    else:
        records_path = archive / "candidate_records.jsonl"
        selection_path = archive / "inputs/selection.json"
        gate_path = archive / "controls/heldout200_control_gate.json"
    selection, gate = read(selection_path), read(gate_path)
    ids = selection["assigned_task_ids"]
    eligible = set(gate["evaluable_task_ids"])
    if (len(ids) != 1000 or gate.get("assigned_task_ids") != ids
            or gate.get("controls_complete") is not True or len(eligible) != 985
            or len(gate["evaluable_task_ids"]) != 985):
        raise ValueError("Completed study does not match the fixed task/control allocation")
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = project_rows(records, ids, eligible, study)
    inputs = {p.relative_to(archive).as_posix(): sha(p) for p in
              (records_path, selection_path, gate_path, archive / "analysis/summary.json",
               archive / "generation/status.json", archive / "EVIDENCE_MANIFEST.json")}
    return study, rows, inventory, inputs


def tex_tables(rows: list[dict], study: str, language: str, rows_per_table: int = 40) -> str:
    """All assignments in separate repeat columns, without averaging or slashes."""
    if language not in ("en", "ru") or rows_per_table < 1:
        raise ValueError("Invalid display options")
    ru = language == "ru"
    conditions = CONDITIONS[study]
    ids = sorted({r["task_id"] for r in rows}, key=lambda t: int(t.split("/")[1]))
    index = {(r["task_id"], r["condition"], r["replicate_id"]): r for r in rows}
    parts = (len(ids) + rows_per_table - 1) // rows_per_table
    title = (("Факторный эксперимент" if study == "factorial" else "Сравнение SCC") if ru else
             ("Factorial experiment" if study == "factorial" else "SCC comparison"))
    intro = (
        "Каждая строка соответствует одной задаче BigCodeBench; ID обозначает числовой суффикс её идентификатора. "
        "Для каждого условия приведены все три повтора с исходными метками 101, 102 и 103; это не seed провайдера. "
        "В столбце контроля указана пригодность задачи по эталонному и неправильному решениям. "
        "P означает успех; F, T и X означают наблюдаемый неуспех. G, N и U означают недоступное качество, а не неуспех. "
        "Полный CSV сохраняет отдельные поля доступности кандидата, извлечения формата, штатного статуса и качества; "
        "PDF показывает конечную классификацию. У непригодных по контролю задач штатный статус может существовать, "
        "но качество остаётся неизвестным.\n\n" if ru else
        "Each row represents one BigCodeBench task; ID is the numeric suffix of its identifier. "
        "Every condition retains the three original replicate labels 101, 102 and 103; these are not provider seeds. "
        "The control column identifies eligibility under the reference and incorrect-solution checks. "
        "P denotes success; F, T and X denote observed failure. G, N and U denote unavailable quality, not failure. "
        "The full CSV separately retains candidate availability, format extraction, native status and quality; "
        "the PDF shows the final classification. A control-ineligible task may have a native status while its quality "
        "remains unknown.\n\n")
    legend = (
        "P: успех; F: провал тестов; T: тайм-аут; X: форматный отказ; G: нет полного кандидата; "
        "N: нативный исход недоступен; U: качество недоступно по контролю." if ru else
        "P: success; F: test failure; T: timeout; X: format failure; G: no complete candidate; "
        "N: native endpoint unavailable; U: quality unavailable under the control gate.")
    if study == "factorial":
        names = ("D: прямое решение; SN: один вызов без обозначений ролей; SR: один вызов с ролями; "
                 "MN: три вызова без обозначений ролей; MR: три вызова с ролями." if ru else
                 "D: direct solution; SN: one call without role labels; SR: one call with roles; "
                 "MN: three calls without role labels; MR: three calls with roles.")
    else:
        names = ("SN: один вызов без обозначений ролей; SR: один вызов с ролями; SCC: адаптация авторской "
                 "процедуры с собственными сгенерированными тестами и исправлениями. Качество определяется "
                 "отдельной штатной проверкой бенчмарка." if ru else
                 "SN: one call without role labels; SR: one call with roles; SCC: the adapted author procedure "
                 "with generated tests and revisions. Quality is determined separately by the native benchmark evaluator.")
    chunks = [names + "\n\n" + intro]
    for part, start in enumerate(range(0, len(ids), rows_per_table), 1):
        part_text = f"часть {part} из {parts}" if ru else f"part {part} of {parts}"
        chunks.extend([r"\begin{table}[p]\centering\footnotesize", r"\setlength{\tabcolsep}{3pt}",
                       f"\\caption{{{title}: {part_text}. {legend}}}",
                       r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}rc" + "c" * (3 * len(conditions)) + r"}\toprule"])
        header = "ID & " + ("Контроль" if ru else "Control")
        header += " & " + " & ".join(f"\\multicolumn{{3}}{{c}}{{{label}}}" for _, label in conditions)
        chunks.append(header + r"\\")
        chunks.append("".join(f"\\cmidrule(lr){{{3+3*i}-{5+3*i}}}" for i in range(len(conditions))))
        chunks.append(" & & " + " & ".join(str(rep) for _ in conditions for rep in REPEATS) + r"\\\midrule")
        for task in ids[start:start + rows_per_table]:
            eligible = index[(task, conditions[0][0], REPEATS[0])]["control_eligible"]
            gate = ("да" if eligible else "нет") if ru else ("yes" if eligible else "no")
            values = [str(int(task.split("/")[1])), gate]
            values.extend(index[(task, condition, rep)]["display_code"] for condition, _ in conditions for rep in REPEATS)
            chunks.append(" & ".join(values) + r"\\")
        chunks.extend([r"\bottomrule\end{tabular*}\end{table}", r"\clearpage", ""])
    return "\n".join(chunks)


def render(archive: Path, output: Path) -> dict:
    archive, output = archive.resolve(), output.resolve()
    if output == archive or archive in output.parents:
        raise ValueError("Presentation files must remain outside the immutable evidence archive")
    study, rows, inventory, inputs = load_archive(archive)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "assignment_outcomes.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "unknown" if v is None else str(v).lower() if type(v) is bool else v
                             for k, v in row.items()})
    for language in ("en", "ru"):
        (output / f"assignment_outcomes_{language}.tex").write_text(tex_tables(rows, study, language), encoding="utf-8")
    notes = """# Assignment-outcome presentation

One CSV row is one task-condition-repeat assignment. Every assigned row is kept.
`quality` is the original true/false/unknown endpoint, without imputation.
`native_status` is separately retained even for control-ineligible tasks.
`availability_recorded` is unknown if the source ledger has no such field.
`format_extracted_recorded` preserves the source flag. A false flag when no
candidate exists does not establish a format failure; `format_status` is then
`not_assessed`. Generation failures are not inferred to be test failures.

P is success. F (native failure), T (native timeout) and X (recorded format
failure) are observed failures. G (no complete candidate), N (unavailable native
endpoint) and U (control-ineligible quality) remain unknown. The PDF projection
uses G first for unavailable candidates and U for other control-ineligible rows;
the full CSV retains the underlying flags. Neither file contains full programs,
raw responses, resource counters or all native diagnostic details.

The EN/RU TeX tables require booktabs and preserve every repeat in its own
column. Their task IDs are numeric suffixes of the CSV BigCodeBench IDs.
No inferential test is recalculated here. Run the completed archive's full
raw-response/native-report/statistical replay before using these files.
"""
    (output / "README.md").write_text(notes, encoding="utf-8")
    report = {"study": study, "assignments": len(rows), "tasks": len({r["task_id"] for r in rows}),
              "replicates": list(REPEATS), "display_code_counts": dict(sorted(Counter(r["display_code"] for r in rows).items())),
              "input_sha256": inputs, "input_byte_inventory": inventory, "renderer_sha256": sha(Path(__file__)),
              "verification_scope": "Exact archive bytes, completed-study summary contract, complete assignment matrix and endpoint consistency; not statistical replay.",
              "output_sha256": {p.name: sha(p) for p in sorted(output.iterdir())}}
    (output / "provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.archive, args.output), ensure_ascii=False))
