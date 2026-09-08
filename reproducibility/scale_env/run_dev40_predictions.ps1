param(
    [Parameter(Mandatory = $true)][string]$Samples,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$Image = "bcb-scale40:v2",
    [int]$DeadlineSeconds = 3600,
    [string]$ControlGate = "reproducibility/runs/dev40-controls-v3/dev40_control_gate.json"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$upstream = "$repo\reproducibility\vendor\bigcodebench"
$prepared = "$repo\reproducibility\data\bigcodebench-split\prepared.jsonl"
$dataset = "$repo\reproducibility\runs\dev40-controls-v1\inputs\official_dev40.jsonl"
$source = (Resolve-Path $Samples).Path
$ids = @(Get-Content -LiteralPath $prepared | Where-Object { $_.Trim() } | Select-Object -First 40 | ForEach-Object { ($_ | ConvertFrom-Json).task_id })
if ($ids.Count -ne 40 -or (@($ids | Sort-Object -Unique).Count -ne 40)) { throw "Prepared split does not provide 40 unique IDs" }
$rows = @(Get-Content -LiteralPath $source | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
if ($rows.Count -ne 40 -or (@($rows.task_id | Sort-Object -Unique).Count -ne 40) -or ((@($rows.task_id | Sort-Object) -join "\n") -ne (@($ids | Sort-Object) -join "\n"))) { throw "Prediction samples must contain exactly the frozen 40 unique IDs" }
$expectedCommit = "09dd993f46c3fbf3a799465bb96d524edcb0b199"
$actualCommit = (& git -C $upstream rev-parse HEAD).Trim()
if ($actualCommit -ne $expectedCommit) { throw "Pinned upstream HEAD mismatch" }
& git -C $upstream diff --quiet --exit-code HEAD --
if ($LASTEXITCODE -ne 0) { throw "Pinned upstream checkout has tracked changes" }
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$out = (Resolve-Path $OutputDir).Path
if (@(Get-ChildItem -LiteralPath $out -Force).Count -gt 0) { throw "Output directory must be empty" }
$stage = Join-Path $out "input"; New-Item -ItemType Directory -Force $stage | Out-Null
$staged = Join-Path $stage "samples.jsonl"; Copy-Item -LiteralPath $source -Destination $staged
function Hash([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$imageId = (docker --context default image inspect $Image --format '{{.Id}}').Trim()
if (-not $imageId) { throw "Image not found" }
$control = Get-Content -Raw -LiteralPath $ControlGate | ConvertFrom-Json
if ($control.image_id -ne $imageId) { throw "Prediction image differs from validated controls" }
$containerName = "bcb-dev40-" + [guid]::NewGuid().ToString("N")
$taskDockerArgs = @("--context","default","run","--rm","--name",$containerName,"--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--user","65532:65532","--memory","3g","--pids-limit","256","--cpus","2","--tmpfs","/tmp:rw,noexec,nosuid,size=512m","--mount","type=bind,source=$upstream,target=/workspace/reproducibility/vendor/bigcodebench,readonly","--mount","type=bind,source=$dataset,target=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl,readonly","--mount","type=bind,source=$out,target=/run","--mount","type=bind,source=$staged,target=/run/input/samples.jsonl,readonly","--env","BIGCODEBENCH_OVERRIDE_PATH=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl","--env","NLTK_DATA=/opt/nltk_data","--entrypoint","python",$imageId,"-m","bigcodebench.evaluate","instruct","full","--samples","/run/input/samples.jsonl","--execution","local","--selective_evaluate",($ids -join ','),"--calibrated","False","--parallel","2","--no_gt","True","--save_pass_rate","False","--min_time_limit","0.1","--max_as_limit","30720","--max_data_limit","30720","--max_stack_limit","10")
$provenance = (& C:\Python311\python.exe "$PSScriptRoot\provenance.py" --vendor $upstream --dataset $dataset --prepared $prepared --requirements "$PSScriptRoot\requirements.txt" --dockerfile "$PSScriptRoot\Dockerfile" | ConvertFrom-Json)
$metadata = [ordered]@{schema="bcb-dev40-prediction-run-v1";image_id=$imageId;base_image_id=$control.base_image_id;upstream_commit_verified=$actualCommit;selected_ids=$ids;cli_split="instruct";dataset_partition="development (40 seeded IDs)";network="none";argv=$taskDockerArgs;samples_source_sha256=(Hash $source);staged_samples_sha256=(Hash $staged);deadline_seconds=$DeadlineSeconds;run_status="prepared";provenance=$provenance;expected_missing_status="missing report rows remain missing; never inferred pass/fail"}
$metadata | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")
$freezeArgs = @("--context","default","run","--rm","--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--user","65532:65532","--entrypoint","python",$imageId,"-m","pip","freeze")
& docker @freezeArgs 1> (Join-Path $out "pip-freeze.txt") 2> (Join-Path $out "pip-freeze.stderr.log")
if ($LASTEXITCODE -ne 0) { throw "Could not capture pip freeze" }
$resourceArgs = @("--context","default","run","--rm","--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--user","65532:65532","--entrypoint","sh",$imageId,"-c","find /opt/nltk_data -type f -print0 | sort -z | xargs -0 sha256sum")
& docker @resourceArgs 1> (Join-Path $out "nltk-resources-sha256.txt") 2> (Join-Path $out "nltk-resources-sha256.stderr.log")
if ($LASTEXITCODE -ne 0) { throw "Could not capture NLTK resource hashes" }
$metadata.package_freeze_sha256=Hash (Join-Path $out "pip-freeze.txt")
$metadata.nltk_resources_sha256=Hash (Join-Path $out "nltk-resources-sha256.txt")
$metadata | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")
function Invoke-DockerWithDeadline([string[]]$arguments, [string]$stdoutPath, [string]$stderrPath, [int]$seconds) {
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = "docker"
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    foreach ($argument in $arguments) { [void]$startInfo.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::new(); $process.StartInfo = $startInfo
    if (-not $process.Start()) { throw "Could not start docker" }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($seconds * 1000)) {
        # Stop only this invocation's uniquely named container; killing the client alone leaves Docker running.
        & docker --context default rm --force $containerName 1>$null 2>$null
        if (-not $process.WaitForExit(10000)) { $process.Kill($true); $process.WaitForExit() }
        [IO.File]::WriteAllText($stdoutPath, $stdoutTask.Result)
        [IO.File]::WriteAllText($stderrPath, $stderrTask.Result)
        $process.Dispose()
        return 124
    }
    [IO.File]::WriteAllText($stdoutPath, $stdoutTask.Result)
    [IO.File]::WriteAllText($stderrPath, $stderrTask.Result)
    $code = $process.ExitCode; $process.Dispose(); return $code
}
$exitCode=Invoke-DockerWithDeadline $taskDockerArgs (Join-Path $out "stdout.log") (Join-Path $out "stderr.log") $DeadlineSeconds
if ($exitCode -eq 124) { $metadata.run_status="run_level_timeout"; $metadata | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json"); throw "Prediction evaluator exceeded run-level deadline; partial report retained" }
if ($exitCode -ne 0) { $metadata.run_status="evaluator_error"; $metadata | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json"); throw "Prediction evaluator failed with exit code $exitCode; see stderr.log" }
if ((Hash $staged) -ne $metadata.samples_source_sha256) { throw "Staged samples changed during evaluation" }
$metadata.post_evaluator_staged_samples_sha256=Hash $staged
$metadata.run_status="completed"
$metadata | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")
exit 0
