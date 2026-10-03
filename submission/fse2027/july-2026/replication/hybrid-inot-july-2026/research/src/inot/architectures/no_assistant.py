"""CTRL baseline: no assistant / no LLM calls.

This is the control configuration from the coursework text. It represents the
state before an assistant contributes generated code: zero model cost, zero
model latency, and only the task starter scaffold is submitted to the verifier.

It is intentionally pessimistic for HumanEval, but scientifically useful: it
anchors productivity metrics against a non-assistant baseline without silently
spending tokens or asking an LLM to play "the human".
"""
from __future__ import annotations

from ..types import RunResult, Task, TokenUsage
from .base import BaseAgent


class NoAssistantAgent(BaseAgent):
    name = "CTRL_NoAssistant"

    def _solve(self, task: Task, seed: int, usages: list[TokenUsage]) -> RunResult:
        scaffold = _starter_scaffold(task)
        verification = self.verifier.verify(scaffold, task)
        return RunResult(
            task_id=task.task_id,
            architecture=self.name,
            seed=seed,
            final_solution=scaffold,
            verification=verification,
            usages=usages,
            iterations_used=0,
            extra={"control": "no_llm_no_assistant"},
        )


def _starter_scaffold(task: Task) -> str:
    prompt = task.prompt.rstrip()
    if f"def {task.entry_point}" in prompt:
        return f"```python\n{prompt}\n    pass\n```"
    return f"```python\ndef {task.entry_point}(*args, **kwargs):\n    pass\n```"
