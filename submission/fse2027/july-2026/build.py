from pathlib import Path
import subprocess,json,sys
base=Path(__file__).resolve().parent
paper=base/'paper'
(base/'validation').mkdir(parents=True,exist_ok=True)
results=[]
for number,cmd in enumerate([['pdflatex','-interaction=nonstopmode','-halt-on-error','-file-line-error','main.tex'],['bibtex','main'],['pdflatex','-interaction=nonstopmode','-halt-on-error','-file-line-error','main.tex'],['pdflatex','-interaction=nonstopmode','-halt-on-error','-file-line-error','main.tex']],1):
    result=subprocess.run(cmd,cwd=paper,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=result.stdout.decode('utf-8',errors='replace')
    (base/'validation'/f'build-{number}.txt').write_text(log,encoding='utf-8')
    results.append({'command':cmd,'exit_code':result.returncode})
    print('Step',number,'exit',result.returncode)
    if result.returncode:
        print(log[-5500:]);sys.exit(result.returncode)
(base/'validation/build_result.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print('Build succeeded')
