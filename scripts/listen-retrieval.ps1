param([string]$Report = 'reports/local/c02/report-command.json', [int]$Port = 8771)
$ErrorActionPreference = 'Stop'
$c02Root = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $c02Root
try {
    $c02SummaryPath = [IO.Path]::GetFullPath((Join-Path $c02Root $Report))
    $c02ReportsRoot = [IO.Path]::GetFullPath((Join-Path $c02Root 'reports/local/c02'))
    if (-not $c02SummaryPath.StartsWith($c02ReportsRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Select an owned JSON summary under reports/local/c02'
    }
    if (-not (Test-Path -LiteralPath $c02SummaryPath -PathType Leaf)) { throw 'C02 report missing: see docs/RETRIEVAL.md' }
    if ((Get-Item -LiteralPath $c02SummaryPath).Length -gt 1MB) { throw 'Report exceeds 1 MiB' }
    $c02Summary = Get-Content -LiteralPath $c02SummaryPath -Raw | ConvertFrom-Json
    if ($c02Summary.status -ne 'ok' -or $c02Summary.report -notmatch '^reports/local/c02/retrieval-[0-9a-f]{64}/index\.html$') {
        throw 'Expected successful C02 summary and owned bundle path'
    }
    & .\.venv\Scripts\python.exe -m similar_sound_search --tier starter retrieval serve $c02Summary.report --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'C02 report verification/server failed' }
} finally { Pop-Location }
