param([string]$Report = 'reports/local/b02-report.json', [int]$Port = 8768)
$ErrorActionPreference = 'Stop'
$b02Root = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $b02Root
try {
    $b02SummaryPath = [IO.Path]::GetFullPath((Join-Path $b02Root $Report))
    $b02ReportsRoot = [IO.Path]::GetFullPath((Join-Path $b02Root 'reports/local'))
    if (-not $b02SummaryPath.StartsWith($b02ReportsRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Select an owned JSON report under reports/local'
    }
    if (-not (Test-Path -LiteralPath $b02SummaryPath -PathType Leaf)) {
        throw 'B02 report missing: run the commands in docs/SEPARATION.md'
    }
    if ((Get-Item -LiteralPath $b02SummaryPath).Length -gt 1MB) { throw 'Report exceeds 1 MiB' }
    $b02Summary = Get-Content -LiteralPath $b02SummaryPath -Raw | ConvertFrom-Json
    if ($b02Summary.status -ne 'ok' -or $b02Summary.report -notmatch '^reports/local/b02/separation-[0-9a-f]{64}/index\.html$') {
        throw 'Expected successful B02 report summary and owned bundle path'
    }
    & .\.venv\Scripts\python.exe -m similar_sound_search --tier starter separation serve $b02Summary.report --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'B02 report verification/server failed' }
} finally { Pop-Location }
