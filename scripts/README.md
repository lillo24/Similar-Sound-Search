# Local setup

`setup.ps1` owns Windows project-local environment creation and installation from the complete pinned `requirements.lock`, followed by an editable install and dependency check. It reuses an existing Python 3.12 `.venv`, never clears it, and fails on an incompatible interpreter or installation error. Pip's cache stays in ignored `.cache/pip/`.

Pass a working interpreter with `-PythonExecutable` when `python` is a Windows Store alias. [RUNTIME.md](../docs/RUNTIME.md#setup) gives the exact setup and Linux equivalent; numerical libraries are used by the source package, while Ruff is only a validation tool.

`setup-models.ps1` owns the separate optional Windows AMD64/Python 3.12 CPU inference setup. It downloads only the hash-pinned wheel closure from `requirements-models.lock`, reuses root setuptools/numerical packages, checks finite wheel space/free headroom and dependency consistency, and refuses renderer identity changes. It never downloads a checkpoint. [MATCHERS.md](../docs/MATCHERS.md) gives explicit acquisition/inference commands and platform limits; ordinary setup/smoke remain independent of models.

`listen-search.ps1` opens an already generated A06 bundle through its loopback-only
allowlisted server, using the successful private report summary (default
`reports/local/a06-demo-report.json`). It performs no indexing/inference and stops with
Ctrl+C. Optional `-Report` stays within `reports/local`; `-Port` defaults to 8766. Stop
console commands/server processes before reinstalling the Windows launcher.

`listen-events.ps1` similarly opens the verified B01 event bundle and its separate
single/multiple search pages (default `reports/local/b01-event-report.json`, port
8767). It does no inference or ledger reset; [EVENTS.md](../docs/EVENTS.md) owns the
finite proposal/selection/extraction/comparison commands.

## B02 comparison listener

`listen-separation.ps1` validates the successful owned B02 summary, then starts the
hash-verified loopback listener on 8768. Ctrl+C stops it. Existing B01/A06 listeners
retain 8767/8766. The private media remain in the delivery checkout.
