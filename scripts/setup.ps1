param([string]$PythonExecutable = "python")
$ErrorActionPreference = "Stop"
$a02Root = Split-Path -Parent $PSScriptRoot
$a02Environment = Join-Path $a02Root ".venv"
$a02Python = Join-Path $a02Environment "Scripts/python.exe"
Push-Location $a02Root
try {
    if (-not (Test-Path -LiteralPath $a02Python)) {
        & $PythonExecutable -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 required'"
        if ($LASTEXITCODE -ne 0) { throw "Select a working Python 3.12 executable with -PythonExecutable (a Store alias is insufficient)." }
        & $PythonExecutable -m venv $a02Environment
        if ($LASTEXITCODE -ne 0) { throw "Could not create project .venv." }
    }
    & $a02Python -c "import sys; assert sys.version_info[:2] == (3, 12), 'Existing .venv must use Python 3.12'"
    if ($LASTEXITCODE -ne 0) { throw "Existing .venv is incompatible; choose a separate Python 3.12 environment." }
    & $a02Python -m pip --disable-pip-version-check --cache-dir .cache/pip install --only-binary=:all: -r requirements.lock
    if ($LASTEXITCODE -ne 0) { throw "Locked dependency installation failed." }
    & $a02Python -m pip --disable-pip-version-check --cache-dir .cache/pip install --no-deps --no-build-isolation -e .
    if ($LASTEXITCODE -ne 0) { throw "Editable project installation failed." }
    & $a02Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Dependency validation failed." }
} finally {
    Pop-Location
}
