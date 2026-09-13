import json
from pathlib import Path
import pytest
from reproducibility.scc2000 import finish, parallel_finish


def fixture(tmp_path, monkeypatch):
    root=tmp_path.resolve()
    (root/'generation').mkdir()
    (root/'generation/status.json').write_text(json.dumps({'state':'paused'}))
    ids=[str(i) for i in range(6000)]
    manifest={'methods':['sr','sn','scc'],'replicate_ids':[101,102,103]}
    (root/'selection.json').write_text(json.dumps({'selected_ids':ids}))
    (root/'manifest.json').write_text(json.dumps(manifest))
    (root/'heldout200_control_gate.json').write_text(json.dumps({'image_id':'fixed','evaluable_task_ids':[]}))
    (root/'predictions').mkdir()
    for method in manifest['methods']:
        for rep in manifest['replicate_ids']:
            (root/'predictions'/f'{method}-r{rep}.jsonl').write_text(json.dumps({'task_id':'task','solution':'complete exact program'})+'\n')
    monkeypatch.setattr(finish,'_terminal_selected',lambda *a:None)
    monkeypatch.setattr(finish,'_verify_prefix',lambda *a:None)
    monkeypatch.setattr(finish.scc_export,'validate_export',lambda *a:{'rows':9000})
    monkeypatch.setattr(finish,'environment_from_gate',lambda *a:{'image_id':'fixed'})
    monkeypatch.setattr(finish.scc_finish,'_image_id',lambda *a:'fixed')
    args=dict(root=root,inputs=root,gate_dir=root,manifest=root/'manifest.json',selection_manifest=root/'selection.json')
    return root,manifest,args


def test_parallel_commands_equal_unchanged_sequential_finisher(tmp_path,monkeypatch):
    root,manifest,args=fixture(tmp_path,monkeypatch)
    seen=[]
    monkeypatch.setattr(finish.scc_finish,'_run_native_stage',lambda *a:seen.append(a))
    monkeypatch.setattr(finish,'validate_native',lambda *a:{'ok':True,'statuses':{}})
    monkeypatch.setattr(finish.scc_finish,'_records',lambda *a:[])
    monkeypatch.setattr(finish,'_write_selected_view',lambda *a:{})
    monkeypatch.setattr(finish.scc_finish,'_run_analysis_stage',lambda *a:Path('analysis'))
    finish.run(**args,analyze_fn=lambda *a:None)
    jobs=parallel_finish.native_jobs(root,root,manifest,'bcb-scale1000:v2',
        'reproducibility/scale1000/environment-v2/requirements.txt',
        'reproducibility/scale1000/environment-v2/Dockerfile')
    assert len(jobs)==9
    assert jobs==seen


def test_stage_failure_prevents_analysis(tmp_path,monkeypatch):
    _,_,args=fixture(tmp_path,monkeypatch)
    called=[]
    def fail(*a): raise RuntimeError('native failed')
    monkeypatch.setattr(finish.scc_finish,'_run_native_stage',fail)
    monkeypatch.setattr(finish,'run',lambda **k:called.append(k))
    with pytest.raises(RuntimeError,match='native failed'):
        parallel_finish.run(**args)
    assert not called


def test_changed_image_fails_before_native_submission(tmp_path,monkeypatch):
    _,_,args=fixture(tmp_path,monkeypatch)
    called=[]
    monkeypatch.setattr(finish.scc_finish,'_image_id',lambda *a:'different')
    monkeypatch.setattr(finish.scc_finish,'_run_native_stage',lambda *a:called.append(a))
    with pytest.raises(ValueError,match='image differs'):
        parallel_finish.run(**args)
    assert not called
