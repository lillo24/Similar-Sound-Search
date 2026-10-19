param([string]$Report = 'reports/local/b01-event-report.json', [int]$Port = 8767)
$ErrorActionPreference = 'Stop'
$b01Root = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $b01Root
try {
    $b01SummaryPath = [IO.Path]::GetFullPath((Join-Path $b01Root $Report))
    $b01ReportsRoot = [IO.Path]::GetFullPath((Join-Path $b01Root 'reports/local'))
    if (-not $b01SummaryPath.StartsWith($b01ReportsRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Select an owned JSON report under reports/local'
    }
    if (-not (Test-Path -LiteralPath $b01SummaryPath -PathType Leaf)) {
        throw 'Event report missing: run the B01 commands in docs/EVENTS.md'
    }
    if ((Get-Item -LiteralPath $b01SummaryPath).Length -gt 1MB) { throw 'Report exceeds 1 MiB' }
    $b01Summary = Get-Content -LiteralPath $b01SummaryPath -Raw | ConvertFrom-Json
    if ($b01Summary.status -ne 'ok' -or $b01Summary.report -notmatch '^reports/local/b01/events-[0-9a-f]{64}/index\.html$') {
        throw 'Expected successful B01 event report summary and owned bundle path'
    }
    & .\.venv\Scripts\python.exe -m similar_sound_search --tier starter events serve $b01Summary.report --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Event report verification/server failed' }
} finally { Pop-Location }
