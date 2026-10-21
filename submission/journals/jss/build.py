"""Build only the manuscript PDF; never execute study or generated programs."""
from pathlib import Path
import os
import shutil
import subprocess
import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root = Path(__file__).resolve().parent
source = root / "manuscript"
build = root / "qa" / "build"
build.mkdir(parents=True, exist_ok=True)
for intermediate in ("main.aux", "main.bbl", "main.out"):
    (build / intermediate).unlink(missing_ok=True)

def find_tool(name):
    installed = shutil.which(name)
    if installed:
        return installed
    candidate = Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64" / (name + ".exe")
    if candidate.is_file():
        return str(candidate)
    raise SystemExit(f"Install a TeX distribution with {name}, then run this file again.")

pdflatex, bibtex = find_tool("pdflatex"), find_tool("bibtex")
env = os.environ.copy()
env["BIBINPUTS"] = str(source) + os.pathsep + env.get("BIBINPUTS", "")
env["BSTINPUTS"] = str(source) + os.pathsep + env.get("BSTINPUTS", "")
commands = [
    ([pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-output-directory={build}", "main.tex"], source),
    ([bibtex, "main"], build),
    ([pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-output-directory={build}", "main.tex"], source),
    ([pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-output-directory={build}", "main.tex"], source),
    ([pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-output-directory={build}", "main.tex"], source),
]
for index, (command, cwd) in enumerate(commands, 1):
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (build / f"step-{index}.txt").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        print(completed.stdout[-16000:])
        raise SystemExit(f"Typesetting step {index} failed; see qa/build/step-{index}.txt.")
log = (build / "main.log").read_text(encoding="utf-8", errors="replace")
unresolved = [line for line in log.splitlines() if re.search(r"undefined|Rerun to get cross-references|There were undefined", line, re.I)]
if unresolved:
    raise SystemExit("Unresolved references or citations: " + "\n".join(unresolved))
shutil.copyfile(build / "main.pdf", source / "main.pdf")
shutil.copyfile(build / "main.bbl", source / "main.bbl")
summary = {"compiled": True, "undefined_references_or_citations": unresolved, "overfull_boxes": re.findall(r"Overfull[^\n]+", log), "pdf": str(source / "main.pdf")}
(root / "qa/compile-check.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
