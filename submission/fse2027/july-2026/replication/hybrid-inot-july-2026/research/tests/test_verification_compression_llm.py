import pytest

from inot.compression import compress
from inot.config import Config
from inot.llm import BudgetExceeded, OpenRouterClient
from inot.tasks import build_synthetic_tool_use_suite
from inot.types import Task
from inot.verification import Verifier, extract_code, run_tests, security_check


def _config(**overrides):
    raw = {
        "llm": {
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url": "https://openrouter.ai/api/v1",
            "large_model": "test/large",
            "small_model": "test/small",
            "hard_budget_usd": 1.0,
            "prices_usd_per_mtok": {
                "test/large": {"input": 1.0, "output": 2.0},
                "test/small": {"input": 0.1, "output": 0.2},
            },
        },
        "metrics": {"weights_M": {"cc": 0.35, "dup": 0.25, "warn": 0.20, "doc": 0.20}},
    }
    for dotted, value in overrides.items():
        node = raw
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return Config(raw)


def test_extract_code_prefers_fenced_block_with_entry_point():
    raw = """
Some reasoning.
```python
def other():
    return 0
```
```python
def target():
    return 42
```
"""
    assert extract_code(raw, "target").startswith("def target")


def test_verifier_runs_humaneval_style_check():
    task = Task(
        task_id="toy",
        prompt="Implement add_one",
        context="",
        test_code="def check(candidate):\n    assert candidate(2) == 3\n",
        entry_point="add_one",
    )
    verifier = Verifier(_config(), timeout_seconds=3)
    result = verifier.verify("def add_one(x):\n    return x + 1\n", task)
    assert result.passed
    assert result.tests_passed
    assert result.security_passed


def test_security_check_blocks_dangerous_calls():
    ok, issues = security_check("import os\ndef f():\n    os.system('echo no')\n")
    assert not ok
    assert any("os.system" in issue for issue in issues)


def test_compression_respects_tau_and_keeps_signatures():
    context = "\n\n".join(
        [
            "def important_api(x):\n    return x + 1",
            "# noisy notes\n" + ("lorem ipsum " * 500),
            "Traceback: ValueError in important_api",
        ]
    )
    result = compress(context, "Call important_api safely", tau_len=80)
    assert result.compressed_tokens <= 80
    assert "important_api" in result.text


def test_openrouter_preflight_budget_guard(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    cfg = _config(**{"llm.hard_budget_usd": 0.000001})
    client = OpenRouterClient(cfg)
    try:
        with pytest.raises(BudgetExceeded):
            client.chat(
                [{"role": "user", "content": "hello"}],
                "test/large",
                max_tokens=1000,
            )
    finally:
        client.close()


def test_synthetic_tool_suite_verifier_contract():
    task = build_synthetic_tool_use_suite(n=1, seed=1)[0]
    ops = task.metadata["ops"]
    source = "\n".join(f"def f{i}():\n    return {a + b if op == 'add' else a * b if op == 'mul' else a - b}\n" for i, (op, a, b) in enumerate(ops))
    passed, err, _runtime = run_tests(source, task, timeout_seconds=3)
    assert passed, err
