param([string]$Report = 'reports/local/a06-demo-report.json', [int]$Port = 8766)
$ErrorActionPreference = 'Stop'
$a06Root = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $a06Root
try {
    $a06SummaryPath = [IO.Path]::GetFullPath((Join-Path $a06Root $Report))
    $a06ReportsRoot = [IO.Path]::GetFullPath((Join-Path $a06Root 'reports/local'))
    if (-not $a06SummaryPath.StartsWith($a06ReportsRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Select an owned JSON report under reports/local'
    }
    if (-not (Test-Path -LiteralPath $a06SummaryPath -PathType Leaf)) {
        throw 'Listening report missing: run the index/query/rank/report commands in docs/SEARCH.md'
    }
    if ((Get-Item -LiteralPath $a06SummaryPath).Length -gt 1MB) { throw 'Report exceeds 1 MiB' }
    $a06Summary = Get-Content -LiteralPath $a06SummaryPath -Raw | ConvertFrom-Json
    if ($a06Summary.status -ne 'ok' -or $a06Summary.report -notmatch '^reports/local/a06/[0-9a-f]{64}/index\.html$') {
        throw 'Expected a successful A06 report summary and owned bundle path'
    }
    & .\.venv\Scripts\python.exe -m similar_sound_search --tier starter search serve $a06Summary.report --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Report verification/server failed; inspect the displayed error' }
} finally { Pop-Location }
