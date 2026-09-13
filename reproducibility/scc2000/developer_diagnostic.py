"""Prepare the SCC developer-only diagnostic without executing models or Docker."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any
from reproducibility.heldout200.evidence import environment_from_gate
from reproducibility.heldout200.run_observed_native import ids, validate_observed_ids

ROOT = Path(__file__).resolve().parents[2]
SOURCE_HASHES = {
    'utils.py': 'b591deeb5d083399730062369afec279954831474677459948506c9857ed2328',
    'session.py': '9721cee26ec87b29585fc99a0e4cba942e16cc7ab05f2a7ca64c41460dea8889',
}

PAUSED = {
    "0c1ca5b96627cc9e217c36fd": 102,
    "3a7a8311ed77c570b188d89c": 102,
    "aa5b1774457304d543d858b9": 103,
}
EXPECTED_GROUPS = {101: 140, 102: 147, 103: 112}


def sha256(value: bytes | Path) -> str:
    data = value.read_bytes() if isinstance(value, Path) else value
    return hashlib.sha256(data).hexdigest()


def _load_utils(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("scc_frozen_utils", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load frozen utils: {path}")
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module


def extract_developer(final_text: str, utils: Any) -> tuple[str, str]:
    """Apply the frozen upstream extraction and method-name rules exactly."""
    code = utils.code_truncate(final_text)
    method = utils.find_method_name(code)
    if not method:
        raise ValueError("frozen extraction did not produce one developer function")
    return code, method


def _copy_snapshot(source: Path, destination: Path) -> None:
    if destination.exists():
        if not destination.is_dir():
            raise ValueError(f"snapshot target is not a directory: {destination}")
        # Existing diagnostic runs are immutable.
        for item in source.rglob("*"):
            if item.is_file():
                target = destination / item.relative_to(source)
                if not target.is_file() or target.read_bytes() != item.read_bytes():
                    raise ValueError(f"immutable source snapshot differs: {target}")
        return
    shutil.copytree(source, destination)


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"immutable diagnostic artifact differs: {path}")
    if not path.exists():
        path.write_bytes(data)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _old_record(record: dict[str, Any], generation_root: Path, output: Path,
                utils: Any) -> dict[str, Any]:
    assignment = generation_root / "assignments" / record["assignment_id"]
    input_path = Path(record["generated_test_input"])
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    payload = _load(input_path)
    if sha256(input_path) != record['generated_test_input_sha256']:
        raise ValueError('generated-test input differs from original failure inventory')
    if set(payload) != {"code", "report"} or payload["report"] != "":
        raise ValueError(f"invalid old generated-test payload: {input_path}")
    result_path = assignment / "turns" / "002" / "result.json"
    request_path = assignment / "turns" / "002.upstream_request.json"
    developer_result_path = assignment / "turns" / "001" / "result.json"
    if not result_path.is_file() or not request_path.is_file() or not developer_result_path.is_file():
        raise ValueError(f"missing tester source for {record['assignment_id']}")
    result = _load(result_path)
    tester = utils.code_truncate(result["final_text"])
    developer, method = extract_developer(_load(developer_result_path)["final_text"], utils)
    suffix = ("\n" + tester + "\ncheck(" + method + ")").encode("utf-8")
    combined = payload["code"].encode("utf-8")
    if sha256(combined) != record['developer_program_sha256']:
        raise ValueError('combined payload differs from original failure inventory')
    if not combined.endswith(suffix):
        raise ValueError(f"combined generated input is not exact developer/tester assembly: {input_path}")
    assembled_developer = combined[:-len(suffix)]
    if assembled_developer.decode("utf-8") != developer:
        raise ValueError(f"developer source differs from turn001 extraction: {record['assignment_id']}")
    # The prior partial audit retained the combined developer+tester input under
    # those legacy fields; keep them as provenance and derive the developer hash
    # only from the exact source assembly above.
    out = output / "assignments" / record["assignment_id"]
    _copy_snapshot(assignment, out / "source_snapshot")
    _write_once(out / "developer_program.py", assembled_developer)
    return {
        "assignment_id": record["assignment_id"], "task_id": record["task_id"],
        "method": record["method"], "replicate_id": int(record["replicate_id"]),
        "source_kind": "docker_failed_retained_candidate",
        "developer_program": str(out / "developer_program.py"),
        "developer_program_sha256": sha256(assembled_developer), "developer_program_bytes": len(assembled_developer),
        "legacy_audit_code_sha256": record["developer_program_sha256"],
        "legacy_audit_code_bytes": record["developer_program_bytes"],
        "generated_test_input": str(input_path), "generated_test_input_sha256": sha256(input_path),
        "tester_result": str(result_path), "tester_result_sha256": sha256(result_path),
        "tester_upstream_request": str(request_path), "tester_upstream_request_sha256": sha256(request_path),
        "developer_result": str(developer_result_path), "developer_result_sha256": sha256(developer_result_path),
        "native_outcome": "unknown", "report": "", "assembly_verified": True,
    }


def _paused_record(assignment_id: str, generation_root: Path, output: Path,
                   utils: Any) -> dict[str, Any]:
    assignment = generation_root / "assignments" / assignment_id
    cell = _load(assignment / "cell.json")
    result_path = assignment / "turns" / "001" / "result.json"
    request_path = assignment / "turns" / "001.upstream_request.json"
    if not result_path.is_file() or not request_path.is_file():
        raise ValueError(f"paused assignment lacks developer result: {assignment_id}")
    result = _load(result_path)
    developer, method = extract_developer(result["final_text"], utils)
    out = output / "assignments" / assignment_id
    _copy_snapshot(assignment, out / "source_snapshot")
    _write_once(out / "developer_program.py", developer.encode("utf-8"))
    return {
        "assignment_id": assignment_id, "task_id": cell["task_id"],
        "method": cell["method"], "replicate_id": int(cell["replicate_id"]),
        "source_kind": "paused_turn_001_developer_result",
        "developer_program": str(out / "developer_program.py"),
        "developer_program_sha256": sha256(developer.encode("utf-8")),
        "developer_program_bytes": len(developer.encode("utf-8")),
        "developer_result": str(result_path), "developer_result_sha256": sha256(result_path),
        "developer_upstream_request": str(request_path), "developer_upstream_request_sha256": sha256(request_path),
        "native_outcome": "unknown", "assembly_verified": True,
    }


def validate_setup(setup: dict[str, Any]) -> None:
    if setup.get("schema") != "scc-developer-diagnostic-20260913-v1":
        raise ValueError("unexpected diagnostic setup schema")
    groups = {int(g["replicate_id"]): g for g in setup.get("groups", [])}
    if len(setup.get('groups', [])) != 3 or set(groups) != set(EXPECTED_GROUPS):
        raise ValueError("diagnostic replicate groups differ")
    if {k: int(v["count"]) for k, v in groups.items()} != EXPECTED_GROUPS:
        raise ValueError("diagnostic group counts differ")
    if sum(int(g["count"]) for g in groups.values()) != 399:
        raise ValueError("diagnostic must contain 399 programs")
    if setup.get("native_executed") is not False:
        raise ValueError("diagnostic preparation must be pre-execution")
    records = setup.get("records", [])
    if len(records) != 399 or len({r["assignment_id"] for r in records}) != 399:
        raise ValueError("diagnostic identities are not exactly 399 unique assignments")
    if any(r.get("native_outcome") != "unknown" for r in records):
        raise ValueError("primary statuses must remain unknown")
    if any(not r.get("assembly_verified") for r in records):
        raise ValueError("unverified source assembly")
    for key in ('dataset', 'prepared', 'selection', 'control_gate', 'prefix_manifest'):
        if sha256(Path(setup[key])) != setup[key + '_sha256']:
            raise ValueError('frozen input differs: ' + key)
    selection = _load(Path(setup['selection']))
    allocated = selection['assigned_task_ids']
    if ids(Path(setup['dataset'])) != allocated or ids(Path(setup['prepared'])) != allocated:
        raise ValueError('dataset/prepared allocation differs')
    if setup['dataset_sha256'] != selection['evaluator_dataset_sha256'] or setup['prepared_sha256'] != selection['model_input_sha256']:
        raise ValueError('dataset hashes differ from original selection')
    gate = _load(Path(setup['control_gate']))
    env = environment_from_gate(Path(setup['control_gate']).parent)
    if not gate.get('controls_complete') or gate['assigned_task_ids'] != allocated or gate['image_id'] != setup['frozen_image_id'] or env != setup['control_environment']:
        raise ValueError('frozen control evidence differs')
    prefix = {c['id']: c for c in _load(Path(setup['prefix_manifest']))['selected_cells']}
    if len(prefix) != 6000:
        raise ValueError('scientific prefix differs')
    for path, expected in setup['frozen_source_hashes'].items():
        if sha256(Path(path)) != expected:
            raise ValueError('extraction source changed')
    utils = _load_utils(Path(setup['extraction_utils']))
    expected_programs = {}
    for record in records:
        snapshot = Path(record['source_snapshot'])
        actual_files = {p.relative_to(snapshot).as_posix(): sha256(p) for p in snapshot.rglob('*') if p.is_file()}
        if actual_files != record['source_snapshot_files']:
            raise ValueError('retained source snapshot differs')
        cell, status = _load(snapshot/'cell.json'), _load(snapshot/'status.json')
        if prefix.get(record['assignment_id']) != cell:
            raise ValueError('record outside the frozen selected allocation')
        if any(cell[k] != record[k] for k in ('task_id', 'method', 'replicate_id')):
            raise ValueError('diagnostic cell identity differs')
        developer, method = extract_developer(_load(snapshot/'turns/001/result.json')['final_text'], utils)
        if record['source_kind'] == 'docker_failed_retained_candidate':
            if status['state'] != 'infrastructure_failure' or 'container' not in status.get('reason', '').lower():
                raise ValueError('Docker-failure status differs')
            payload = _load(snapshot/'generated_tests/000/input.json')
            tester = utils.code_truncate(_load(snapshot/'turns/002/result.json')['final_text'])
            if payload != {'code': developer+'\n'+tester+'\ncheck('+method+')', 'report': ''}:
                raise ValueError('stored combined payload differs from frozen source assembly')
        elif record['source_kind'] == 'paused_turn_001_developer_result':
            if status['state'] != 'paused' or PAUSED.get(cell['id']) != cell['replicate_id']:
                raise ValueError('historical paused identity differs')
        else:
            raise ValueError('unknown retained-program source kind')
        data = developer.encode('utf-8')
        if sha256(data) != record['developer_program_sha256'] or Path(record['developer_program']).read_bytes() != data:
            raise ValueError('developer program differs from original extraction')
        key = f"{cell['replicate_id']}:{cell['task_id']}:{cell['id']}"
        expected_programs[key] = sha256(data)
    if expected_programs != setup['candidate_source_hashes']:
        raise ValueError('source hash inventory differs')
    if len(set((r['replicate_id'], r['task_id']) for r in records)) != 399:
        raise ValueError('duplicate task/replicate identity')
    for rep, group in groups.items():
        path = Path(group['samples'])
        if sha256(path) != group['samples_sha256']:
            raise ValueError('prepared sample bytes differ')
        samples = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        validate_observed_ids([r['task_id'] for r in samples], allocated)
        wanted = [r for r in records if r['replicate_id'] == rep]
        expected_samples = [{'task_id': r['task_id'], 'solution': Path(r['developer_program']).read_text(encoding='utf-8')} for r in wanted]
        if samples != expected_samples or len(samples) != group['count']:
            raise ValueError('sample rows differ from exact developer programs')


def prepare(*, old_audit: Path, generation_root: Path, output: Path,
            selection: Path, dataset: Path, prepared: Path, control_gate: Path,
            frozen_source_root: Path) -> dict[str, Any]:
    audit = _load(old_audit)
    old_records = list(audit["records"])
    if len(old_records) != 396:
        raise ValueError("old Docker-failure audit must contain 396 records")
    utils_path = frozen_source_root / "reproducibility/external_baselines/vendor/scc_2024/utils.py"
    adapter_path = frozen_source_root / "reproducibility/external_baselines/scc.py"
    if sha256(adapter_path) != "5349376721b3938deec45fc1c8b05ce33f7804c792209a1ff34c217ca36801e1":
        raise ValueError("generation extraction source hash mismatch")
    for name, expected in SOURCE_HASHES.items():
        if sha256(utils_path.parent/name) != expected:
            raise ValueError('frozen SCC source changed: ' + name)
    utils = _load_utils(utils_path)
    output.mkdir(parents=True, exist_ok=True)
    records = [_old_record(r, generation_root, output, utils) for r in old_records]
    records.extend(_paused_record(i, generation_root, output, utils) for i in PAUSED)
    for record in records:
        snapshot = output/'assignments'/record['assignment_id']/'source_snapshot'
        record['source_snapshot'] = str(snapshot.resolve())
        record['source_snapshot_files'] = {p.relative_to(snapshot).as_posix(): sha256(p) for p in snapshot.rglob('*') if p.is_file()}
    allocation = _load(selection)["assigned_task_ids"]
    order = {task: i for i, task in enumerate(allocation)}
    records.sort(key=lambda r: (order.get(r["task_id"], len(order)), int(r["replicate_id"])))
    groups = []
    for rep in (101, 102, 103):
        rows = [r for r in records if int(r["replicate_id"]) == rep]
        sample_path = output / f"replicate-{rep}" / "samples.jsonl"
        data = ("\n".join(json.dumps({"task_id": r["task_id"], "solution": Path(r["developer_program"]).read_text(encoding="utf-8")}, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")
        _write_once(sample_path, data)
        groups.append({"replicate_id": rep, "samples": str(sample_path.resolve()), "count": len(rows), "native_outcome": "unknown", "samples_sha256": sha256(sample_path)})
    prefix = ROOT/'reproducibility/scc2000/freeze-v3/selection_manifest.json'
    setup = {
        "schema": "scc-developer-diagnostic-20260913-v1", "native_executed": False,
        "quality_interpretation": "developer-only diagnostic; primary SCC statuses remain unknown",
        "original_partial_diagnostic_v2_executed": False,
        "control_gate": str(control_gate.resolve()), "dataset": str(dataset.resolve()),
        "prepared": str(prepared.resolve()), "selection": str(selection.resolve()),
        "control_gate_sha256": sha256(control_gate), "dataset_sha256": sha256(dataset),
        "prepared_sha256": sha256(prepared), "selection_sha256": sha256(selection),
        "frozen_image_id": _load(control_gate).get("image_id"),
        "control_environment": environment_from_gate(control_gate.resolve().parent),
        "prefix_manifest": str(prefix), "prefix_manifest_sha256": sha256(prefix),
        "groups": groups, "records": records,
        "candidate_source_hashes": {f"{r['replicate_id']}:{r['task_id']}:{r['assignment_id']}": r["developer_program_sha256"] for r in records},
        "extraction_source": str(adapter_path.resolve()), "extraction_source_sha256": sha256(adapter_path),
        "extraction_utils": str(utils_path.resolve()), "extraction_utils_sha256": sha256(utils_path),
        "frozen_source_hashes": {str(p.resolve()): sha256(p) for p in (adapter_path, utils_path, utils_path.parent/'session.py')},
    }
    validate_setup(setup)
    _write_once(output / "setup.json", (json.dumps(setup, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return setup


def main() -> int:
    p = argparse.ArgumentParser()
    for name in ("old-audit", "generation-root", "output", "selection", "dataset", "prepared", "control-gate", "frozen-source-root"):
        p.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    a = p.parse_args()
    setup = prepare(**vars(a))
    print(json.dumps({"schema": setup["schema"], "records": len(setup["records"]), "groups": setup["groups"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
