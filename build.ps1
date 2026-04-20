param(
  [ValidateSet("ru", "en", "all", "clean", "help")]
  [string]$Target = "ru"
)

$latexmk = "C:\Users\GF62\AppData\Local\Programs\MiKTeX\miktex\bin\x64\latexmk.exe"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location -LiteralPath $repoRoot

if (-not (Test-Path -LiteralPath $latexmk)) {
  Write-Error "latexmk.exe not found at $latexmk"
  exit 1
}

function Show-Usage {
  Write-Host "Usage:"
  Write-Host "  .\build.ps1 ru     Build Russian version"
  Write-Host "  .\build.ps1 en     Build English version"
  Write-Host "  .\build.ps1 all    Build both versions"
  Write-Host "  .\build.ps1 clean  Remove LaTeX build artifacts"
  Write-Host "  .\build.ps1 help   Show this help"
}

function Invoke-Build([string]$TexFile) {
  # -f keeps latexmk going through pdflatex's non-fatal exit codes (e.g.
  # undefined references/citations on the first pass), so embedded
  # \begin{thebibliography} gets resolved across the 2-3 passes latexmk
  # runs automatically. Without -f the first pdflatex exit code 1 would
  # abort the whole build before references stabilise.
  & $latexmk `
    -synctex=1 `
    -interaction=nonstopmode `
    -file-line-error `
    -pdf `
    -f `
    $TexFile

  # Treat "finished with errors but produced pdf" (exit 12 from latexmk
  # under -f) as a soft failure only when the PDF is actually missing.
  $pdfName = [IO.Path]::ChangeExtension($TexFile, ".pdf")
  if (-not (Test-Path -LiteralPath $pdfName)) {
    exit $LASTEXITCODE
  }
}

function Remove-Artifacts {
  $patterns = @(
    "*.aux",
    "*.fdb_latexmk",
    "*.fls",
    "*.log",
    "*.out",
    "*.synctex.gz"
  )

  Get-ChildItem -LiteralPath $repoRoot -File | Where-Object {
    $name = $_.Name
    ($patterns | Where-Object { $name -like $_ }).Count -gt 0
  } | Remove-Item -Force

  $pdfs = @(
    "converted_article_springer.pdf",
    "converted_article_springer_ru.pdf"
  )

  foreach ($pdf in $pdfs) {
    if (Test-Path -LiteralPath $pdf) {
      Remove-Item -LiteralPath $pdf -Force
    }
  }

  Write-Host "LaTeX build artifacts removed."
}

switch ($Target) {
  "ru" {
    Invoke-Build "converted_article_springer_ru.tex"
  }
  "en" {
    Invoke-Build "converted_article_springer.tex"
  }
  "all" {
    Invoke-Build "converted_article_springer.tex"
    Invoke-Build "converted_article_springer_ru.tex"
  }
  "clean" {
    Remove-Artifacts
  }
  "help" {
    Show-Usage
  }
}

exit 0
