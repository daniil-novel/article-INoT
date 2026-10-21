param([string]$TexBin = '')
$ErrorActionPreference = 'Stop'
if (-not $TexBin) {
    $texCommand = Get-Command pdflatex -ErrorAction SilentlyContinue
    if ($texCommand) {
        $TexBin = Split-Path -Parent $texCommand.Source
    } else {
        $TexBin = Join-Path $env:LOCALAPPDATA 'Programs\MiKTeX\miktex\bin\x64'
    }
}
$pdfLatex = Join-Path $TexBin 'pdflatex.exe'
$bibTex = Join-Path $TexBin 'bibtex.exe'
if (-not (Test-Path -LiteralPath $pdfLatex) -or -not (Test-Path -LiteralPath $bibTex)) {
    throw 'Provide a TeX installation directory with -TexBin, or put pdflatex and bibtex on PATH.'
}
Push-Location -LiteralPath (Join-Path $PSScriptRoot 'manuscript')
try {
    & $pdfLatex -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'First LaTeX pass failed.' }
    & $bibTex main
    if ($LASTEXITCODE -ne 0) { throw 'Bibliography pass failed.' }
    1..2 | ForEach-Object {
        & $pdfLatex -interaction=nonstopmode -halt-on-error main.tex
        if ($LASTEXITCODE -ne 0) { throw 'Final LaTeX pass failed.' }
    }
    Write-Output 'Built manuscript/main.pdf from the matching source files.'
} finally {
    Pop-Location
}
