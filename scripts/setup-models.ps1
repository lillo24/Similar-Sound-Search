param([string]$PythonExecutable = '.\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
$a05Root = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $a05Root
try {
    $a05Platform = & $PythonExecutable -c "import platform,sys; print(platform.system(),platform.machine(),sys.version_info.minor)"
    if ($LASTEXITCODE -ne 0 -or $a05Platform -ne 'Windows AMD64 12') { throw 'Optional lock is exercised for Windows AMD64 / Python 3.12 only' }
    $a05Before = & $PythonExecutable -c "from similar_sound_search.preparation import versions; import json; print(json.dumps(versions(),sort_keys=True))"
    if ($LASTEXITCODE -ne 0) { throw 'Run ordinary setup first' }
    $a05Wheels = Join-Path $a05Root 'data/models/dependencies'
    New-Item -ItemType Directory -Force -Path $a05Wheels | Out-Null
    # The ten reviewed wheel hashes bound this finite install; no model is fetched.
    $a05Free = (Get-PSDrive -Name ([IO.Path]::GetPathRoot($a05Root).Substring(0,1))).Free
    if ($a05Free -lt 6GB) { throw 'Optional setup needs 6 GiB free before downloads/unpacking' }
    # Every missing transitive package is pinned here. setuptools is already supplied
    # by ordinary setup; the CPU wheel index does not carry its required root version.
    & $PythonExecutable -m pip --cache-dir .cache/pip download --no-deps --only-binary=:all: --require-hashes --dest $a05Wheels -r requirements-models.lock
    if ($LASTEXITCODE -ne 0) { throw 'Pinned optional wheel download failed' }
    $a05Bytes = (Get-ChildItem -LiteralPath $a05Wheels -File | Measure-Object -Property Length -Sum).Sum
    if ($a05Bytes -gt 512MB) { throw 'Optional dependency wheel allowance exceeds 512 MiB' }
    & $PythonExecutable -m pip --cache-dir .cache/pip install --no-deps --no-index --find-links $a05Wheels --require-hashes -r requirements-models.lock
    if ($LASTEXITCODE -ne 0) { throw 'Pinned optional dependency installation failed' }
    & $PythonExecutable -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Optional dependency consistency failed' }
    $a05After = & $PythonExecutable -c "from similar_sound_search.preparation import versions; import json; print(json.dumps(versions(),sort_keys=True))"
    if ($LASTEXITCODE -ne 0 -or $a05After -ne $a05Before) { throw 'Optional install changed renderer tool identity' }
    Write-Output "Optional wheel bytes: $a05Bytes; renderer identity unchanged. No checkpoint downloaded."
} finally { Pop-Location }
