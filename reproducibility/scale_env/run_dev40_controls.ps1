param(
    [Parameter(Mandatory = $true)][ValidateSet("gold", "incorrect")][string]$Kind,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$Image = "bcb-scale40:dev"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$upstream = "$repo\reproducibility\vendor\bigcodebench"
$prepared = "$repo\reproducibility\data\bigcodebench-split\prepared.jsonl"
$dataset = "$repo\reproducibility\runs\dev40-controls-v1\inputs\official_dev40.jsonl"
$samples = "$repo\reproducibility\runs\dev40-controls-v1\inputs\$Kind.jsonl"
$ids = @(Get-Content -LiteralPath $prepared | Where-Object { $_.Trim() } | Select-Object -First 40 | ForEach-Object { $_ | ConvertFrom-Json }).task_id
if ($ids.Count -ne 40 -or (@($ids | Sort-Object -Unique).Count -ne 40)) { throw "Prepared split does not provide 40 unique IDs" }
$selected = $ids -join ","
$expectedCommit = "09dd993f46c3fbf3a799465bb96d524edcb0b199"
$actualCommit = (& git -C $upstream rev-parse HEAD).Trim()
if ($actualCommit -ne $expectedCommit) { throw "Pinned upstream HEAD mismatch" }
& git -C $upstream diff --quiet --exit-code HEAD --
if ($LASTEXITCODE -ne 0) { throw "Pinned upstream checkout has tracked changes" }
foreach ($path in @($dataset, $samples)) { if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing input: $path" } }

New-Item -ItemType Directory -Force $OutputDir | Out-Null
$out = (Resolve-Path $OutputDir).Path
if (@(Get-ChildItem -LiteralPath $out -Force).Count -gt 0) { throw "Output directory must be empty: $out" }
$stage = Join-Path $out "input"
New-Item -ItemType Directory -Force $stage | Out-Null
$staged = Join-Path $stage "samples.jsonl"
Copy-Item -LiteralPath $samples -Destination $staged

function Hash([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$imageId = (docker --context default image inspect $Image --format '{{.Id}}').Trim()
$baseImageId = (docker --context default image inspect bcb-official-cli:dev --format '{{.Id}}').Trim()
if (-not $imageId -or -not $baseImageId) { throw "Required image missing" }
$provenance = (& C:\Python311\python.exe "$PSScriptRoot\provenance.py" --vendor $upstream --dataset $dataset --prepared $prepared --requirements "$PSScriptRoot\requirements.txt" --dockerfile "$PSScriptRoot\Dockerfile" | ConvertFrom-Json)

$taskDockerArgs = @(
    "--context", "default", "run", "--rm", "--network", "none", "--read-only",
    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65532:65532",
    "--memory", "3g", "--pids-limit", "256", "--cpus", "2",
    "--tmpfs", "/tmp:rw,noexec,nosuid,size=512m",
    "--mount", "type=bind,source=$upstream,target=/workspace/reproducibility/vendor/bigcodebench,readonly",
    "--mount", "type=bind,source=$dataset,target=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl,readonly",
    "--mount", "type=bind,source=$out,target=/run",
    "--mount", "type=bind,source=$staged,target=/run/input/samples.jsonl,readonly",
    "--env", "BIGCODEBENCH_OVERRIDE_PATH=/workspace/reproducibility/data/bigcodebench-v0.1.4.jsonl",
    "--env", "NLTK_DATA=/opt/nltk_data",
    "--entrypoint", "python", $imageId, "-m", "bigcodebench.evaluate", "instruct", "full",
    "--samples", "/run/input/samples.jsonl", "--execution", "local",
    "--selective_evaluate", $selected, "--calibrated", "False", "--parallel", "2",
    "--no_gt", "True", "--save_pass_rate", "False", "--min_time_limit", "0.1",
    "--max_as_limit", "30720", "--max_data_limit", "30720", "--max_stack_limit", "10"
)

$metadata = [ordered]@{
    schema = "bcb-dev40-controls-v1"
    kind = $Kind
    image_id = $imageId
    base_image_id = $baseImageId
    upstream_commit_expected = $expectedCommit
    upstream_commit_verified = $actualCommit
    selected_ids = $ids
    cli_split = "instruct"
    dataset_partition = "development (40 seeded IDs)"
    prepared_split_sha256 = Hash $prepared
    samples_source_sha256 = Hash $samples
    staged_samples_sha256 = Hash $staged
    official_dev40_dataset_sha256 = Hash $dataset
    network = "none"
    argv = $taskDockerArgs
    process_limits = @{ memory = "3g"; pids = 256; cpus = 2 }
    provenance = $provenance
}
$metadata | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")

$freezeArgs = @("--context", "default", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65532:65532", "--entrypoint", "python", $imageId, "-m", "pip", "freeze")
& docker @freezeArgs 1> (Join-Path $out "pip-freeze.txt") 2> (Join-Path $out "pip-freeze.stderr.log")
if ($LASTEXITCODE -ne 0) { throw "Could not capture pip freeze" }
$metadata.package_freeze_sha256 = Hash (Join-Path $out "pip-freeze.txt")
$resourceArgs = @("--context", "default", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65532:65532", "--entrypoint", "sh", $imageId, "-c", "find /opt/nltk_data -type f -print0 | sort -z | xargs -0 sha256sum")
& docker @resourceArgs 1> (Join-Path $out "nltk-resources-sha256.txt") 2> (Join-Path $out "nltk-resources-sha256.stderr.log")
if ($LASTEXITCODE -ne 0) { throw "Could not capture NLTK resource hashes" }
$metadata.nltk_resources_sha256 = Hash (Join-Path $out "nltk-resources-sha256.txt")
$metadata | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")

& docker @taskDockerArgs 1> (Join-Path $out "stdout.log") 2> (Join-Path $out "stderr.log")
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) { throw "Control evaluator failed with exit code $exitCode; see stderr.log" }
if ((Hash $staged) -ne $metadata.samples_source_sha256) { throw "Staged samples changed during evaluation" }
$metadata.post_evaluator_staged_samples_sha256 = Hash $staged
$metadata | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 (Join-Path $out "run-metadata.json")
exit 0
