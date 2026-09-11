"""Reserve-policy and process-boundary tests; no model requests."""
import json
import subprocess
import sys
import time

import psutil
import pytest

from reproducibility.revision_20260911 import subscription_guard as guard


def bucket(used, secondary=None):
    return {"limitId": "codex", "primary": {"usedPercent": used},
            "secondary": None if secondary is None else {"usedPercent": secondary}}


def test_main_bucket_is_authoritative_and_spark_is_separate():
    payload = {"rateLimits": bucket(90), "rateLimitsByLimitId": {
        "codex": bucket(14), "codex_bengalfox": {"primary": {"usedPercent": 99}}}}
    assert guard.remaining_percent(payload) == 86


@pytest.mark.parametrize("primary,secondary,expected", [(14, None, 86), (20, 46, 54),
                                                        (45, 12, 55), (110, None, 0)])
def test_minimum_available_window(primary, secondary, expected):
    assert guard.remaining_percent({"rateLimits": bucket(primary, secondary)}) == expected


@pytest.mark.parametrize("used", [None, True, "14", -1, float("nan"), float("inf")])
def test_unknown_and_invalid_percentages_are_not_permission(used):
    with pytest.raises(ValueError):
        guard.remaining_percent({"rateLimits": bucket(used)})


def test_missing_main_bucket_cannot_fall_back_to_stale_legacy():
    with pytest.raises(ValueError):
        guard.remaining_percent({"rateLimits": bucket(0), "rateLimitsByLimitId": {
            "codex_bengalfox": bucket(0)}})
    with pytest.raises(ValueError):
        guard.remaining_percent({"rateLimits": {"limitId": "codex"}})


@pytest.mark.parametrize("used,allowed", [(44, True), (45, False), (46, False)])
def test_exact_reserve_boundary(monkeypatch, tmp_path, used, allowed):
    monkeypatch.setattr(guard, "read_limits", lambda *a: {"rateLimits": bucket(used)})
    result = guard.snapshot(tmp_path / "unused.exe", tmp_path)
    assert result["allow_model_work"] is allowed


def test_reader_failure_closes_gate(monkeypatch, tmp_path):
    def unavailable(*args):
        raise TimeoutError("Synthetic reader failure")
    monkeypatch.setattr(guard, "read_limits", unavailable)
    result = guard.snapshot(tmp_path / "unused.exe", tmp_path)
    assert result["allow_model_work"] is False
    assert result["remaining_percent"] is None


def test_latched_pause_never_reads_quota_or_auto_resumes(monkeypatch, tmp_path):
    class EndTest(Exception):
        pass
    calls = []
    guard.save(tmp_path / "PAUSED.json", {"reason": "user_subscription_reserve"})
    monkeypatch.setattr(guard, "read_limits", lambda *a: pytest.fail("Latched pause must not read quota"))
    monkeypatch.setattr(guard, "stop_study_generators", lambda root: calls.append(root) or {"stopped": [], "errors": []})
    def end_loop(*args):
        raise EndTest
    monkeypatch.setattr(guard.time, "sleep", end_loop)
    with pytest.raises(EndTest):
        guard.watch(tmp_path / "unused.exe", tmp_path, tmp_path, 60)
    assert calls == [tmp_path]
    assert (tmp_path / "PAUSED.json").is_file()
    assert json.loads((tmp_path / "status.json").read_text())["state"] == "paused"


def test_process_stop_is_confined_to_selected_checkout(tmp_path):
    """Terminate harmless sleeping fixtures, never an actual study process."""
    roots = [tmp_path / "selected", tmp_path / "unrelated"]
    parents, children = [], []
    try:
        for root in roots:
            package = root / "reproducibility/scale1000_luna"
            package.mkdir(parents=True)
            (root / "reproducibility/__init__.py").write_text("")
            (package / "__init__.py").write_text("")
            (package / "dispatch.py").write_text(
                "import pathlib,subprocess,sys,time\n"
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(90)'])\n"
                "pathlib.Path('child.pid').write_text(str(child.pid))\n"
                "time.sleep(90)\n", encoding="utf-8")
            parent = subprocess.Popen([sys.executable, "-m", "reproducibility.scale1000_luna.dispatch"],
                                      cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            parents.append(parent)
            deadline = time.monotonic() + 10
            while not (root / "child.pid").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            assert (root / "child.pid").exists()
            children.append(psutil.Process(int((root / "child.pid").read_text())))
        result = guard.stop_study_generators(roots[0])
        assert result["errors"] == []
        assert [p["pid"] for p in result["stopped"]] == [parents[0].pid]
        assert result["stopped"][0]["surviving_pids"] == []
        assert parents[0].wait(timeout=5) is not None
        assert not children[0].is_running()
        assert parents[1].poll() is None
        assert children[1].is_running()
    finally:
        for child in children:
            if child.is_running():
                child.terminate()
                child.wait(timeout=5)
        for parent in parents:
            if parent.poll() is None:
                parent.terminate()
            parent.wait(timeout=5)
