"""Freeze newly terminal attempt bytes before a further administrative resume.

This does not change the scientific prefix or analysis selection. The original
adapter intentionally accepts only the exact byte inventory of its launch;
after a stopped session, this tool adds the newly submitted attempts to that
inventory. The original eight pre-recovery entries stay unchanged so that the
original strict recovery verifier can still check their historical copies.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import time

from reproducibility.scc2000 import continuation as c


def extend_inventory(selection: dict, current: dict) -> dict:
    old=selection["old_inventory"]
    if c.canonical_digest(old["assignments"]) != old["snapshot_sha256"]:
        raise ValueError("Original inventory digest changed")
    previous={r["id"]:r for r in old["assignments"]}
    latest={r["id"]:r for r in current["assignments"]}
    if len(latest)!=len(current["assignments"]) or not set(previous)<=set(latest):
        raise ValueError("Missing or duplicate previous assignments")
    if not set(latest)<=set(selection["selected_ids"]):
        raise ValueError("Touched cells outside the fixed prefix")
    # Old rows must keep their original hashes, including eight pre-recovery
    # statuses. validate_recovery then checks actual bytes against those rows.
    rows=[copy.deepcopy(previous.get(i,latest[i])) for i in sorted(latest)]
    result=copy.deepcopy(selection)
    result["old_inventory"]={"assignment_count":len(rows),"assignments":rows,
                              "snapshot_sha256":c.canonical_digest(rows)}
    return result


def prepare(original: Path, root: Path, recovery: Path, amendment: Path, out: Path) -> dict:
    if out.exists(): raise FileExistsError("Resume snapshot already exists")
    selection=c.load_selection(original,amendment=amendment)
    c.assert_recovery_idle(root/"DISPATCH.lock",c.process_inventory(Path("C:/Python311/python.exe")))
    if (root/"DISPATCH.lock").exists(): raise ValueError("Dispatch lock must be absent")
    selected=set(selection["selected_ids"])
    current=c._inventory(root,selected,{r["id"]:r for r in selection["selected_cells"]})
    terminal={"completed","infrastructure_failure","model_or_workflow_failure","paused"}
    for row in current["assignments"]:
        if c._read(root/"assignments"/row["id"]/"status.json").get("state") not in terminal:
            raise ValueError("A submitted assignment is not terminal")
    result=extend_inventory(selection,current)
    verified=c.validate_recovery(result,recovery)
    scientific={k:v for k,v in selection.items() if k!="old_inventory"}
    if {k:v for k,v in result.items() if k!="old_inventory"} != scientific:
        raise ValueError("Scientific selection or bound sources changed")
    result["administrative_resume"]={"created_unix":time.time(),"source_selection_sha256":c.sha(original),
        "scientific_analysis_selection":"freeze-v3/selection_manifest.json",
        "newly_terminal_attempts":len(current["assignments"])-selection["old_inventory"]["assignment_count"],
        "untouched_selected":6000-len(current["assignments"]),
        "preparation_source_sha256":c.normalized_sha(Path(__file__)),"recovery_verified":verified}
    out.mkdir(parents=True)
    c.cli.save(out/"selection_manifest.json",result)
    c.cli.save(out/"current_inventory.json",current)
    return result["administrative_resume"]


def main():
    p=argparse.ArgumentParser()
    for name in ("original","root","recovery","amendment","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.original,a.root,a.recovery,a.amendment,a.out)))


if __name__=="__main__":main()
