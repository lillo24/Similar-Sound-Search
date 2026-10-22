param([string]$Report = 'reports/local/c03/report-command.json', [int]$Port = 8772)
$ErrorActionPreference = 'Stop'
$c03Root = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $c03Root
try {
    $c03SummaryPath = [IO.Path]::GetFullPath((Join-Path $c03Root $Report))
    $c03ReportsRoot = [IO.Path]::GetFullPath((Join-Path $c03Root 'reports/local/c03'))
    if (-not $c03SummaryPath.StartsWith($c03ReportsRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Select an owned JSON summary under reports/local/c03'
    }
    if (-not (Test-Path -LiteralPath $c03SummaryPath -PathType Leaf)) { throw 'C03 report missing: see docs/REFINEMENT.md' }
    if ((Get-Item -LiteralPath $c03SummaryPath).Length -gt 1MB) { throw 'Report exceeds 1 MiB' }
    $c03Summary = Get-Content -LiteralPath $c03SummaryPath -Raw | ConvertFrom-Json
    if ($c03Summary.status -ne 'ok' -or $c03Summary.report -notmatch '^reports/local/c03/refinement-[0-9a-f]{64}/index\.html$') {
        throw 'Expected successful C03 summary and owned bundle path'
    }
    & .\.venv\Scripts\python.exe -m similar_sound_search --tier starter refinement serve $c03Summary.report --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'C03 report verification/server failed' }
} finally { Pop-Location }
