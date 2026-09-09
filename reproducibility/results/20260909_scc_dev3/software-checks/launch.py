import pathlib,subprocess,sys,json,os
root=pathlib.Path.cwd(); env=dict(os.environ); env['PYTHONPATH']=str(root/'tmp/external-baseline-deps')
for i in range(3):
 out=root/f'reproducibility/runs/scc-dev3-v1/generation/task-{i}'
 argv=[sys.executable,'-X','utf8','-m','reproducibility.external_baselines.scc','--task',str(root/f'reproducibility/external_baselines/pilot-inputs-v1/task-{i}.json'),'--out',str(out)]
 result=subprocess.run(argv,env=env)
 if result.returncode or json.loads((out/'status.json').read_text())['state']!='completed': break
