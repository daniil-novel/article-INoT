$scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "build.ps1"
powershell -ExecutionPolicy Bypass -File $scriptPath en
exit $LASTEXITCODE
