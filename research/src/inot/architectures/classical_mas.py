"""B2 Classical-MAS: planner + worker + critic as SEPARATE LLM calls.

This is the baseline H1 attacks: each role re-receives the full context C0,
incurring the Θ(|A|·|C0|) overhead from formula (1) of the article. We
intentionally pass the *unsanitised, uncompressed* context to every role to
mirror MetaGPT/ChatDev behaviour — that is precisely what makes the
comparison with Hybrid-INoT (B3) meaningful.
"""
from __future__ import annotations

import json
import re

from ..types import RunResult, Task, TokenUsage
from .base import BaseAgent


_CAND_RE = re.compile(r"<<\s*CANDIDATE\s+(\d+)\s*>>\s*```(?:python|py)?\s*\n(.*?)```",
                      re.DOTALL | re.IGNORECASE)


class ClassicalMASAgent(BaseAgent):
    name = "B2_ClassicalMAS"

    def _solve(self, task: Task, seed: int, usages: list[TokenUsage]) -> RunResult:
        ctx_block = (
            f"### Project context (shared across all roles)\n{task.context}\n\n"
            if task.context.strip() else ""
        )
        best_solution = ""
        verification = None
        used_iter = 0
        for it in range(1, self.I + 1):
            used_iter = it
            # ---- 1. Planner -----------------------------------------------
            plan_text, plan_usage = self._call(
                "planner", role_msg=self._system_for_role("planner"),
                user_msg=ctx_block + f"### Task\n{task.prompt}",
                seed=seed, iteration=it, max_tokens=400,
            )
            self._record(usages, plan_usage)

            # ---- 2. Worker (K candidates) ---------------------------------
            worker_user = (
                ctx_block
                + f"### Task\n{task.prompt}\n\n"
                + f"### Plan\n{plan_text}\n\n"
                + f"Produce K={self.K} diverse candidate solutions."
            )
            cand_text, work_usage = self._call(
                "worker", role_msg=self._system_for_role("worker"),
                user_msg=worker_user, seed=seed, iteration=it,
                max_tokens=1024 * self.K,
            )
            self._record(usages, work_usage)
            candidates = self._parse_candidates(cand_text, k=self.K)
            if not candidates:
                continue

            # ---- 3. Critic -------------------------------------------------
            critic_user = (
                ctx_block + f"### Task\n{task.prompt}\n\n"
                + "### Candidates to score\n"
                + "\n".join(f"<<CANDIDATE {i+1}>>\n```python\n{c}\n```"
                           for i, c in enumerate(candidates))
            )
            crit_text, crit_usage = self._call(
                "critic", role_msg=self._system_for_role("critic"),
                user_msg=critic_user, seed=seed, iteration=it, max_tokens=300,
            )
            self._record(usages, crit_usage)
            scores = self._parse_scores(crit_text, n=len(candidates))
            best_idx = max(range(len(candidates)), key=lambda i: scores[i])
            best_solution = f"```python\n{candidates[best_idx]}\n```"

            # ---- 4. External verification (r_self) ------------------------
            verification = self.verifier.verify(best_solution, task)
            if verification.passed:
                break
        if verification is None:
            from ..types import VerificationResult
            verification = VerificationResult(passed=False, error_message="no candidate produced")
        return RunResult(
            task_id=task.task_id, architecture=self.name, seed=seed,
            final_solution=best_solution, verification=verification,
            usages=usages, iterations_used=used_iter,
        )

    # ---------------------------------------------------------------------
    def _call(self, role: str, *, role_msg: str, user_msg: str,
              seed: int, iteration: int, max_tokens: int) -> tuple[str, TokenUsage]:
        res = self.llm.chat(
            [{"role": "system", "content": role_msg},
             {"role": "user", "content": user_msg}],
            model=self.large_model, role=role, architecture=self.name,
            iteration=iteration, seed=seed, max_tokens=max_tokens,
        )
        return res.text, res.usage

    @staticmethod
    def _parse_candidates(text: str, k: int) -> list[str]:
        matches = _CAND_RE.findall(text or "")
        cands = [m[1].strip() for m in matches]
        if cands:
            return cands[:k]
        # Fallback: any python fence
        blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text or "", re.DOTALL)
        return [b.strip() for b in blocks[:k]] if blocks else []

    @staticmethod
    def _parse_scores(text: str, n: int) -> list[float]:
        # Look for {"scores": [...]}
        try:
            obj_match = re.search(r"\{.*?\"scores\".*?\}", text or "", re.DOTALL)
            if obj_match:
                obj = json.loads(obj_match.group(0))
                scores = obj.get("scores", [])
                if isinstance(scores, list) and len(scores) >= n:
                    return [float(s) for s in scores[:n]]
        except (ValueError, json.JSONDecodeError):
            pass
        # Fallback: equal scores
        return [0.5] * n
