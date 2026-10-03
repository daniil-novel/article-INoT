from inot.architectures import make
from inot.config import Config
from inot.llm import DryRunClient
from inot.tasks import build_controlled_context_suite, build_synthetic_tool_use_suite
from inot.tools.synthetic import measure_synthetic_tool_latency


def _config():
    return Config({
        "llm": {
            "large_model": "test/large",
            "small_model": "test/small",
            "hard_budget_usd": 1.0,
            "prices_usd_per_mtok": {
                "test/large": {"input": 1.0, "output": 2.0},
                "test/small": {"input": 0.1, "output": 0.2},
            },
        },
        "architectures": {"K": 3, "I": 1, "R": 0, "M": 1, "stagnation_eps": 0.02},
        "routing": {"enable": True, "tau_route_star_tokens": 1024},
        "compression": {"enable": True, "tau_len_tokens": 128},
        "metrics": {"lambda_maintainability": 0.5, "weights_M": {}},
    })


def test_controlled_context_suite_scales_context_without_solution_leakage():
    tasks = build_controlled_context_suite(n=3, context_target_tokens=512, seed=7)
    assert len(tasks) == 3
    assert all(t.suite == "controlled_context" for t in tasks)
    assert all(t.metadata["context_actual_tokens"] >= 512 for t in tasks)
    assert all("return text" not in t.context for t in tasks)


def test_no_assistant_baseline_uses_zero_llm_calls():
    cfg = _config()
    llm = DryRunClient(cfg)
    agent = make("CTRL", llm=llm, config=cfg)
    result = agent.run(build_controlled_context_suite(n=1, context_target_tokens=32)[0], seed=42)
    assert result.architecture == "CTRL_NoAssistant"
    assert result.total_tokens == 0
    assert result.total_cost_usd == 0.0
    assert result.total_cost_rub == 0.0


def test_synthetic_tool_latency_parallel_is_faster_than_serial():
    tasks = build_synthetic_tool_use_suite(n=2, seed=2)
    serial = measure_synthetic_tool_latency(tasks, mode="serial")
    parallel = measure_synthetic_tool_latency(tasks, mode="parallel")
    assert sum(r.expected_latency_ms for r in serial) > sum(r.expected_latency_ms for r in parallel)


def test_dry_run_records_rub_cost_from_fixed_rate():
    cfg = _config()
    llm = DryRunClient(cfg)
    result = llm.chat([{"role": "user", "content": "hello"}], "test/large", max_tokens=10)
    assert result.usage.cost_usd > 0
    assert result.usage.cost_rub == result.usage.cost_usd * cfg.usd_to_rub()
