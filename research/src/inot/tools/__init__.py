"""Deterministic external-tool harnesses used by H3 experiments."""

from .synthetic import ToolLatencyResult, measure_synthetic_tool_latency

__all__ = ["ToolLatencyResult", "measure_synthetic_tool_latency"]
