# Local setup

`setup.ps1` owns Windows project-local environment creation and installation from the complete pinned `requirements.lock`, followed by an editable install and dependency check. It reuses an existing Python 3.12 `.venv`, never clears it, and fails on an incompatible interpreter or installation error. Pip's cache stays in ignored `.cache/pip/`.

Pass a working interpreter with `-PythonExecutable` when `python` is a Windows Store alias. [RUNTIME.md](../docs/RUNTIME.md#setup) gives the exact setup and Linux equivalent; numerical libraries are used by the source package, while Ruff is only a validation tool.

`setup-models.ps1` owns the separate optional Windows AMD64/Python 3.12 CPU inference setup. It downloads only the hash-pinned wheel closure from `requirements-models.lock`, reuses root setuptools/numerical packages, checks finite wheel space/free headroom and dependency consistency, and refuses renderer identity changes. It never downloads a checkpoint. [MATCHERS.md](../docs/MATCHERS.md) gives explicit acquisition/inference commands and platform limits; ordinary setup/smoke remain independent of models.
