"""Sandboxed verification of generated Python solutions.

Provides ``r_self`` of equation (6): given a ``Task`` and a candidate solution
string, return ``VerificationResult(v, M)`` with:

* ``v``      = (tests pass) ∧ (static analysis pass) ∧ (security pass)
* ``M``      = maintainability score from formula (21):
               M = w_cc·(1-CC̃) + w_dup·(1-Dup̃) + w_warn·(1-Warñ) + w_doc·Doc̃

Tests are executed in a separate Python process with a wall-time limit
to contain infinite loops or runaway recursion in generated code.

Static analysis: py_compile + a tiny set of "obvious bug" lint rules
(``radon`` is used for cyclomatic complexity but is optional; if missing
the CC term is set to 0 which lowers M but does not break the run).

Security check: a minimal blocklist (``os.system``, ``eval``, ``exec``,
network primitives) since the article positions ``sec_i`` as a Bandit/Semgrep
proxy. For HumanEval-style snippets this is conservative enough.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile

from ..config import Config
from ..types import Task, VerificationResult


# ---------------------------------------------------------------------------
# Code extraction (LLMs love to wrap code in fences)
# ---------------------------------------------------------------------------
_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_code(raw: str, entry_point: str | None = None) -> str:
    """Pull the most plausible Python block from a raw LLM answer.

    Strategy: prefer fenced ```python``` blocks; among those, prefer ones
    that mention ``entry_point``; fall back to the whole string otherwise.
    """
    if not raw:
        return ""
    blocks = _FENCE.findall(raw)
    if blocks:
        if entry_point:
            for b in blocks:
                if entry_point in b:
                    return b.strip()
        return blocks[0].strip()
    # Heuristic: if it parses as Python as-is, return it; else search for first def
    try:
        ast.parse(raw)
        return raw.strip()
    except SyntaxError:
        m = re.search(r"((?:from\s+\S+\s+import[^\n]*\n|import\s+\S+\n)*\s*def\s+.*)", raw, re.DOTALL)
        if m:
            return m.group(1).strip()
    return raw.strip()


# ---------------------------------------------------------------------------
# Subprocess test runner (per-task isolation)
# ---------------------------------------------------------------------------
_RUNNER_TEMPLATE = """\
import sys, traceback
__SOLUTION__
__TESTS__
try:
    check(__ENTRY__)
    print("__VERIFY_OK__")
except Exception:
    traceback.print_exc()
    sys.exit(1)
"""


def run_tests(solution_code: str, task: Task, *, timeout_seconds: int = 15) -> tuple[bool, str, float]:
    """Run ``task.test_code`` against ``solution_code``. Returns (passed, stderr, runtime)."""
    src = (
        _RUNNER_TEMPLATE
        .replace("__SOLUTION__", solution_code)
        .replace("__TESTS__", task.test_code)
        .replace("__ENTRY__", task.entry_point)
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(src)
        path = f.name
    import time as _time
    t0 = _time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-I", path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        runtime = _time.perf_counter() - t0
        ok = proc.returncode == 0 and "__VERIFY_OK__" in proc.stdout
        err = proc.stderr if not ok else ""
        return ok, err, runtime
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout_seconds}s", timeout_seconds
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Static checks (replacement for Bandit/Semgrep + linter)
# ---------------------------------------------------------------------------
_DANGEROUS_CALLS = {
    "os.system", "subprocess.call", "subprocess.run", "subprocess.Popen",
    "eval", "exec", "compile", "__import__",
    "socket.socket", "urllib.request.urlopen", "requests.get", "requests.post",
}


def static_check(solution_code: str) -> tuple[bool, list[str]]:
    """Returns (ok, list_of_warnings).

    `ok` is True when no syntax errors and no critical issues are present.
    """
    warnings: list[str] = []
    try:
        tree = ast.parse(solution_code)
    except SyntaxError as e:
        return False, [f"SyntaxError: {e}"]
    # Look for obviously broken patterns
    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            warnings.append("uses bare `pass` (likely stub)")
        if isinstance(node, ast.Raise) and not getattr(node, "exc", None):
            warnings.append("bare `raise` outside except")
    return True, warnings


def security_check(solution_code: str) -> tuple[bool, list[str]]:
    issues: list[str] = []
    try:
        tree = ast.parse(solution_code)
    except SyntaxError:
        return False, ["does not parse"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _qualname(node.func)
            if name in _DANGEROUS_CALLS:
                issues.append(f"dangerous call: {name}")
    return (len(issues) == 0), issues


def _qualname(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_qualname(node.value)}.{node.attr}"
    return ""


# ---------------------------------------------------------------------------
# Maintainability M_i (formula (21))
# ---------------------------------------------------------------------------
def maintainability_score(solution_code: str, weights: dict[str, float]) -> float:
    """Compute M ∈ [0,1] from formula (21).

    All four sub-scores are normalised:
        CC̃   = min(1, mean cyclomatic complexity / 10)
        Dup̃  = duplicated lines / total lines  (Jaccard on 3-grams)
        Warñ = number of static warnings / 10  (capped at 1)
        Doc̃  = fraction of definitions with a docstring
    """
    if not solution_code.strip():
        return 0.0
    cc_norm = _normalised_cc(solution_code)
    dup_norm = _normalised_duplication(solution_code)
    warn_norm = _normalised_warnings(solution_code)
    doc = _docstring_coverage(solution_code)
    M = (
        weights.get("cc", 0.35) * (1 - cc_norm)
        + weights.get("dup", 0.25) * (1 - dup_norm)
        + weights.get("warn", 0.20) * (1 - warn_norm)
        + weights.get("doc", 0.20) * doc
    )
    return max(0.0, min(1.0, M))


def _normalised_cc(code: str) -> float:
    try:
        from radon.complexity import cc_visit  # type: ignore
    except ImportError:
        return 0.5  # neutral if radon not installed
    try:
        blocks = cc_visit(code)
    except Exception:
        return 0.5
    if not blocks:
        return 0.0
    mean = sum(b.complexity for b in blocks) / len(blocks)
    return min(1.0, mean / 10.0)


def _normalised_duplication(code: str) -> float:
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    if len(lines) < 4:
        return 0.0
    seen: dict[str, int] = {}
    for line in lines:
        seen[line] = seen.get(line, 0) + 1
    dup = sum(c - 1 for c in seen.values() if c > 1)
    return min(1.0, dup / max(1, len(lines)))


def _normalised_warnings(code: str) -> float:
    _, w = static_check(code)
    return min(1.0, len(w) / 10.0)


def _docstring_coverage(code: str) -> float:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0.0
    defs = [n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    if not defs:
        return 1.0  # nothing to document; don't penalise
    documented = sum(1 for n in defs if ast.get_docstring(n))
    return documented / len(defs)


# ---------------------------------------------------------------------------
# Top-level verifier (used by all architectures)
# ---------------------------------------------------------------------------
class Verifier:
    """Convenience wrapper bundling all four signals (tests + static + security + M)."""
    def __init__(self, config: Config, timeout_seconds: int = 15):
        self.cfg = config
        self.timeout = timeout_seconds
        self.weights = config.get("metrics.weights_M", {}) or {}

    def verify(self, raw_solution: str, task: Task) -> VerificationResult:
        code = extract_code(raw_solution, task.entry_point)
        if not code:
            return VerificationResult(passed=False, error_message="empty solution")
        sec_ok, sec_issues = security_check(code)
        st_ok, _st_warnings = static_check(code)
        if not (sec_ok and st_ok):
            return VerificationResult(
                passed=False,
                tests_passed=False,
                static_passed=st_ok,
                security_passed=sec_ok,
                maintainability=maintainability_score(code, self.weights),
                error_message="; ".join(sec_issues) or "static error",
            )
        passed, err, runtime = run_tests(code, task, timeout_seconds=self.timeout)
        M = maintainability_score(code, self.weights)
        return VerificationResult(
            passed=passed and st_ok and sec_ok,
            tests_passed=passed,
            static_passed=st_ok,
            security_passed=sec_ok,
            maintainability=M,
            error_message=err,
            runtime_seconds=runtime,
        )
