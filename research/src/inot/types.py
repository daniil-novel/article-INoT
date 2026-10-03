"""Common dataclasses shared by all subpackages.

Mirrors the formal objects from §3 of the article:
    Task              ~ (x, C0, Z, V) — agent engineering task (Definition 1)
    TokenUsage        ~ (p^L_i, r^L_i, p^S_i, r^S_i) — per-call token counts
    VerificationResult~ (v, M) — (binary verdict, maintainability score)
    RunResult         ~ Y(omega), T(omega), C_inf(omega), l(omega) — (eq. 2)

Everything here is plain data; no I/O, no LLM calls. Architectures and
experiments construct these objects and metrics consume them.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Tasks (Definition 1: (x, C0, Z, V))
# ---------------------------------------------------------------------------
@dataclass
class Task:
    """A single agent engineering task.

    Attributes
    ----------
    task_id : str
        Stable identifier (e.g. ``HumanEval/42``).
    prompt : str
        Natural-language specification ``x`` from set X.
    context : str
        Concrete context artifact ``C0`` (code, docs, logs) — the long shared
        context whose retransmission cost the article studies.
    test_code : str
        Python source defining the verifier ``V``: must define ``check(candidate)``
        which raises on failure. Used by ``inot.verification.runner``.
    entry_point : str
        Name of the function the candidate solution must define.
    suite : str
        Source benchmark, one of {"humaneval", "swebench_lite", "synthetic_tools"}.
    metadata : dict
        Free-form fields (e.g. parallelism degree p_||, original difficulty).
    """
    task_id: str
    prompt: str
    context: str
    test_code: str
    entry_point: str
    suite: str = "humaneval"
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Token / cost accounting (formula (14) of the article)
# ---------------------------------------------------------------------------
@dataclass
class TokenUsage:
    """One LLM call's input/output token counts and dollar cost.

    Maps directly onto (p^L_i, r^L_i, c^in_L, c^out_L) from §5.4. The ``model``
    string distinguishes large vs small models so that experiments can
    aggregate by model class for the H2 self-check analysis.
    """
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cost_rub: float = 0.0
    role: str = "unspecified"   # 'plan', 'work', 'crit', 'self_check', 'compress'
    architecture: str = ""
    iteration: int = 0
    latency_seconds: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# ---------------------------------------------------------------------------
# External verification (r_self of equation (6))
# ---------------------------------------------------------------------------
@dataclass
class VerificationResult:
    """Output of r_self: (v, M) — bool verdict plus maintainability score."""
    passed: bool
    tests_passed: bool = False
    static_passed: bool = False
    security_passed: bool = False
    maintainability: float = 0.0     # M ∈ [0,1] from formula (21)
    error_message: str = ""
    runtime_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Whole-task run
# ---------------------------------------------------------------------------
@dataclass
class RunResult:
    """Result of running one agent on one task once.

    Equation (2) variables:
        Y         <- final_solution
        T         <- total_tokens (sum of TokenUsage.total_tokens)
        C_inf     <- total_cost_usd
        l         <- wall_clock_seconds
        V(Y)      <- verification.passed
    """
    task_id: str
    architecture: str
    seed: int
    final_solution: str
    verification: VerificationResult
    usages: list[TokenUsage] = field(default_factory=list)
    wall_clock_seconds: float = 0.0
    iterations_used: int = 0
    rerun_count: int = 0
    routed_external: bool = False    # B3 RouteMode decision
    extra: dict[str, Any] = field(default_factory=dict)

    # ---- aggregate accessors ------------------------------------------------
    @property
    def total_tokens(self) -> int:
        return sum(u.total_tokens for u in self.usages)

    @property
    def total_input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.usages)

    @property
    def total_output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.usages)

    @property
    def total_cost_usd(self) -> float:
        return sum(u.cost_usd for u in self.usages)

    @property
    def total_cost_rub(self) -> float:
        return sum(u.cost_rub for u in self.usages)

    @property
    def passed(self) -> bool:
        return self.verification.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "architecture": self.architecture,
            "seed": self.seed,
            "passed": self.passed,
            "tests_passed": self.verification.tests_passed,
            "static_passed": self.verification.static_passed,
            "security_passed": self.verification.security_passed,
            "maintainability": self.verification.maintainability,
            "total_tokens": self.total_tokens,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "cost_usd": self.total_cost_usd,
            "cost_rub": self.total_cost_rub,
            "wall_clock_seconds": self.wall_clock_seconds,
            "iterations_used": self.iterations_used,
            "rerun_count": self.rerun_count,
            "routed_external": self.routed_external,
            "usages": [asdict(u) for u in self.usages],
            "extra": self.extra,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class WallClock:
    """Tiny context manager for wall-clock measurement.

    Used uniformly in architectures so latency l(omega) is comparable.
    """
    def __init__(self):
        self.elapsed: float = 0.0
        self._t0: Optional[float] = None

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        assert self._t0 is not None
        self.elapsed = time.perf_counter() - self._t0
        return False
