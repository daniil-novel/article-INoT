"""B1 Self-Refine (Madaan et al. 2023): generator -> feedback -> revise loop.

We implement the *original* Self-Refine: each iteration the same model is
asked to (a) critique its previous output then (b) emit a revised solution.
Stops on either external test-pass or after I iterations."""
from __future__ import annotations

from ..types import RunResult, Task, TokenUsage
from .base import BaseAgent


class SelfRefineAgent(BaseAgent):
    name = "B1_SelfRefine"

    def _solve(self, task: Task, seed: int, usages: list[TokenUsage]) -> RunResult:
        # First draft
        msgs = [
            {"role": "system", "content": self._system_for_role("solver")},
            {"role": "user", "content": self._build_user_prompt(task)},
        ]
        res = self.llm.chat(msgs, model=self.large_model,
                            role="solver", architecture=self.name, iteration=1, seed=seed,
                            max_tokens=1024)
        self._record(usages, res.usage)
        best_solution = res.text
        verification = self.verifier.verify(best_solution, task)
        iteration = 1
        if verification.passed:
            return RunResult(
                task_id=task.task_id, architecture=self.name, seed=seed,
                final_solution=best_solution, verification=verification,
                usages=usages, iterations_used=iteration,
            )

        # Refinement loop
        for it in range(2, self.I + 1):
            iteration = it
            refine_msgs = [
                {"role": "system", "content": self._system_for_role("self_refiner")},
                {"role": "user", "content": (
                    f"Original task:\n{task.prompt}\n\n"
                    f"Your previous solution:\n```python\n{self._extract(best_solution, task)}\n```\n\n"
                    f"Critique it and produce a corrected version."
                )},
            ]
            res = self.llm.chat(refine_msgs, model=self.large_model,
                                role="self_refiner", architecture=self.name,
                                iteration=it, seed=seed, max_tokens=1024)
            self._record(usages, res.usage)
            verification = self.verifier.verify(res.text, task)
            if verification.passed:
                best_solution = res.text
                break
            # accept if at least it parses; else keep previous
            if res.text.strip():
                best_solution = res.text
        return RunResult(
            task_id=task.task_id, architecture=self.name, seed=seed,
            final_solution=best_solution, verification=verification,
            usages=usages, iterations_used=iteration,
        )
