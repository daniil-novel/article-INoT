"""Terminal renderer for experiment results.

For each experiment we display:
  - a short scientific brief loaded from ``docs/<experiment>.md``
  - the per-architecture summary table
  - the verdict / key numbers (e.g. H1 confirmed?)
  - paths to generated PNG figures so the user can open them.
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .config import project_root

console = Console()

_DOCS = project_root() / "docs"


def render_experiment(name: str, results_dir: Path) -> None:
    """``inot view e1``-equivalent: render whatever artefacts exist."""
    exp_dir = results_dir / name
    if not exp_dir.exists():
        console.print(f"[red]No results found at {exp_dir}. Run `python -m inot {name}` first.[/red]")
        return

    # 1) doc card
    md_file = _DOCS / f"{name}.md"
    if md_file.exists():
        console.print(Panel(Markdown(md_file.read_text(encoding="utf-8")),
                            title=f"docs/{name}.md", border_style="cyan"))
    else:
        console.print(f"[yellow]No docs/{name}.md found; skipping description.[/yellow]")

    # 2) verdict (if any)
    for verdict_file in ("H1_VERDICT.md", "H2_VERDICT.md", "E6_VERDICT.md"):
        v = exp_dir / verdict_file
        if v.exists():
            console.print(Panel(Markdown(v.read_text(encoding="utf-8")),
                                title=verdict_file, border_style="green"))

    # 3) summary table snapshot (text)
    txt = exp_dir / "table.txt"
    if txt.exists():
        console.print(Panel(txt.read_text(encoding="utf-8"),
                            title="Summary table", border_style="magenta"))

    # 4) numeric headlines from summary.json / tau_star.json / tco_summary.json
    for jname in ("summary.json", "tau_star.json", "tco_summary.json"):
        f = exp_dir / jname
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            console.print(Panel(_pretty_json_excerpt(data),
                                title=jname, border_style="blue"))

    # 5) figure list
    figs = sorted(exp_dir.rglob("*.png"))
    if figs:
        t = Table(title="Generated figures", header_style="bold")
        t.add_column("Path")
        for p in figs:
            t.add_row(str(p))
        console.print(t)


def _pretty_json_excerpt(obj, max_lines: int = 30) -> str:
    s = json.dumps(obj, indent=2, default=str, ensure_ascii=False)
    lines = s.splitlines()
    if len(lines) <= max_lines:
        return s
    head = "\n".join(lines[: max_lines - 2])
    return head + f"\n... [{len(lines) - max_lines + 2} more lines truncated]"
