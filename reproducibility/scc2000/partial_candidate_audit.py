"""Inventory SCC developer programs retained before Docker infrastructure failure."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def sha(data: bytes | Path) -> str:
    if isinstance(data, Path):
        data = data.read_bytes()
    return hashlib.sha256(data).hexdigest()

def jload(p: Path):
    # Parse the JSON object; never echo the multi-megabyte inventory line.
    return json.loads(p.read_text(encoding="utf-8"))


def immutable_bytes(path: Path, data: bytes) -> None:
    """Write an artifact once, and reject any attempted replacement."""
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"immutable diagnostic artifact differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def immutable_text(path: Path, value: str) -> None:
    immutable_bytes(path, value.encode("utf-8"))

def audit(root: Path, manifest: Path, output: Path, inventory: Path,
          expected_failures: int = 396) -> dict:
    m = jload(manifest)
    selected = {str(x["id"]): x for x in m["selected_cells"]}
    inv = jload(inventory)
    inventory_rows = {str(x["id"]): x for x in inv["assignments"]}
    failures = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        sp, cp = d / "status.json", d / "cell.json"
        if not sp.exists() or not cp.exists():
            continue
        status, cell = jload(sp), jload(cp)
        is_failure = (cell.get("method") == "scc_author_2024_codex_transport"
                      and status.get("state") == "infrastructure_failure"
                      and "container" in str(status.get("reason", "")).lower())
        if is_failure:
            if cell["id"] not in selected:
                raise ValueError(f"failed SCC cell outside frozen selection: {cell['id']}")
            failures.append((d, status, cell))
    if len(failures) != expected_failures:
        raise ValueError(f"expected {expected_failures} selected SCC container failures, found {len(failures)}")
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for d, status, cell in failures:
        if d.name != cell['id']:
            raise ValueError('assignment directory differs from cell identity')
        if cell != selected[cell["id"]]:
            raise ValueError(f"allocation identity differs from selection: {cell['id']}")
        ir = inventory_rows.get(cell["id"])
        if ir is None:
            raise ValueError(f"failed SCC cell absent from frozen inventory: {cell['id']}")
        if ir.get("status_sha256") != sha(d / "status.json"):
            raise ValueError(f"status hash differs from frozen inventory: {cell['id']}")
        for rel, expected in ir.get("files_sha256", {}).items():
            actual = d / rel
            if not actual.is_file() or sha(actual) != expected:
                raise ValueError(f"frozen source hash differs: {cell['id']}/{rel}")
        inputs = sorted((d / "generated_tests").glob("*/input.json"), key=lambda p: p.parent.name)
        if not inputs:
            raise ValueError(f"missing generated-test input: {cell['id']}")
        inp = inputs[-1]
        if inp.relative_to(d).as_posix() not in ir.get('files_sha256', {}):
            raise ValueError('selected developer input is outside the frozen inventory')
        raw = inp.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        if set(payload) != {"code", "report"} or not all(isinstance(payload[k], str) for k in ("code", "report")):
            raise ValueError(f"invalid generated-test input schema: {inp}")
        code = payload["code"].encode("utf-8")
        out = output / d.name
        out.mkdir(exist_ok=True)
        immutable_bytes(out / "developer_program.py", code)
        immutable_text(out / "generated_test_report.txt", payload["report"])
        records.append({"assignment_id": cell["id"], "task_id": cell["task_id"], "method": cell["method"],
                        "replicate_id": cell["replicate_id"], "terminal_state": status["state"],
                        "terminal_reason": status.get("reason"), "generated_test_input": str(inp),
                        "generated_test_input_sha256": sha(raw), "developer_program_sha256": sha(code),
                        "developer_program_bytes": len(code), "native_outcome": "unassigned"})
    summary = {"schema": "scc-partial-candidate-audit-v2", "source_root": str(root),
               "selection_manifest": str(manifest), "failed_assignments_scanned": len(records),
               "recoverable_developer_programs": len(records), "native_outcomes_assigned": False, "records": records}
    immutable_text(output / "audit.json", json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--expected-failures", type=int, default=396)
    a = p.parse_args()
    print(json.dumps(audit(a.root.resolve(), a.manifest.resolve(), a.output.resolve(),
                          a.inventory.resolve(), a.expected_failures), ensure_ascii=False))

if __name__ == "__main__":
    main()
