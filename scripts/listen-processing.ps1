param([string]$Job = '', [int]$Port = 8773)
$ErrorActionPreference = 'Stop'
$processingRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $processingRoot
try {
    if ($Job -eq '') {
        $processingSummary = Get-Content -LiteralPath 'reports/local/c04/historical-warm.json' -Raw | ConvertFrom-Json
        if ($processingSummary.status -ne 'ok' -or $processingSummary.state -ne 'complete') {
            throw 'Complete the explicit C04 historical warm job first; see docs/PROCESSING.md'
        }
        $Job = $processingSummary.job.path
    }
    & .\.venv\Scripts\python.exe -m similar_sound_search --tier starter processing serve $Job --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'C04 completed-job/result/playback verification failed' }
} finally { Pop-Location }
