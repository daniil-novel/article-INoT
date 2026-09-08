"""Continue only never-started cells from the partial held-out INoT archive."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import threading
import time
from typing import Any, Callable

from .. import codex_subscription as c
from ..record_codex_runtime import capture
from . import inot, inot_audit

TIMEOUT = 180
DEPENDENCIES = ("codex_subscription.py", "factorial_runner.py", "record_codex_runtime.py", "audit_codex_pilot.py", "benchmark_bridge.py", "heldout200/inot.py", "heldout200/inot_audit.py", "heldout200/inot_continue.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def freeze(parent: Path, tasks: Path, protocol: Path, selection: Path, gate: Path, source_root: Path, out: Path) -> dict[str, Any]:
    if out.exists(): raise ValueError("refuse to overwrite continuation manifest")
    # Audit first because audit() intentionally refreshes audit_inventory.json.
    audited = inot_audit.audit(parent, tasks, selection, gate, protocol)
    status = c.read(parent / "status.json")
    if status.get("state") not in {"blocked", "completed"} or audited.get("status") not in {"partial", "complete"}:
        raise ValueError("original INoT archive is not terminal and audited")
    original_manifest = c.read(parent / "manifest.json")
    pending = [cell for cell in original_manifest["cells"] if not (parent / "turns" / cell["id"]).exists()]
    files = {"parent_tree": tree(parent), "tasks": sha(tasks), "protocol": sha(protocol), "selection": sha(selection), "gate": sha(gate)}
    amendment = source_root / 'revision/INOT_EXECUTION_AMENDMENT.md'
    files['amendment'] = sha(amendment)
    deps = {name: sha(source_root / name) for name in DEPENDENCIES}
    body = {"schema": "codex-inot-heldout200-continuation-v1", "original_archive_tree": files["parent_tree"], "original_manifest_sha256": sha(parent / "manifest.json"), "original_manifest": original_manifest, "original_status": status, "audit_summary": audited, "input_hashes": {k: v for k, v in files.items() if k != "parent_tree"}, "dependency_sha256": deps, "pending_cells": pending, "pending_count": len(pending), "workers": 2, "timeout_seconds": TIMEOUT, "no_retry": True, "treatment": inot.TREATMENT, "replicate_id": inot.REPLICATE_ID}
    result = {**body, "manifest_sha256": c.digest(body)}; c.save(out, result); return result


def validate(manifest: dict[str, Any], parent: Path, tasks: Path, protocol: Path, selection: Path, gate: Path, source_root: Path) -> None:
    if c.digest({k: v for k, v in manifest.items() if k != "manifest_sha256"}) != manifest["manifest_sha256"]: raise ValueError("continuation manifest changed")
    if tree(parent) != manifest["original_archive_tree"]: raise ValueError("original INoT archive changed")
    for path, expected in {tasks: manifest["input_hashes"]["tasks"], protocol: manifest["input_hashes"]["protocol"], selection: manifest["input_hashes"]["selection"], gate: manifest["input_hashes"]["gate"]}.items():
        if sha(path) != expected: raise ValueError("continuation input changed")
    if sha(source_root / 'revision/INOT_EXECUTION_AMENDMENT.md') != manifest['input_hashes']['amendment']:
        raise ValueError('Continuation amendment changed')
    for name, expected in manifest["dependency_sha256"].items():
        if sha(source_root / name) != expected: raise ValueError("continuation dependency changed: " + name)
    pending = [cell for cell in manifest["original_manifest"]["cells"] if not (parent / "turns" / cell["id"]).exists()]
    if pending != manifest["pending_cells"]: raise ValueError("pending INoT cells changed")


def known_nonfatal(reason: str, folder: Path) -> bool:
    text = reason.lower()
    if "timeout" in text: return True
    evidence = "".join((folder / n).read_text(encoding="utf-8", errors="replace").lower() for n in ("stderr.txt", "events.jsonl") if (folder / n).exists())
    if any(x in evidence for x in ('quota', 'usage limit', 'rate limit', 'unauthorized', 'authentication', '401', '403')): return False
    return any(x in evidence for x in ("stream disconnected before completion", "transport error: network error", "error decoding response body"))


def run_cells(cells: list[dict[str, Any]], tasks: list[dict[str, Any]], archive: Path, prefix: list[str], instructions: Path, transport: Callable[..., dict[str, Any]] = c.archive_turn) -> dict[str, Any]:
    by_id = {t["task_id"]: t for t in tasks}; failures=[]; rows=[]; lock=threading.Lock(); stop=threading.Event()
    command = c.cli_command(prefix, (archive / "empty").resolve(), instructions.resolve())
    def one(cell):
        if stop.is_set():
            return
        try:
            with lock:
                with (archive/'submission_order.jsonl').open('a',encoding='utf-8') as log:
                    log.write(json.dumps({'cell':cell['id'],'started_unix':time.time()})+'\n')
            result=transport(archive / "turns" / cell["id"], command, inot.prompt_for(by_id[cell["task_id"]]), TIMEOUT)
            row={**cell,"model":c.MODEL,"treatment":inot.TREATMENT,"seed":inot.REPLICATE_ID,"seed_field_semantics":"replicate label only; CLI sampling seed not set","final_text":result["final_text"],"usage":result["usage"],"total_tokens":result["usage"]["input_tokens"]+result["usage"]["output_tokens"],"api_equivalent_usd":result["api_equivalent_usd"],"uncached_sensitivity_usd":result["uncached_sensitivity_usd"],"wall_seconds":result["wall_seconds"],"actual_api_charge_usd":None}
            c.save(archive / "cells" / f"{cell['id']}.json", row); rows.append(row)
        except Exception as exc:
            reason=str(exc); failures.append({"cell":cell["id"],"reason":reason})
            if not known_nonfatal(reason, archive / "turns" / cell["id"]): stop.set()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(one, cells))
    rows.sort(key=lambda x:x["id"]); (archive / "results.jsonl").write_bytes(b"".join(c.canonical(x)+b"\n" for x in rows))
    return {"attempted":len(rows)+len(failures),"completed":len(rows),"failures":failures,"allocation_exhausted":len(rows)+len(failures)==len(cells) and not stop.is_set()}


def run(parent: Path, tasks: Path, protocol: Path, selection: Path, gate: Path, source_root: Path, manifest_path: Path, archive: Path, npm_root: Path) -> dict[str, Any]:
    parent,tasks,protocol,selection,gate,source_root,manifest_path,archive,npm_root=[p.resolve() for p in (parent,tasks,protocol,selection,gate,source_root,manifest_path,archive,npm_root)]
    manifest=c.read(manifest_path); validate(manifest,parent,tasks,protocol,selection,gate,source_root)
    if archive.exists(): raise ValueError("refuse to overwrite continuation archive")
    archive.mkdir(parents=True); (archive/"turns").mkdir(); (archive/"cells").mkdir(); (archive/"empty").mkdir()
    for name in ("manifest.json","tasks.json","protocol.md","selection.json","control-gate.json","inot_source.py","factorial_runner.py","record_codex_runtime.py","audit_codex_pilot.py","runner_source.py","runtime.json","runtime_provenance.json","npm-package.json","npm-package-lock.json","cli-package.json"):
        src=parent/name
        if src.exists():
            shutil.copyfile(src, archive/("original_"+name))
            if name not in {"runtime.json", "runtime_provenance.json", "npm-package.json", "npm-package-lock.json", "cli-package.json"}:
                shutil.copyfile(src, archive/name)
    c.save(archive/"continuation_manifest.json",manifest)
    (archive/'continuation_protocol.md').write_bytes((source_root/'revision/INOT_EXECUTION_AMENDMENT.md').read_bytes())
    (archive/'continuation_sources').mkdir()
    for name in DEPENDENCIES:
        (archive/'continuation_sources'/name.replace('/','__')).write_bytes((source_root/name).read_bytes())
    node=shutil.which("node"); entry=npm_root.resolve()/"node_modules/@openai/codex/bin/codex.js"
    if not node or not entry.is_file(): raise ValueError("explicit npm Codex entry missing")
    prefix=[node,str(entry)]; version=subprocess.check_output(prefix+["--version"],text=True).strip()
    if version!=c.CLI_VERSION: raise ValueError("CLI version mismatch")
    auth=subprocess.run(prefix+["login","status"],capture_output=True,text=True)
    if auth.returncode or "ChatGPT" not in auth.stdout+auth.stderr: raise ValueError("ChatGPT subscription login required")
    instructions=archive/"instructions.txt"; instructions.write_bytes(c.BASE.encode()); c.save(archive/"runtime.json",{"version":version,"prefix":prefix,"authentication":"chatgpt","workers":2,"timeout_seconds":TIMEOUT,"started_unix":time.time()}); capture(archive,npm_root,Path(c.__file__))
    c.save(archive/'status.json',{'state':'started','assigned_generations':200,'continuation_assigned':manifest['pending_count']})
    c.save(archive/"continuation_status.json",{"state":"started","assigned_cells":manifest["pending_count"],"started_unix":time.time()})
    tasks_rows=[json.loads(x) for x in tasks.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    result=run_cells(manifest["pending_cells"],tasks_rows,archive,prefix,instructions)
    result["state"]="allocation_exhausted" if result["allocation_exhausted"] else "blocked"; c.save(archive/"continuation_status.json",result)
    c.save(archive/"status.json", {"state":"blocked", "continuation_state":result["state"], "assigned_generations":200, "continuation_assigned":manifest["pending_count"], "completed_generations":result["completed"], "failures":result["failures"]})
    audit=inot_audit.audit(archive,tasks,selection,gate,protocol); c.save(archive/"continuation_audit.json",audit); return result


def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest="command",required=True)
    f=s.add_parser("freeze")
    for n in ("parent","tasks","protocol","selection","gate","source-root","out"):f.add_argument("--"+n,type=Path,required=True)
    r=s.add_parser("run")
    for n in ("parent","tasks","protocol","selection","gate","source-root","manifest","archive"):r.add_argument("--"+n,type=Path,required=True)
    r.add_argument("--npm-root",type=Path,default=Path("tmp/codex-runtime"));a=p.parse_args()
    if a.command=="freeze":freeze(a.parent,a.tasks,a.protocol,a.selection,a.gate,a.source_root,a.out);return
    print(json.dumps(run(a.parent,a.tasks,a.protocol,a.selection,a.gate,a.source_root,a.manifest,a.archive,a.npm_root)))
if __name__=="__main__":main()
