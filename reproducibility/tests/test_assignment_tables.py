"""Presentation checks on explicit software fixtures, never study outcomes."""
import csv
import json
import re

import pytest

from reproducibility.revision_20260911 import render_assignment_tables as table


def fixture(study="factorial", n=1):
    tasks = [f"BigCodeBench/{900001+i}" for i in range(n)]
    rows = []
    for task in tasks:
        for condition, _ in table.CONDITIONS[study]:
            for repeat in table.REPEATS:
                row = {"id": f"fixture-{task}-{condition}-{repeat}", "task_id": task,
                       "arm" if study == "factorial" else "method": condition,
                       "replicate_id": repeat, "generation_complete": True,
                       "format_extracted": True, "native_status": "pass", "quality": True,
                       "outcome_type": "native_outcome"}
                if study == "scc":
                    row.update(observed_candidate=True, availability="completed")
                rows.append(row)
    return tasks, rows


@pytest.mark.parametrize("study", ["factorial", "scc"])
@pytest.mark.parametrize("case,expected", [("missing_candidate", "G"), ("missing_native", "N"),
                                           ("format", "X"), ("timeout", "T"), ("fail", "F"),
                                           ("ineligible", "U"), ("success", "P")])
def test_observed_failure_and_unavailable_states_stay_distinct(study, case, expected):
    tasks, source = fixture(study)
    row = source[0]
    eligible = set(tasks)
    if case == "missing_candidate":
        row.update(generation_complete=False, quality=None, native_status=None, format_extracted=False,
                   observed_candidate=False, availability="submitted_incomplete", outcome_type="generation_unavailable")
    elif case == "missing_native":
        row.update(quality=None, native_status=None, outcome_type="native_unavailable")
    elif case == "format":
        row.update(quality=False, format_extracted=False, outcome_type="model_format_failure")
    elif case in ("timeout", "fail"):
        row.update(quality=False, native_status=case)
    elif case == "ineligible":
        eligible.clear()
        for item in source:
            item.update(quality=None, outcome_type="control_ineligible")
    projected = table.project_rows(source, tasks, eligible, study)
    first = next(r for r in projected if r["assignment_id"] == row["id"])
    assert first["display_code"] == expected
    assert first["quality"] is row["quality"]
    assert first["native_status"] == row["native_status"]
    if case == "missing_candidate":
        assert first["format_status"] == "not_assessed"
    if case == "ineligible":
        assert first["native_status"] == "pass" and first["quality"] is None


@pytest.mark.parametrize("change", ["missing_row", "duplicate", "wrong_task", "wrong_repeat",
                                     "numeric_quality", "unsupported_success", "hidden_native_failure"])
def test_corrupt_or_incomplete_ledgers_are_rejected(change):
    tasks, source = fixture()
    if change == "missing_row":
        source.pop()
    elif change == "duplicate":
        source[-1] = source[0].copy()
    elif change == "wrong_task":
        source[0]["task_id"] = "BigCodeBench/42"
    elif change == "wrong_repeat":
        source[0]["replicate_id"] = 104
    elif change == "numeric_quality":
        source[0]["quality"] = 1
    elif change == "unsupported_success":
        source[0]["native_status"] = "fail"
    else:
        source[0].update(quality=None, native_status="fail")
    with pytest.raises(ValueError):
        table.project_rows(source, tasks, set(tasks), "factorial")


@pytest.mark.parametrize("study,expected", [("factorial", 15000), ("scc", 9000)])
def test_full_size_presentation_keeps_every_task_and_repeat(study, expected):
    tasks, source = fixture(study, 1000)
    rows = table.project_rows(source, tasks, set(tasks), study)
    assert len(rows) == expected
    for language in ("en", "ru"):
        tex = table.tex_tables(rows, study, language)
        body = [line for line in tex.splitlines() if re.match(r"^9\d+ & ", line)]
        assert len(body) == 1000
        shown = [line.removesuffix(r"\\").split(" & ")[2:] for line in body]
        assert sum(map(len, shown)) == expected
        assert all(value == "P" for codes in shown for value in codes)
        assert all(str(rep) in tex for rep in table.REPEATS)
        assert "/" not in "".join(body)


def test_running_archive_is_rejected_before_any_presentation(tmp_path):
    generation = tmp_path / "generation"
    generation.mkdir()
    (generation / "status.json").write_text(json.dumps({"state": "running"}))
    with pytest.raises(ValueError, match="completed"):
        table.load_archive(tmp_path)


def test_csv_null_is_explicit_and_native_status_is_retained(tmp_path, monkeypatch):
    tasks, source = fixture()
    for row in source:
        row.update(quality=None, outcome_type="control_unavailable")
    projected = table.project_rows(source, tasks, set(), "factorial")
    monkeypatch.setattr(table, "load_archive", lambda archive: ("factorial", projected, {}, {}))
    destination = tmp_path / "presentation"
    table.render(tmp_path / "fixture-archive", destination)
    with (destination / "assignment_outcomes.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 15
    assert all(row["quality"] == "unknown" and row["native_status"] == "pass" for row in rows)
    assert all(row["control_eligible"] == "false" for row in rows)
    assert all(row["display_code"] == "U" for row in rows)


def test_cannot_add_presentation_files_inside_evidence_archive(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        table.render(tmp_path, tmp_path / "presentation")
