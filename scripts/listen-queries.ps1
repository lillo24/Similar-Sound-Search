param([string]$Report = 'reports/local/b03-report.json', [int]$Port = 8769)
$ErrorActionPreference = 'Stop'
$b03Root = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $b03Root
try {
    $b03SummaryPath = [IO.Path]::GetFullPath((Join-Path $b03Root $Report))
    $b03ReportsRoot = [IO.Path]::GetFullPath((Join-Path $b03Root 'reports/local'))
    if (-not $b03SummaryPath.StartsWith($b03ReportsRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Select an owned JSON report under reports/local'
    }
    if (-not (Test-Path -LiteralPath $b03SummaryPath -PathType Leaf)) { throw 'B03 report missing: see docs/QUERIES.md' }
    if ((Get-Item -LiteralPath $b03SummaryPath).Length -gt 1MB) { throw 'Report exceeds 1 MiB' }
    $b03Summary = Get-Content -LiteralPath $b03SummaryPath -Raw | ConvertFrom-Json
    if ($b03Summary.status -ne 'ok' -or $b03Summary.report -notmatch '^reports/local/b03/queries-[0-9a-f]{64}/index\.html$') {
        throw 'Expected successful B03 summary and owned bundle path'
    }
    & .\.venv\Scripts\python.exe -m similar_sound_search --tier starter queries serve $b03Summary.report --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'B03 report verification/server failed' }
} finally { Pop-Location }
