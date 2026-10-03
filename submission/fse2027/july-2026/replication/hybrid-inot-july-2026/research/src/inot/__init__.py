"""Hybrid-INoT empirical validation package.

Implements four agent architectures and five experiments (E1-E5) from
Anonymous authors (2026), "Hybrid-INoT: гибридная агентная архитектура с внутренней
ролевой сегрегацией для инженерных задач в условиях длинного общего контекста".

Public submodules:
    inot.types          - common dataclasses (Task, RunResult, TokenUsage)
    inot.config         - load YAML config with overrides
    inot.llm            - OpenRouter client with token+cost accounting
    inot.tasks          - HumanEval and Synthetic Tool-Use Suite loaders
    inot.architectures  - B0 SingleLarge, B1 SelfRefine, B2 ClassicalMAS, B3 HybridINoT
    inot.verification   - sandboxed test execution and code-quality checks
    inot.metrics        - U_tok, Q$, VCR, MAS_i, statistical tests
    inot.compression    - LLMLingua-style relevance compression
    inot.cli            - typer entrypoint
"""
__version__ = "0.1.0"
