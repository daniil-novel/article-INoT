"""Resolve held-out evaluator identity through frozen raw control evidence."""
from pathlib import Path
import json
from ..scale_env.validate_native import sha256, validate_native


def environment_from_gate(folder: Path):
    gate = json.loads((folder / 'heldout200_control_gate.json').read_text(encoding='utf-8'))
    environments = []
    for kind in ('gold', 'incorrect'):
        root = folder / kind
        for suffix, relative in (('metadata','run-metadata.json'),('report','input/samples_eval_results.json'),('samples','input/samples.jsonl')):
            if sha256(root / relative) != gate[f'{kind}_{suffix}_sha256']:
                raise ValueError('Control evidence changed after gate: ' + kind + '/' + relative)
        meta = json.loads((root / 'run-metadata.json').read_text(encoding='utf-8'))
        fields = ('image_id','base_image_id','upstream_commit_verified','network','cli_split',
                  'package_freeze_sha256','nltk_resources_sha256')
        environment = {**{k:meta[k] for k in fields}, **meta['provenance']}
        samples = [json.loads(line) for line in (root / 'input/samples.jsonl').read_text(encoding='utf-8').splitlines()]
        expected = {r['task_id']:r['solution'] for r in samples}
        if list(expected) != gate['assigned_task_ids']:
            raise ValueError('Control sample order differs from assignment')
        checked = validate_native(root, expected, environment)
        if not checked['ok']:
            raise ValueError('Native control integrity failed: ' + repr(checked['errors']))
        if any(checked['statuses'][t] != gate['status_by_task'][t][kind] for t in gate['assigned_task_ids']):
            raise ValueError('Frozen control status does not match original report')
        environments.append(environment)
    if environments[0] != environments[1]:
        raise ValueError('Control environments differ')
    if environments[0]['image_id'] != gate['image_id'] or environments[0]['vendor_tree_sha256'] != gate['source_tree_sha256']:
        raise ValueError('Gate does not match verified environment')
    expected_eligible = [t for t in gate['assigned_task_ids'] if gate['status_by_task'][t]['gold'] == 'pass' and gate['status_by_task'][t]['incorrect'] == 'fail']
    if gate['evaluable_task_ids'] != expected_eligible or not gate['controls_complete']:
        raise ValueError('Control-derived eligibility is incorrect')
    return environments[0]
