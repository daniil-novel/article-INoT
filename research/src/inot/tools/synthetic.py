"""Synthetic tool-use harness for hypothesis H3.

The article's H3 is about orchestration latency, not code correctness: if a
task decomposes into independent external-tool calls, Classical-MAS can run
those calls in parallel while a single internal Hybrid-INoT loop must serialize
them. This module measures that effect directly with deterministic local tools.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from ..types import Task


@dataclass
class ToolLatencyResult:
    task_id: str
    mode: str
    parallelism: int
    expected_latency_ms: float
    measured_latency_ms: float

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "mode": self.mode,
            "parallelism": self.parallelism,
            "expected_latency_ms": self.expected_latency_ms,
            "measured_latency_ms": self.measured_latency_ms,
        }


def measure_synthetic_tool_latency(tasks: Iterable[Task], *, mode: str) -> list[ToolLatencyResult]:
    """Measure serial Hybrid-style vs parallel Classical-MAS-style tools.

    ``mode='serial'`` executes all independent tools one after another.
    ``mode='parallel'`` executes them concurrently with a thread pool.
    """
    if mode not in {"serial", "parallel"}:
        raise ValueError("mode must be 'serial' or 'parallel'")
    results: list[ToolLatencyResult] = []
    for task in tasks:
        latencies = [float(x) for x in task.metadata.get("tool_latency_ms", [])]
        if not latencies:
            latencies = [100.0] * int(task.metadata.get("parallelism", 1))
        t0 = time.perf_counter()
        if mode == "serial":
            for ms in latencies:
                _tool_sleep(ms)
            expected = sum(latencies)
        else:
            with ThreadPoolExecutor(max_workers=len(latencies)) as pool:
                list(pool.map(_tool_sleep, latencies))
            expected = max(latencies)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        results.append(ToolLatencyResult(
            task_id=task.task_id,
            mode=mode,
            parallelism=len(latencies),
            expected_latency_ms=expected,
            measured_latency_ms=elapsed_ms,
        ))
    return results


def summarize_tool_latency(results: Iterable[ToolLatencyResult]) -> dict[str, float]:
    rows = list(results)
    if not rows:
        return {"n": 0, "mean_expected_latency_ms": 0.0, "mean_measured_latency_ms": 0.0}
    return {
        "n": len(rows),
        "mean_expected_latency_ms": mean(r.expected_latency_ms for r in rows),
        "mean_measured_latency_ms": mean(r.measured_latency_ms for r in rows),
    }


def _tool_sleep(ms: float) -> float:
    time.sleep(ms / 1000.0)
    return ms
