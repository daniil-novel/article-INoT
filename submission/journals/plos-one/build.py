from pathlib import Path
import shutil, subprocess, sys
root=Path(__file__).resolve().parent/'manuscript'
tex=shutil.which('pdflatex')
bib=shutil.which('bibtex')
if not tex or not bib:
    sys.exit('Install a current TeX distribution with pdflatex and bibtex on PATH.')
for name in ['main']:
    # Only reproducible build products in this package are removed. Sources and
    # the frozen replication archive are never touched.
    for suffix in ('.aux','.bbl','.blg','.out','.toc'):
        old=root/(name+suffix)
        if old.exists(): old.unlink()
    for command in ([tex,'-interaction=nonstopmode','-halt-on-error',name+'.tex'], [bib,name], [tex,'-interaction=nonstopmode','-halt-on-error',name+'.tex'], [tex,'-interaction=nonstopmode','-halt-on-error',name+'.tex']):
        result=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (root/(name+'-last-build.txt')).write_bytes(result.stdout)
        if result.returncode:
            sys.exit('Build failed: '+str(root/(name+'-last-build.txt')))
    log=(root/(name+'.log')).read_text(errors='replace')
    if 'undefined references' in log or 'Citation' in log and 'undefined' in log:
        sys.exit('Unresolved references in '+name)
    print(name+'.pdf')
