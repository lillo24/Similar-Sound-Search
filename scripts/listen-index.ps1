param([string]$Report = 'reports/local/c01/report-command.json', [int]$Port = 8770)
$ErrorActionPreference = 'Stop'
$c01Root = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $c01Root
try {
    $c01SummaryPath = [IO.Path]::GetFullPath((Join-Path $c01Root $Report))
    $c01ReportsRoot = [IO.Path]::GetFullPath((Join-Path $c01Root 'reports/local'))
    if (-not $c01SummaryPath.StartsWith($c01ReportsRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Select an owned JSON report under reports/local'
    }
    if (-not (Test-Path -LiteralPath $c01SummaryPath -PathType Leaf)) { throw 'C01 report missing: see docs/INDEXING.md' }
    if ((Get-Item -LiteralPath $c01SummaryPath).Length -gt 1MB) { throw 'Report exceeds 1 MiB' }
    $c01Summary = Get-Content -LiteralPath $c01SummaryPath -Raw | ConvertFrom-Json
    if ($c01Summary.status -ne 'ok' -or $c01Summary.report -notmatch '^reports/local/c01/index-[0-9a-f]{64}/index\.html$') {
        throw 'Expected successful C01 summary and owned bundle path'
    }
    & .\.venv\Scripts\python.exe -m similar_sound_search --tier starter indexing serve $c01Summary.report --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'C01 report verification/server failed' }
} finally { Pop-Location }
