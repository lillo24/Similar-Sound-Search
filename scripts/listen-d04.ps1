param([int]$Port = 8777)
$ErrorActionPreference = 'Stop'
$d04Project = Split-Path -Parent $PSScriptRoot
$d04Output = Join-Path $d04Project 'reports/local/d04'
$d04Config = Join-Path $d04Output 'metadata/launch.json'
if (-not (Test-Path -LiteralPath $d04Config -PathType Leaf)) {
    throw 'The private D04 review is missing. See docs/LISTENING.md for exact prerequisites; do not create a new allocation.'
}
if ((Get-Item -LiteralPath $d04Config).Length -gt 64KB) { throw 'Invalid D04 launch config size' }
$d04Python = (Get-Content -LiteralPath $d04Config -Raw -Encoding UTF8 | ConvertFrom-Json).python
if (-not (Test-Path -LiteralPath $d04Python -PathType Leaf)) {
    throw 'The configured installed D03 interpreter is missing. Restore its original path; see docs/LISTENING.md.'
}
& $d04Python -I -B (Join-Path $PSScriptRoot 'd04-review.py') serve --root $d04Output --port $Port
if ($LASTEXITCODE -ne 0) { throw 'D04 review failed; retain the error and private evidence' }
