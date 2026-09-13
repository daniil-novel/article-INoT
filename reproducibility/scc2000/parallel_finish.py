"""Schedule independent native groups, then run the unchanged SCC finisher.

This administrative scheduler changes no candidate, evaluator option, control,
statistic or model call. Each native container keeps the frozen limits. Two
containers may run concurrently within the Docker engine's 8.32GB memory.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

from reproducibility.scc2000 import finish


def native_jobs(root: Path, inputs: Path, frozen: dict, image: str,
                requirements: str, dockerfile: str) -> list[tuple]:
    jobs = []
    for method in frozen['methods']:
        for rep in frozen['replicate_ids']:
            key = f'{method}-r{rep}'
            samples = root/'predictions'/f'{key}.jsonl'
            if not samples.is_file() or not samples.read_text(encoding='utf-8').strip():
                continue
            target = root/'native'/key
            argv = [sys.executable, '-X', 'utf8', '-m',
                    'reproducibility.heldout200.run_observed_native',
                    '--dataset', str(inputs/'evaluator/evaluator_dataset.jsonl'),
                    '--prepared', str(inputs/'input/prepared.jsonl'),
                    '--samples', str(samples), '--output', str(target),
                    '--selection', str(inputs/'selection.json'), '--image', image,
                    '--requirements', requirements, '--dockerfile', dockerfile,
                    '--deadline-seconds', '14400']
            jobs.append((root/'pipeline'/f'native-{key}', target, argv))
    return jobs


def run(*, root: Path, inputs: Path, gate_dir: Path, manifest: Path,
        selection_manifest: Path, image='bcb-scale1000:v2',
        requirements='reproducibility/scale1000/environment-v2/requirements.txt',
        dockerfile='reproducibility/scale1000/environment-v2/Dockerfile') -> dict:
    root, inputs, gate_dir, manifest, selection_manifest = [p.resolve() for p in
        (root, inputs, gate_dir, manifest, selection_manifest)]
    selection = finish._read(selection_manifest)
    finish._terminal_selected(root/'generation', set(selection['selected_ids']))
    finish._verify_prefix(selection, inputs, manifest, gate_dir)
    actual_image = finish.scc_finish._image_id(image)
    gate = finish._read(gate_dir/'heldout200_control_gate.json')
    env = finish.environment_from_gate(gate_dir)
    if actual_image != gate['image_id'] or actual_image != env['image_id']:
        raise ValueError('Native image differs from frozen controls')
    predictions = root/'predictions'
    if predictions.exists():
        finish.scc_export.validate_export(root/'generation', inputs, manifest, predictions, gate_dir)
    else:
        finish.scc_export.export(root/'generation', inputs, manifest, predictions, gate_dir)
    jobs = native_jobs(root, inputs, finish._read(manifest), image, requirements, dockerfile)
    # Exact original stage helper retains each command, exit and all logs.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(finish.scc_finish._run_native_stage, *job): job[0].name for job in jobs}
        for future in as_completed(futures):
            future.result()
            print('Native stage complete: '+futures[future], flush=True)
    # The original finisher validates all native reports and reuses the exact
    # completed commands before its original and amended statistical analyses.
    return finish.run(root=root, inputs=inputs, gate_dir=gate_dir, manifest=manifest,
                      selection_manifest=selection_manifest, image=image,
                      requirements=requirements, dockerfile=dockerfile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'inputs', 'gate-dir', 'manifest', 'selection-manifest'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(run(**vars(args)), flush=True)


if __name__ == '__main__':
    main()
