param([string]$TeXBin = '')
$ErrorActionPreference = 'Stop'
if (-not $TeXBin) {
    $found = Get-Command pdflatex -ErrorAction SilentlyContinue
    if ($found) { $TeXBin = Split-Path $found.Source }
    else { $TeXBin = Join-Path $env:LOCALAPPDATA 'Programs\MiKTeX\miktex\bin\x64' }
}
$pdf = Join-Path $TeXBin 'pdflatex.exe'
$bib = Join-Path $TeXBin 'bibtex.exe'
if (-not (Test-Path -LiteralPath $pdf) -or -not (Test-Path -LiteralPath $bib)) {
    throw 'A standard LaTeX installation with pdflatex and BibTeX is required.'
}
Push-Location (Join-Path $PSScriptRoot 'manuscript')
try {
    & $pdf -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE) { throw 'First LaTeX pass failed.' }
    & $bib main
    if ($LASTEXITCODE) { throw 'BibTeX pass failed.' }
    & $pdf -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE) { throw 'Second LaTeX pass failed.' }
    & $pdf -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE) { throw 'Final LaTeX pass failed.' }
} finally { Pop-Location }
