"""Choose deterministic illustrative discordances; no inference or score changes."""
import argparse
import json
from pathlib import Path


def select(records):
    index = {}
    for record in records:
        key = record['task_id'], record['arm']
        if key in index:
            raise ValueError('Duplicate task and arm')
        index[key] = record
    tasks = sorted({key[0] for key in index}, key=lambda task: int(task.split('/')[-1]))
    chosen = []
    for roles, neutral in (('single_roles','single_neutral'), ('multi_roles','multi_neutral')):
        for direction in ('role_only_pass', 'neutral_only_pass'):
            found = None
            for task in tasks:
                a, b = index.get((task,roles)), index.get((task,neutral))
                if a is None or b is None or a['analysis_status'] is None or b['analysis_status'] is None:
                    continue
                pass_a, pass_b = a['analysis_status']=='pass', b['analysis_status']=='pass'
                if (pass_a and not pass_b) if direction=='role_only_pass' else (pass_b and not pass_a):
                    found = task
                    break
            chosen.append({'roles':roles,'neutral':neutral,'direction':direction,'task_id':found})
    return {'scope':'deterministic illustrative examples, not representative frequencies or additional tests', 'cases':chosen}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    rows=[json.loads(line) for line in args.records.read_text(encoding='utf-8').splitlines() if line.strip()]
    with args.output.open('x',encoding='utf-8') as handle:
        json.dump(select(rows),handle,ensure_ascii=False,indent=2)
        handle.write('\n')
