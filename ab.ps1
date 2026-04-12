$scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "build.ps1"
powershell -ExecutionPolicy Bypass -File $scriptPath @args
exit $LASTEXITCODE
