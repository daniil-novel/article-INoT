"""Typer-based CLI: ``python -m inot --help``.

Subcommands map 1:1 to the article's experiments E1..E5 plus utility ``view``
(rich rendering of result JSONs) and ``check`` (smoke-test plumbing without
spending real tokens).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import httpx
import typer
from rich.console import Console

# Ensure UTF-8 stdio on Windows consoles that default to cp1251/cp866.
# Without this, rich crashes on Δ, σ, ρ, τ, etc. used in result panels.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from .config import load_config, project_root

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
console = Console()
app = typer.Typer(add_completion=False, help="Hybrid-INoT empirical validation suite (Anonymous authors 2026).")


# ---------------------------------------------------------------------------
@app.command()
def check(
    config: Path = typer.Option(project_root() / "config.yaml", help="Path to config.yaml"),
):
    """Quick smoke test (no network) — verifies imports and DryRunClient wiring."""
    from .architectures import make
    from .llm import DryRunClient
    from .tasks import load_humaneval

    cfg = load_config(config)
    llm = DryRunClient(cfg)
    tasks = load_humaneval(n=2, context_target_tokens=256, seed=42)
    for arch in ("B0", "B1", "B2", "B3"):
        agent = make(arch, llm=llm, config=cfg)
        r = agent.run(tasks[0], seed=42)
        console.log(f"{arch}: tokens={r.total_tokens} cost=${r.total_cost_usd:.6f} passed={r.passed}")
    console.print("[bold green]Check passed[/bold green]")


@app.command(name="api-check")
def api_check(
    config: Path = typer.Option(project_root() / "config.yaml", help="Path to config.yaml"),
):
    """Tiny real OpenRouter call: verifies key, credits, token usage, USD/RUB accounting."""
    from .llm import make_client

    cfg = load_config(config)
    llm = make_client(cfg, dry_run=False)
    try:
        try:
            result = llm.chat(
                [{"role": "user", "content": "Reply with exactly: OK"}],
                model=cfg.small_model,
                role="api_check",
                architecture="api_check",
                max_tokens=8,
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            body = exc.response.text[:300] if exc.response is not None else str(exc)
            console.print(f"[bold red]OpenRouter API check failed[/bold red]: HTTP {status}")
            console.print(body)
            raise typer.Exit(1) from exc
        console.print("[bold green]OpenRouter API check passed[/bold green]")
        console.print(
            f"model={result.usage.model} "
            f"input={result.usage.input_tokens} "
            f"output={result.usage.output_tokens} "
            f"cost=${result.usage.cost_usd:.8f} "
            f"cost_rub=₽{result.usage.cost_rub:.4f}"
        )
    finally:
        llm.close()


@app.command()
def e1(
    n: int = typer.Option(20, help="Number of HumanEval tasks (article default 164)"),
    seeds: str = typer.Option("42,123", help="Comma-separated seeds"),
    suite: str = typer.Option("humaneval", help="humaneval | controlled | both"),
    config: Path = typer.Option(project_root() / "config.yaml"),
    output: Path = typer.Option(project_root() / "results" / "e1"),
    dry_run: bool = typer.Option(False, help="Use DryRunClient (no API spending)"),
):
    """E1 — Pilot on HumanEval (verifies H1, §7.2)."""
    from .experiments.e1_humaneval_pilot import run as _run
    _run(load_config(config), n=n, seeds=_parse_seeds(seeds), out_dir=output, dry_run=dry_run, suite=suite)


@app.command()
def e2(
    n: int = typer.Option(20),
    seeds: str = typer.Option("42,123"),
    config: Path = typer.Option(project_root() / "config.yaml"),
    output: Path = typer.Option(project_root() / "results" / "e2"),
    dry_run: bool = typer.Option(False),
):
    """E2 — Ablation analysis + adversarial scenarios (E2a-d, §7.3)."""
    from .experiments.e2_ablation import run as _run
    _run(load_config(config), n=n, seeds=_parse_seeds(seeds), out_dir=output, dry_run=dry_run)


@app.command()
def e3(
    n: int = typer.Option(20),
    seeds: str = typer.Option("42,123"),
    config: Path = typer.Option(project_root() / "config.yaml"),
    output: Path = typer.Option(project_root() / "results" / "e3"),
    dry_run: bool = typer.Option(False),
):
    """E3 — Scaling on context length, estimates τ⋆ (§7.4)."""
    from .experiments.e3_context_scaling import run as _run
    _run(load_config(config), n=n, seeds=_parse_seeds(seeds), out_dir=output, dry_run=dry_run)


@app.command()
def e4(
    n: int = typer.Option(20),
    seeds: str = typer.Option("42,123"),
    config: Path = typer.Option(project_root() / "config.yaml"),
    output: Path = typer.Option(project_root() / "results" / "e4"),
    dry_run: bool = typer.Option(False),
):
    """E4 — Small-model self-check evaluation (verifies H2, §7.5)."""
    from .experiments.e4_self_check import run as _run
    _run(load_config(config), n=n, seeds=_parse_seeds(seeds), out_dir=output, dry_run=dry_run)


@app.command()
def e5(
    n: int = typer.Option(40, help="Tasks for TCO measurement (article: 500)"),
    seeds: str = typer.Option("42,123"),
    config: Path = typer.Option(project_root() / "config.yaml"),
    output: Path = typer.Option(project_root() / "results" / "e5"),
    dry_run: bool = typer.Option(False),
):
    """E5 — TCO on real measurements (§7.6)."""
    from .experiments.e5_tco import run as _run
    _run(load_config(config), n=n, seeds=_parse_seeds(seeds), out_dir=output, dry_run=dry_run)


@app.command()
def e6(
    n: int = typer.Option(20),
    seeds: str = typer.Option("42,123"),
    suite: str = typer.Option("controlled", help="humaneval | controlled | both"),
    config: Path = typer.Option(project_root() / "config.yaml"),
    output: Path = typer.Option(project_root() / "results" / "e6"),
    dry_run: bool = typer.Option(False),
):
    """E6 — Gemini Pro vs Flash-Lite inside B2 and B3."""
    from .experiments.e6_model_sweep import run as _run
    _run(load_config(config), n=n, seeds=_parse_seeds(seeds), out_dir=output, dry_run=dry_run, suite=suite)


@app.command(name="all")
def run_all(
    n: int = typer.Option(20),
    seeds: str = typer.Option("42,123"),
    config: Path = typer.Option(project_root() / "config.yaml"),
    output: Path = typer.Option(project_root() / "results"),
    dry_run: bool = typer.Option(False),
):
    """Run E1..E5 sequentially with a shared n/seeds budget."""
    cfg = load_config(config)
    seeds_list = _parse_seeds(seeds)
    from .experiments import (
        e1_humaneval_pilot,
        e2_ablation,
        e3_context_scaling,
        e4_self_check,
        e5_tco,
    )
    e1_humaneval_pilot.run(cfg, n=n, seeds=seeds_list, out_dir=output / "e1", dry_run=dry_run)
    e2_ablation.run(cfg, n=n, seeds=seeds_list, out_dir=output / "e2", dry_run=dry_run)
    e3_context_scaling.run(cfg, n=n, seeds=seeds_list, out_dir=output / "e3", dry_run=dry_run)
    e4_self_check.run(cfg, n=n, seeds=seeds_list, out_dir=output / "e4", dry_run=dry_run)
    e5_tco.run(cfg, n=n, seeds=seeds_list, out_dir=output / "e5", dry_run=dry_run)


@app.command()
def view(
    experiment: str = typer.Argument(..., help="One of: e1 e2 e3 e4 e5"),
    results_dir: Path = typer.Option(project_root() / "results"),
):
    """Pretty-print results of a previously run experiment."""
    from .doc_viewer import render_experiment
    render_experiment(experiment.lower(), results_dir=results_dir)


# ---------------------------------------------------------------------------
def _parse_seeds(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main():  # console_scripts entrypoint
    app()


if __name__ == "__main__":
    main()
