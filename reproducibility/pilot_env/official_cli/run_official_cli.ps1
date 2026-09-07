param(
    [Parameter(Mandatory = $true)][string]$Samples,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$Image = "bcb-official-cli:dev",
    [string]$Split = "instruct",
    [string]$Subset = "full",
    [string]$SelectedIds = "BigCodeBench/325,BigCodeBench/322,BigCodeBench/1036,BigCodeBench/1005,BigCodeBench/361,BigCodeBench/1087,BigCodeBench/45,BigCodeBench/309"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$source = (Resolve-Path $Samples).Path
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Samples file not found: $source" }

$expectedCommit = "09dd993f46c3fbf3a799465bb96d524edcb0b199"
$upstream = "$repo\reproducibility\vendor\bigcodebench"
$actualCommit = (& git -C $upstream rev-parse HEAD).Trim()
if ($actualCommit -ne $expectedCommit) { throw "Pinned upstream HEAD mismatch: expected $expectedCommit, got $actualCommit" }
& git -C $upstream diff --quiet --exit-code HEAD --
if ($LASTEXITCODE -ne 0) { throw "Pinned upstream checkout has tracked changes" }

New-Item -ItemType Directory -Force $OutputDir | Out-Null
$out = (Resolve-Path $OutputDir).Path
if (@(Get-ChildItem -LiteralPath $out -Force).Count -gt 0) { throw "Output directory must be empty: $out" }
$stage = Join-Path $out "input"
New-Item -ItemType Directory -Force $stage | Out-Null
$staged = Join-Path $stage "samples.jsonl"
Copy-Item -LiteralPath $source -Destination $staged

$imageId = (docker --context default image inspect $Image --format '{{.Id}}').Trim()
if (-not $imageId) { throw "Docker image not found: $Image" }

function Get-Hash([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Get-TreeHash([string]$rootPath) {
    $rootPath = (Resolve-Path -LiteralPath $rootPath).Path.TrimEnd('\')
    $hash = [System.Security.Cryptography.IncrementalHash]::CreateHash([System.Security.Cryptography.HashAlgorithmName]::SHA256)
    try {
        $files = Get-ChildItem -LiteralPath $rootPath -Recurse -File | Where-Object {
            $parts = $_.FullName.Substring($rootPath.Length + 1).Split('\')
            ($parts -notcontains '.git') -and ($parts -notcontains '__pycache__')
        }
        $relativePaths = [string[]]@($files | ForEach-Object { $_.FullName.Substring($rootPath.Length + 1).Replace('\','/') })
        [Array]::Sort($relativePaths, [StringComparer]::Ordinal)
        foreach ($relative in $relativePaths) {
            $hash.AppendData([Text.Encoding]::UTF8.GetBytes($relative))
            $hash.AppendData([byte[]](0))
            $hash.AppendData([Convert]::FromHexString((Get-Hash (Join-Path $rootPath $relative))))
            $hash.AppendData([Text.Encoding]::UTF8.GetBytes("`n"))
        }
        return ([Convert]::ToHexString($hash.GetHashAndReset())).ToLowerInvariant()
    } finally { $hash.Dispose() }
}

$baseImage = (docker --context default image inspect bcb-pilot:dev --format '{{.Id}}').Trim()
if (-not $baseImage) { throw "Base image bcb-pilot:dev not found" }
$sourceTreeHash = Get-TreeHash $upstream
$requirementsHash = Get-Hash "$PSScriptRoot\requirements.txt"
$dockerfileHash = Get-Hash "$PSScriptRoot\Dockerfile"

$taskDockerArgs = @(
    "--context", "default", "run", "--rm", "--network", "none", "--read-only",
    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65532:65532",
    "--memory", "2g", "--pids-limit", "128", "--cpus", "2",
    "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
    "--mount", "type=bind,source=$repo\reproducibility\vendor\bigcodebench,target=/workspace/reproducibility/vendor/bigcodebench,readonly",
    "--mount", "type=bind,source=$repo\reproducibility\data\bigcodebench-v0.1.4.jsonl,target=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl,readonly",
    "--mount", "type=bind,source=$out,target=/run",
    "--mount", "type=bind,source=$staged,target=/run/input/samples.jsonl,readonly",
    "--env", "BIGCODEBENCH_OVERRIDE_PATH=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl",
    "--entrypoint", "python", $imageId, "-m", "bigcodebench.evaluate",
    $Split, $Subset, "--samples", "/run/input/samples.jsonl", "--execution", "local",
    "--selective_evaluate", $SelectedIds, "--calibrated", "False", "--parallel", "1",
    "--no_gt", "True", "--save_pass_rate", "False", "--min_time_limit", "0.1",
    "--max_as_limit", "30720", "--max_data_limit", "30720", "--max_stack_limit", "10"
)

$metadata = [ordered]@{
    executable = "docker"
    arguments = $taskDockerArgs
    image_requested = $Image
    image_id_invoked = $imageId
    base_image_id = $baseImage
    upstream_commit_expected = $expectedCommit
    upstream_commit_verified = $actualCommit
    samples_source = $source
    samples_sha256 = Get-Hash $source
    staged_samples_sha256 = Get-Hash $staged
    official_dataset_sha256 = Get-Hash "$repo\reproducibility\data\bigcodebench-v0.1.4.jsonl"
    network = "none"
    calibrated = $false
    selected_ids = $SelectedIds.Split(',')
    source_tree_sha256 = $sourceTreeHash
    source_tree_hash_algorithm = "SHA256(sorted UTF-8 relative-path + NUL + file-SHA256 bytes + LF; excludes .git and __pycache__)"
    requirements_sha256 = $requirementsHash
    dockerfile_sha256 = $dockerfileHash
}
$metadata | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")

$freezeArgs = @("--context", "default", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65532:65532", "--entrypoint", "python", $imageId, "-m", "pip", "freeze")
& docker @freezeArgs 1> (Join-Path $out "pip-freeze.txt") 2> (Join-Path $out "pip-freeze.stderr.log")
if ($LASTEXITCODE -ne 0) { throw "Could not capture pip freeze; see pip-freeze.stderr.log" }
$metadata.package_freeze_sha256 = Get-Hash (Join-Path $out "pip-freeze.txt")
$metadata | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")

& docker @taskDockerArgs 1> (Join-Path $out "stdout.log") 2> (Join-Path $out "stderr.log")
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) { throw "Official CLI failed with exit code $exitCode; see stderr.log" }
if ((Get-Hash $staged) -ne $metadata.samples_sha256) { throw "Staged samples changed during evaluation" }
$metadata.post_evaluator_staged_samples_sha256 = Get-Hash $staged
$metadata | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")
exit 0
