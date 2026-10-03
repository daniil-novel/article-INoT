"""B3 Hybrid-INoT: the architecture proposed by the article (Definition 3).

Implementation map:
    Algorithm 1 (внутренний цикл) ->  HybridINoTAgent._solve
    Algorithm 2 (compression)     ->  inot.compression.compress
    Algorithm 3 (selective rerun) ->  HybridINoTAgent._selective_rerun
    Definition 4 (RouteMode)      ->  HybridINoTAgent._route_mode

Key design choice (matching the article): roles plan / work / crit are
*role prefixes inside ONE LLM call* over the compressed shared context Ĉ.
Only r_self (external verification) leaves the model.

The agent records every TokenUsage with a ``role`` tag so downstream metrics
can decompose the budget exactly the way §5.2 prescribes.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..compression import compress
from ..llm import count_tokens
from ..types import RunResult, Task, TokenUsage, VerificationResult
from .base import BaseAgent
from .classical_mas import ClassicalMASAgent


_PLAN_RE = re.compile(r"===\s*PLAN\s*===\s*(.*?)===\s*CANDIDATES\s*===", re.DOTALL | re.IGNORECASE)
_CANDS_RE = re.compile(r"===\s*CANDIDATES\s*===\s*(.*?)===\s*CRITIQUE\s*===", re.DOTALL | re.IGNORECASE)
_CRIT_RE = re.compile(r"===\s*CRITIQUE\s*===\s*(.*)$", re.DOTALL | re.IGNORECASE)
_CAND_BLOCK_RE = re.compile(
    r"<<\s*CANDIDATE\s+(\d+)\s*>>\s*```(?:python|py)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class _InotPayload:
    plan: str
    candidates: list[str]
    scores: list[float]
    best_idx: int
    rationale: str


class HybridINoTAgent(BaseAgent):
    name = "B3_HybridINoT"

    def __init__(self, llm, config, *, ablate: dict[str, bool] | None = None, **kwargs):
        """``ablate`` toggles the components for E2a:
            {"compression": False}  -> B3a (no compression)
            {"critic": False}       -> B3b (no internal critic)
            {"self_check": False}   -> B3c (no external verification gating)
        Defaults: all components enabled (= the full B3).
        """
        super().__init__(llm, config, **kwargs)
        self.ablate = {"compression": True, "critic": True, "self_check": True}
        if ablate:
            self.ablate.update(ablate)
        self.tau_route_star = int(config.get("routing.tau_route_star_tokens", 1024))
        self.tau_len = int(config.get("compression.tau_len_tokens", 4096))
        self.routing_enabled = bool(config.get("routing.enable", True))
        self.compression_enabled = bool(config.get("compression.enable", True)) and self.ablate["compression"]

    # ----------------------------------------------------------------------
    def _solve(self, task: Task, seed: int, usages: list[TokenUsage]) -> RunResult:
        # 1. PolicySanitize is a no-op for HumanEval-style code; if you wire up
        #    real repository data here, plug your scrubber in.
        c = task.context

        # 2. Compression  (Algorithm 2)
        comp = compress(c, prompt=task.prompt, tau_len=self.tau_len, enable=self.compression_enabled)
        c_hat = comp.text

        # 3. RouteMode  (Definition 4)
        mode = self._route_mode(task, c_hat)
        if mode == "external" and self.routing_enabled:
            # Fall back to Classical-MAS in the regimes Hybrid-INoT does not target
            external = ClassicalMASAgent(self.llm, self.cfg, verifier=self.verifier)
            external.name = "B3_HybridINoT(routed→ext)"
            r = external._solve(task, seed, usages)
            r.architecture = self.name
            r.routed_external = True
            r.extra["compression_ratio"] = comp.ratio
            r.extra["routed_external_reason"] = "RouteMode=external"
            return r

        # 4. Inner introspective loop  (Algorithm 1)
        best_solution = ""
        verification: VerificationResult | None = None
        prev_best_score = -1.0
        used_iter = 0
        rerun_count = 0
        last_failure_signal = ""

        for it in range(1, self.I + 1):
            used_iter = it
            payload = self._inot_call(
                task, c_hat=c_hat, seed=seed, iteration=it,
                failure_signal=last_failure_signal, usages=usages,
            )
            if not payload.candidates:
                continue

            # If critic is ablated, fall back to the first candidate
            if not self.ablate["critic"]:
                idx = payload.best_idx
            else:
                idx = payload.best_idx if payload.scores else 0
            best_candidate = payload.candidates[idx]
            best_solution = f"```python\n{best_candidate}\n```"

            # External verification (r_self) — gating skipped if ablate[self_check] off
            if self.ablate["self_check"]:
                verification = self.verifier.verify(best_solution, task)
                if verification.passed:
                    break
                last_failure_signal = (
                    f"Tests failed (iteration {it}). Stderr (truncated):\n"
                    f"{(verification.error_message or '')[:600]}"
                )
            else:
                verification = self.verifier.verify(best_solution, task)
                # do not iterate further on success
                if verification.passed:
                    break

            # Selective rerun (Algorithm 3) — only on the *last* iteration's worth
            # of candidates if budget remains.
            if rerun_count < self.R:
                rerun_count += 1
                rerun_solution, rerun_verification = self._selective_rerun(
                    task, payload.candidates, payload.scores, seed, iteration=it,
                    usages=usages,
                )
                if rerun_verification is not None and rerun_verification.passed:
                    best_solution = rerun_solution
                    verification = rerun_verification
                    break

            # Stagnation early-exit
            cur_score = max(payload.scores) if payload.scores else 0.0
            if it > 1 and (cur_score - prev_best_score) < self.stagnation_eps:
                break
            prev_best_score = cur_score

        if verification is None:
            verification = VerificationResult(passed=False, error_message="no candidate produced")

        return RunResult(
            task_id=task.task_id, architecture=self.name, seed=seed,
            final_solution=best_solution, verification=verification,
            usages=usages, iterations_used=used_iter, rerun_count=rerun_count,
            routed_external=False,
            extra={
                "compression_ratio": comp.ratio,
                "compressed_tokens": comp.compressed_tokens,
                "original_context_tokens": comp.original_tokens,
                "ablate": dict(self.ablate),
            },
        )

    # ----------------------------------------------------------------------
    def _route_mode(self, task: Task, c_hat: str) -> str:
        """Definition 4: external if (φ_tool ∨ φ_par ∨ |Ĉ|<τ_route)."""
        if task.metadata.get("force_hybrid_internal", False):
            return "internal"
        if not self.routing_enabled:
            return "internal"
        phi_tool = 1 if task.metadata.get("requires_tool", False) else 0
        phi_par = 1 if task.metadata.get("parallelism", 0) >= 2 else 0
        if phi_tool or phi_par or count_tokens(c_hat) < self.tau_route_star:
            # The article: use external for tool-heavy/parallel/short contexts.
            # We only auto-route when one of φ_tool / φ_par is set; otherwise
            # context-shorter-than-τ_route still runs internal so that E1 with
            # short contexts does not collapse to B2.
            if phi_tool or phi_par:
                return "external"
        return "internal"

    # ----------------------------------------------------------------------
    def _inot_call(self, task: Task, *, c_hat: str, seed: int, iteration: int,
                   failure_signal: str, usages: list[TokenUsage]) -> _InotPayload:
        """One call to the LLM with internal plan/work/crit role prefixes."""
        ctx_block = (
            f"### Compressed shared context\n{c_hat}\n\n" if c_hat.strip() else ""
        )
        failure_block = (
            f"### Previous-iteration failure signals (verbatim from tools)\n"
            f"{failure_signal}\n\n" if failure_signal else ""
        )
        user = (
            ctx_block
            + failure_block
            + f"### Task\n{task.prompt}\n\n"
            + f"Generate K={self.K} candidate solutions. The function must be named "
            + f"`{task.entry_point}`."
        )
        res = self.llm.chat(
            [{"role": "system", "content": self._system_for_role("hybrid_inot")},
             {"role": "user", "content": user}],
            model=self.large_model, role="inot_combined",
            architecture=self.name, iteration=iteration, seed=seed,
            max_tokens=2048 + 700 * self.K,
        )
        self._record(usages, res.usage)
        return self._parse_inot(res.text)

    # ----------------------------------------------------------------------
    def _parse_inot(self, text: str) -> _InotPayload:
        plan = _PLAN_RE.search(text or "")
        cands_blob = _CANDS_RE.search(text or "")
        crit = _CRIT_RE.search(text or "")
        plan_text = plan.group(1).strip() if plan else ""
        cand_blocks: list[str] = []
        if cands_blob:
            for m in _CAND_BLOCK_RE.finditer(cands_blob.group(1)):
                cand_blocks.append(m.group(2).strip())
        if not cand_blocks:
            # Fallback: any python fences anywhere in the response
            cand_blocks = [b.strip() for b in re.findall(r"```(?:python|py)?\s*\n(.*?)```", text or "", re.DOTALL)]
        scores: list[float] = []
        best_idx = 0
        rationale = ""
        if crit:
            try:
                obj = json.loads(re.search(r"\{.*\}", crit.group(1), re.DOTALL).group(0))
                scores = [float(s) for s in obj.get("scores", [])]
                best_idx = int(obj.get("best", 0))
                rationale = str(obj.get("rationale", ""))[:400]
            except Exception:
                pass
        if not scores:
            scores = [0.5] * len(cand_blocks)
        if best_idx < 0 or best_idx >= len(cand_blocks):
            best_idx = max(range(len(cand_blocks)), key=lambda i: scores[i]) if cand_blocks else 0
        return _InotPayload(
            plan=plan_text, candidates=cand_blocks, scores=scores,
            best_idx=best_idx, rationale=rationale,
        )

    # ----------------------------------------------------------------------
    def _selective_rerun(self, task: Task, candidates: list[str], scores: list[float],
                         seed: int, iteration: int,
                         usages: list[TokenUsage]) -> tuple[str, VerificationResult | None]:
        """Algorithm 3: try top-M candidates against ExternalVerify; if none pass,
        re-prompt using ONLY confirmed (tool-derived) failure signals."""
        order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)[: self.M]
        last_err = ""
        for idx in order:
            sol = f"```python\n{candidates[idx]}\n```"
            v = self.verifier.verify(sol, task)
            if v.passed:
                return sol, v
            last_err = (v.error_message or "").strip()[:600]

        # Confirmed-signal re-prompt (one extra call)
        if not last_err:
            return f"```python\n{candidates[order[0]]}\n```", None
        msgs = [
            {"role": "system", "content": (
                "You are a senior Python engineer. Given the previous candidate AND the "
                "verbatim test-runner output, produce a corrected solution. Output ONLY "
                "a single ```python``` fenced block.")},
            {"role": "user", "content": (
                f"### Task\n{task.prompt}\n\n"
                f"### Previous candidate\n```python\n{candidates[order[0]]}\n```\n\n"
                f"### Confirmed failure signal from external tools\n{last_err}\n\n"
                f"Produce a corrected version."
            )},
        ]
        res = self.llm.chat(
            msgs, model=self.large_model, role="rerun",
            architecture=self.name, iteration=iteration, seed=seed,
            max_tokens=1024,
        )
        self._record(usages, res.usage)
        v = self.verifier.verify(res.text, task)
        return res.text, v
