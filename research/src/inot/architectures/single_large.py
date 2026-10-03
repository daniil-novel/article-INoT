"""B0 Single-Large: one shot, no iteration. Control configuration of E1."""
from __future__ import annotations

from ..types import RunResult, Task, TokenUsage
from .base import BaseAgent


class SingleLargeAgent(BaseAgent):
    name = "B0_SingleLarge"

    def _solve(self, task: Task, seed: int, usages: list[TokenUsage]) -> RunResult:
        messages = [
            {"role": "system", "content": self._system_for_role("solver")},
            {"role": "user", "content": self._build_user_prompt(task)},
        ]
        res = self.llm.chat(
            messages, model=self.large_model,
            role="solver", architecture=self.name, iteration=1, seed=seed,
            max_tokens=1024,
        )
        self._record(usages, res.usage)
        verification = self.verifier.verify(res.text, task)
        return RunResult(
            task_id=task.task_id, architecture=self.name, seed=seed,
            final_solution=res.text, verification=verification,
            usages=usages, iterations_used=1, rerun_count=0,
        )
