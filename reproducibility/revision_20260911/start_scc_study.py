"""Run the frozen SCC comparison after the factorial generation has ended."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from reproducibility import codex_luna_subscription as cli
from reproducibility.scale1000_luna.collect import raw_usage
from reproducibility.revision_20260911 import scc_controls, scc_dispatch

ROOT = Path(__file__).resolve().parents[2]


def prior_ledger(primary: Path, development: Path) -> dict:
    if cli.read(primary / "status.json")["state"] != "generation_finished" or (primary / "DISPATCH.lock").exists():
        raise ValueError("Factorial generation must be terminal before starting SCC")
    turns = []
    for folder in sorted((primary / "turns").iterdir()):
        if not folder.is_dir(): continue
        usage = raw_usage(folder)
        turns.append({"turn": folder.name, "events_sha256": scc_dispatch.sha(folder / "events.jsonl"),
                      "usage": usage, "known_api_equivalent_usd": cli.value_usage(usage) if usage is not None else None})
    dev = cli.read(development / "summary.json")
    if dev.get("gate") != "passed" or dev.get("assigned") != 9 or dev.get("native_checked") != 9:
        raise ValueError("The nine-candidate development gate has not passed")
    return {"schema": "scc-prior-known-valuation-v1", "primary_turns": turns,
            "primary_manifest_sha256": scc_dispatch.sha(primary / "manifest.json"),
            "development_summary_sha256": scc_dispatch.sha(development / "summary.json"),
            "unknown_primary_turns": sum(t["usage"] is None for t in turns),
            "known_api_equivalent_usd": sum(t["known_api_equivalent_usd"] or 0 for t in turns) + dev["known_api_equivalent_usd"],
            "interpretation": "Known subtotal of the new Luna studies, not an invoice; unknown usage remains unknown."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("reproducibility/runs/scc1000-luna-v1"))
    args = parser.parse_args()
    root = args.root.resolve()
    inputs = ROOT / "reproducibility/scale1000/inputs-v1"
    gate = ROOT / "reproducibility/runs/scale1000-v1/controls-v3"
    manifest = ROOT / "reproducibility/revision_20260911/scc_manifest.json"
    primary = ROOT / "reproducibility/runs/scale1000-luna-v1/generation"
    development = ROOT / "reproducibility/results/20260911_scc_comparison_dev9"
    if cli.read(manifest) != scc_controls.plan(inputs, gate):
        raise ValueError("SCC launch manifest differs from the frozen sources")
    budget = prior_ledger(primary, development)
    root.mkdir(parents=True, exist_ok=True)
    budget_path = root / "prior_studies_valuation.json"
    if budget_path.exists() and cli.read(budget_path) != budget:
        raise ValueError("Prior-study evidence changed on resume")
    if not budget_path.exists(): cli.save(budget_path, budget)
    session = root / "launcher" / str(time.time_ns())
    session.mkdir(parents=True)
    commands = {
        "generate": [sys.executable, "-X", "utf8", "-m", "reproducibility.revision_20260911.scc_dispatch",
                     "--inputs", str(inputs), "--gate-dir", str(gate), "--manifest", str(manifest),
                     "--out", str(root / "generation"), "--npm-root", str(ROOT / "tmp/codex-runtime"), "--workers", "8",
                     "--prior-known-valuation", str(budget["known_api_equivalent_usd"]), "--prior-valuation-file", str(budget_path)],
        "finish": [sys.executable, "-X", "utf8", "-m", "reproducibility.revision_20260911.scc_finish",
                   "--root", str(root), "--inputs", str(inputs), "--gate-dir", str(gate), "--manifest", str(manifest)]}
    cli.save(session / "commands.json", commands)
    for name, argv in commands.items():
        if name == "finish" and cli.read(root / "generation/status.json")["state"] != "generation_finished":
            print(json.dumps({"state": "paused", "next_stage": "finish"}), flush=True)
            return
        with (session / (name + ".stdout.log")).open("xb") as stdout, (session / (name + ".stderr.log")).open("xb") as stderr:
            process = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr)
        cli.save(session / (name + ".exit.json"), {"returncode": process.returncode, "finished_unix": time.time()})
        print(json.dumps({"stage": name, "returncode": process.returncode}), flush=True)
        if process.returncode: raise SystemExit(process.returncode)


if __name__ == "__main__": main()
