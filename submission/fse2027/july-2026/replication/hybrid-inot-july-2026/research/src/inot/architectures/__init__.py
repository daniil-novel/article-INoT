"""Agent architectures compared in the article (§7.2):

* ``NoAssistantAgent`` - CTRL: no LLM calls, starter scaffold only
* ``SingleLargeAgent``  - B0: one call to the large model, no iteration
* ``SelfRefineAgent``   - B1: Madaan et al. 2023 in-context self-refine, I=3
* ``ClassicalMASAgent`` - B2: planner + worker + critic as SEPARATE LLM calls
                              (MetaGPT-style; this is the baseline H1/H2 attack)
* ``HybridINoTAgent``   - B3: planner+worker+critic *as role prefixes inside
                              one large-model call* over a compressed context,
                              with selective rerun and external verification.

All four expose the same ``run(task, seed) -> RunResult`` interface so that
``inot.experiments`` can swap them mechanically.
"""
from .base import BaseAgent
from .single_large import SingleLargeAgent
from .self_refine import SelfRefineAgent
from .classical_mas import ClassicalMASAgent
from .hybrid_inot import HybridINoTAgent
from .no_assistant import NoAssistantAgent

__all__ = [
    "BaseAgent",
    "NoAssistantAgent",
    "SingleLargeAgent",
    "SelfRefineAgent",
    "ClassicalMASAgent",
    "HybridINoTAgent",
    "make",
]

_REGISTRY = {
    "CTRL": NoAssistantAgent,
    "B0": SingleLargeAgent,
    "B1": SelfRefineAgent,
    "B2": ClassicalMASAgent,
    "B3": HybridINoTAgent,
}


def make(name: str, llm, config, **kwargs) -> BaseAgent:
    """Factory: ``make("B3", llm, cfg)`` → HybridINoTAgent instance."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown architecture {name!r}; choose from {sorted(_REGISTRY)}")
    return _REGISTRY[name](llm=llm, config=config, **kwargs)
