param([int]$Port = 8774)
$ErrorActionPreference = "Stop"
$d01Root = Split-Path -Parent $PSScriptRoot
$d01Python = Join-Path $d01Root ".venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $d01Python)) {
    throw "Missing .venv: follow README setup with the pinned Python 3.12 runtime first."
}
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:PYTHONIOENCODING = "utf-8"
Push-Location $d01Root
try {
    & $d01Python -m similar_sound_search.application --root $d01Root --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Sound Search stopped with a startup/runtime error." }
} finally {
    Pop-Location
}
