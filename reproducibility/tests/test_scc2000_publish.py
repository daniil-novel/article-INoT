"""Publication contracts, with synthetic outcomes and real frozen metadata."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from reproducibility.scc2000 import publish, analyze
from reproducibility.tests.test_scc2000_contract import _rows, FREEZE, ROOT


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_small_status_gate_rejects_live_lock_and_touched_unselected(tmp_path, monkeypatch):
    manifest=tmp_path/"manifest.json"; save(manifest,{})
    selected={"selected_ids":["a","b"],"all_ids":["a","b","c"],
              "original_manifest_sha256":publish.continuation.sha(manifest)}
    monkeypatch.setattr(publish.continuation,"load_selection",lambda *a,**kw:selected)
    monkeypatch.setattr(publish.finish,"_verify_prefix",lambda *a:None)
    gen=tmp_path/"generation"
    for ident in ("a","b"): save(gen/"assignments"/ident/"status.json",{"state":"completed"})
    save(gen/"status.json",{"state":"paused"})
    save(gen/"continuation_status.json",publish.continuation.continuation_status(root=gen,selected_ids=["a","b"]))
    args=(tmp_path,tmp_path/"selection",tmp_path,manifest,tmp_path,tmp_path/"amendment")
    assert publish._gate(*args)==selected
    (gen/"DISPATCH.lock").write_text("active")
    with pytest.raises(ValueError,match="active dispatcher"): publish._gate(*args)
    (gen/"DISPATCH.lock").unlink()
    save(gen/"assignments/c/status.json",{"state":"completed"})
    with pytest.raises(ValueError,match="unselected"): publish._gate(*args)


def test_view_checks_values_not_only_ids(tmp_path):
    rows=[{"id":str(i),"task_id":str(i),"method":"m","replicate_id":1,"quality":False} for i in range(9000)]
    def write(name,values): (tmp_path/name).write_text("\n".join(json.dumps(r) for r in values)+"\n",encoding="utf-8")
    write("candidate_records.jsonl",rows)
    write("selected_assignment_records.jsonl",rows[:6000])
    selection={"selected_ids":[str(i) for i in range(6000)]}
    publish._selected_view(tmp_path,selection)
    rows[0]["quality"]=True
    write("selected_assignment_records.jsonl",rows[:6000])
    with pytest.raises(ValueError,match="Selected view differs"): publish._selected_view(tmp_path,selection)


def test_count_only_fake_archive_cannot_pass(tmp_path):
    (tmp_path/"README.md").write_text("fake")
    with pytest.raises(FileNotFoundError): publish.verify_archive(tmp_path)


def test_amended_replay_detects_changed_draw_and_summary(tmp_path):
    rows,*_= _rows()
    records=tmp_path/"candidate_records.jsonl"
    records.write_text("\n".join(json.dumps(r) for r in rows)+"\n",encoding="utf-8")
    gate=tmp_path/"controls"; gate.mkdir()
    (gate/"heldout200_control_gate.json").write_bytes((FREEZE/"control_gate.json").read_bytes())
    source=ROOT/"reproducibility/task_dependence/source-audit-v2"
    selection=FREEZE/"selection_manifest.json"
    out=tmp_path/"amended-analysis"
    analyze.run_files(records,selection,gate/"heldout200_control_gate.json",source,out)
    publish._recompute_amended(tmp_path,selection,gate,source)
    target=next((out/"draws").rglob("*.npy")); original=target.read_bytes()
    vector=np.load(target,allow_pickle=False); vector[0]+=0.25
    np.save(target,vector,allow_pickle=False)
    with pytest.raises(ValueError,match="Recomputed evidence"): publish._recompute_amended(tmp_path,selection,gate,source)
    target.write_bytes(original)
    summary=json.loads((out/"summary.json").read_text()); summary["task_count"]-=1
    save(out/"summary.json",summary)
    with pytest.raises(ValueError,match="Amended statistics"): publish._recompute_amended(tmp_path,selection,gate,source)


def test_source_tree_comparison_rejects_added_and_missing_files(tmp_path):
    a=tmp_path/"a";b=tmp_path/"b";a.mkdir();b.mkdir()
    (a/"x").write_text("data");(b/"x").write_text("data")
    publish._same_tree(a,b)
    (a/"extra").write_text("data")
    with pytest.raises(ValueError): publish._same_tree(a,b)


def test_moved_source_closure_checks_actual_freeze_and_rejects_source_drift(tmp_path):
    """No SCC outcomes: copy only frozen sources, tasks, controls and selection."""
    archive=tmp_path/"moved"; archive.mkdir()
    frozen=json.loads((FREEZE/"original_manifest.json").read_text(encoding="utf-8"))
    files=set(frozen["source_files_sha256"])|set(publish.SOURCE_FILES)|{
        "reproducibility/results/20260911_scc_comparison_dev9/summary.json",
        "reproducibility/task_dependence/package.py",
        "reproducibility/task_dependence/sensitivity.py",
        *{f"reproducibility/scc2000/{n}.py" for n in ("publish","analyze","finish","continuation")}}
    for rel in files:
        target=archive/"sources"/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/rel,target)
    shutil.copytree(ROOT/"reproducibility/scale1000/inputs-v1",archive/"inputs")
    shutil.copytree(ROOT/"reproducibility/results/20260908_scale1000_preflight/controls-v3",archive/"controls")
    for src,rel in ((FREEZE/"control_gate.json","controls/heldout200_control_gate.json"),
                    (FREEZE/"original_manifest.json","generation/manifest.json"),
                    (FREEZE/"selection_manifest.json","amendment/selection_manifest.json"),
                    (ROOT/"reproducibility/scc2000/AMENDMENT.md","amendment/AMENDMENT.md"),
                    (Path(publish.__file__),"provenance/publish_scc.py")):
        target=archive/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
    probe=archive/"probe.py"
    probe.write_text('''import runpy
from pathlib import Path
root=Path(__file__).resolve().parent
m=runpy.run_path(str(root/'provenance/publish_scc.py'))
with m['_archive_source_context'](root):
    s=m['continuation'].load_selection(root/'amendment/selection_manifest.json', amendment=root/'amendment/AMENDMENT.md')
    m['finish']._verify_prefix(s,root/'inputs',root/'generation/manifest.json',root/'controls')
print('frozen_source_closure_passed')
''',encoding="utf-8")
    def execute(): return subprocess.run([sys.executable,"-I",str(probe)],cwd=tmp_path,capture_output=True,text=True)
    result=execute();assert result.returncode==0,result.stderr
    target=archive/"sources/reproducibility/tests/test_scc_native_pipeline.py"
    original=target.read_bytes();target.write_bytes(original+b"\n# source drift\n")
    result=execute();assert result.returncode!=0 and "manifest differs" in result.stderr
    target.write_bytes(original)
    path=archive/"amendment/selection_manifest.json";value=json.loads(path.read_text(encoding="utf-8"))
    value["selected_cells"][0]["task_id"]="tampered";save(path,value)
    result=execute();assert result.returncode!=0 and "Selection cells or order changed" in result.stderr

def test_actual_source_graph_rebuild_includes_exact_evidence_manifest():
    archive = ROOT / 'reproducibility/results/20260913_scc2000_luna_full'
    if not archive.is_dir():
        pytest.skip('actual completed SCC archive is required for this regression')
    publish._recompute_source_graph(archive)
