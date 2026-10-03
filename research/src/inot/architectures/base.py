"""Common base for all agents (B0/B1/B2/B3)."""
from __future__ import annotations

import abc

from ..config import Config
from ..types import RunResult, Task, TokenUsage, WallClock
from ..verification import Verifier, extract_code


class BaseAgent(abc.ABC):
    name: str = "base"

    def __init__(self, llm, config: Config, *, verifier: Verifier | None = None, **kwargs):
        self.llm = llm
        self.cfg = config
        self.verifier = verifier or Verifier(config)
        self.large_model = config.large_model
        self.small_model = config.small_model
        self.K = int(config.get("architectures.K", 3))
        self.I = int(config.get("architectures.I", 3))
        self.R = int(config.get("architectures.R", 1))
        self.M = int(config.get("architectures.M", 3))
        self.stagnation_eps = float(config.get("architectures.stagnation_eps", 0.02))

    # ----- public API -------------------------------------------------------
    def run(self, task: Task, seed: int) -> RunResult:
        usages: list[TokenUsage] = []
        with WallClock() as wc:
            result = self._solve(task, seed, usages)
        result.wall_clock_seconds = wc.elapsed
        return result

    # ----- subclasses implement this ---------------------------------------
    @abc.abstractmethod
    def _solve(self, task: Task, seed: int, usages: list[TokenUsage]) -> RunResult: ...

    # ----- helpers shared by subclasses ------------------------------------
    def _build_user_prompt(self, task: Task) -> str:
        """Generic 'task + context' prompt skeleton."""
        ctx_section = (
            f"### Project context\n{task.context}\n\n" if task.context.strip() else ""
        )
        return (
            f"{ctx_section}### Task\n{task.prompt}\n\n"
            f"Return ONLY the complete Python source. Define a function called "
            f"`{task.entry_point}`. Wrap your answer in a single ```python``` block."
        )

    def _system_for_role(self, role: str) -> str:
        return _SYSTEM_PROMPTS[role]

    def _record(self, usages: list[TokenUsage], usage: TokenUsage) -> None:
        usage.architecture = self.name
        usages.append(usage)

    def _extract(self, raw: str, task: Task) -> str:
        return extract_code(raw, task.entry_point)


# ---------------------------------------------------------------------------
# Role-specific system prompts shared by B1/B2/B3
# ---------------------------------------------------------------------------
_SYSTEM_PROMPTS: dict[str, str] = {
    "solver": (
        "You are a senior Python engineer. Produce a correct, minimal solution "
        "to the user's task. Output ONLY a single fenced ```python``` block "
        "containing the complete source; no commentary, no explanation."
    ),
    "planner": (
        "You are the PLANNER role. Read the task and the project context, then "
        "produce a short numbered plan (3-7 bullet steps) for solving the task. "
        "Do NOT write code. Output ONLY the plan."
    ),
    "worker": (
        "You are the WORKER role. You receive a PLAN and the task description. "
        "Produce K diverse candidate Python solutions. Use this exact format:\n"
        "<<CANDIDATE 1>>\n```python\n...code...\n```\n"
        "<<CANDIDATE 2>>\n```python\n...code...\n```\n"
        "...\n"
        "Each candidate must define the requested function."
    ),
    "critic": (
        "You are the CRITIC role. Score every candidate on a 0.0-1.0 scale "
        "based on (a) likely correctness on hidden tests, (b) edge-case handling, "
        "(c) code smell. Output ONLY a JSON object: "
        '{"scores": [s1, s2, ...]}'
    ),
    "self_refiner": (
        "You are a senior Python engineer reviewing your own previous solution. "
        "List the most likely defects and produce an improved version. Output ONLY "
        "the new solution as a single ```python``` fenced block."
    ),
    "small_check": (
        "You are a fast pre-screener. Decide whether the candidate solution is "
        "obviously broken (syntax errors, missing function, wrong signature, "
        "trivially wrong logic). Reply with ONE WORD: PASS or REJECT."
    ),
    "hybrid_inot": (
        "You are an Hybrid-INoT agent. Inside ONE response you will play three "
        "roles in sequence over a SHARED compressed context. Use exactly these "
        "section markers and order:\n\n"
        "===PLAN===\n<numbered plan, 3-7 lines>\n\n"
        "===CANDIDATES===\n"
        "<<CANDIDATE 1>>\n```python\n...\n```\n"
        "<<CANDIDATE 2>>\n```python\n...\n```\n"
        "<<CANDIDATE 3>>\n```python\n...\n```\n\n"
        "===CRITIQUE===\n"
        '{"scores": [s1, s2, s3], "best": <0-based index>, "rationale": "<short>"}\n\n'
        "Do not output anything outside these sections."
    ),
}
