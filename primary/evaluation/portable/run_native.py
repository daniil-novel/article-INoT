"""Print or explicitly execute an isolated native replay into a fresh directory."""
from __future__ import annotations
import argparse, json, subprocess, tempfile, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def command(run: Path, image: str, output: Path, name: str) -> list[str]:
    source=(run/"input/samples.jsonl").resolve()
    if not source.is_file():
        raise SystemExit(f"Missing staged programs: {source}")
    meta=json.loads((run/"run-metadata.json").read_text(encoding="utf-8"))
    argv=meta["argv"]
    start=argv.index("bigcodebench.evaluate")+1
    options=list(argv[start:])
    options[options.index("--samples")+1]="/run/input/samples.jsonl"
    return ["docker","run","--name",name,"--rm","--network","none","--read-only",
        "--cap-drop","ALL","--security-opt","no-new-privileges","--user","65532:65532",
        "--memory","3g","--pids-limit","256","--cpus","2",
        "--tmpfs","/tmp:rw,noexec,nosuid,size=512m",
        "--mount",f"type=bind,source={output},target=/run",
        "--mount",f"type=bind,source={source},target=/run/input/samples.jsonl,readonly",
        image,*options]

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-dir",type=Path,required=True)
    parser.add_argument("--image",default="fse2027-native-replay")
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    run=args.run_dir.resolve()
    if ROOT.resolve() not in run.parents:
        raise SystemExit("Run directory must be inside this review archive.")
    output=Path(tempfile.mkdtemp(prefix="fse-native-replay-")).resolve()
    (output/"input").mkdir()
    # Only these newly created directories are writable by the isolated container UID.
    output.chmod(0o777)
    (output/"input").chmod(0o777)
    name="fse-native-replay-"+uuid.uuid4().hex
    argv=command(run,args.image,output,name)
    deadline=int(json.loads((run/"run-metadata.json").read_text(encoding="utf-8")).get("deadline_seconds",14400))
    print(json.dumps({"argv":argv,"output":str(output),"executed":args.execute,"deadline_seconds":deadline},indent=2))
    if args.execute:
        try:
            result=subprocess.run(argv,check=False,timeout=deadline)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker","rm","-f",name],check=False,timeout=60)
            raise SystemExit("Native replay exceeded the retained external deadline.")
        raise SystemExit(result.returncode)
