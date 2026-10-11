# Local setup

`setup.ps1` owns Windows project-local environment creation and installation from the complete pinned `requirements.lock`, followed by an editable install and dependency check. It reuses an existing Python 3.12 `.venv`, never clears it, and fails on an incompatible interpreter or installation error. Pip's cache stays in ignored `.cache/pip/`.

Pass a working interpreter with `-PythonExecutable` when `python` is a Windows Store alias. [RUNTIME.md](../docs/RUNTIME.md#setup) gives the exact setup and Linux equivalent; numerical libraries are used by the source package, while Ruff is only a validation tool.
