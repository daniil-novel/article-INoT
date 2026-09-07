param(
    [string]$Predictions,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$Image = "bcb-pilot:dev"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$expectedCommit = "09dd993f46c3fbf3a799465bb96d524edcb0b199"
$actualCommit = (& git -C "$repo\reproducibility\vendor\bigcodebench" rev-parse HEAD).Trim()
if ($actualCommit -ne $expectedCommit) { throw "Pinned upstream HEAD mismatch: expected $expectedCommit, got $actualCommit" }
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$out = (Resolve-Path $OutputDir).Path
$existing = @(Get-ChildItem -LiteralPath $out -Force)
if ($existing.Count -gt 0) { throw "Output directory must be empty: $out" }
$imageId = (docker --context default image inspect $Image --format '{{.Id}}').Trim()
if (-not $imageId) { throw "Docker image not found: $Image" }

# Bind only the explicit evaluator inputs; the article workspace is never mounted.
$mounts = @(
    "type=bind,source=$repo\reproducibility\bcb_pilot_evaluator.py,target=/workspace/bcb_pilot_evaluator.py,readonly",
    "type=bind,source=$repo\reproducibility\data\bigcodebench-v0.1.4.jsonl,target=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl,readonly",
    "type=bind,source=$repo\reproducibility\data\bigcodebench-split\prepared.jsonl,target=/workspace/reproducibility/data/bigcodebench-split/prepared.jsonl,readonly",
    "type=bind,source=$repo\reproducibility\vendor\bigcodebench,target=/workspace/reproducibility/vendor/bigcodebench,readonly",
    "type=bind,source=$repo\reproducibility\pilot_env\requirements.txt,target=/workspace/reproducibility/pilot_env/requirements.txt,readonly",
    "type=bind,source=$repo\reproducibility\pilot_env\Dockerfile,target=/workspace/reproducibility/pilot_env/Dockerfile,readonly",
    "type=bind,source=$out,target=/out"
)
if ($Predictions) {
    $pred = (Resolve-Path $Predictions).Path
    $mounts += "type=bind,source=$pred,target=/workspace/predictions.jsonl,readonly"
}
$taskDockerArgs = @("--context", "default", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--entrypoint", "python",
    "--security-opt", "no-new-privileges", "--user", "65532:65532", "--memory", "2g",
    "--pids-limit", "128", "--cpus", "2", "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m")
foreach ($mount in $mounts) { $taskDockerArgs += @("--mount", $mount) }
$outputName = if ($Predictions) { "pilot-predictions.json" } else { "pilot-controls.json" }
$taskDockerArgs += @($imageId, "/workspace/bcb_pilot_evaluator.py", "--root", "/workspace", "--output", "/out/$outputName", "--image-ref", $Image, "--image-id", $imageId)
if ($Predictions) { $taskDockerArgs += @("--predictions", "/workspace/predictions.jsonl") }
$argvRecord = [ordered]@{
    executable = "docker"
    arguments = $taskDockerArgs
    image_tag_requested = $Image
    image_id_invoked = $imageId
    upstream_commit_expected = $expectedCommit
    upstream_commit_verified = $actualCommit
}
$argvRecord | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 (Join-Path $out "launcher-argv.json")
$stdoutPath = Join-Path $out "launcher-stdout.log"
$stderrPath = Join-Path $out "launcher-stderr.log"
& docker @taskDockerArgs 1> $stdoutPath 2> $stderrPath
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) { throw "Docker evaluator failed with exit code $exitCode; see launcher-stderr.log" }
exit 0
