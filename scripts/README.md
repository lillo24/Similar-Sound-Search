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

`verify-separation.py` independently checks B02 native-to-PCM16 samples, conversion
receipts, gain and numeric player/source timestamps. It uses the same fixed B02 ledger,
locks and 120s deadline, with source reads charged. It does not load a model or access
the network. Its default input is `reports/local/b02-report.json`.

`listen-queries.ps1` validates the B03 summary and serves its hash-verified revision/
pitch comparison on loopback 8769; Ctrl+C stops it. Native verification is the charged
`queries verify-native` CLI operation. Earlier listeners retain their separate ports.

`verify-query-geometry.py` independently audits B03's saved source hashes, nonzero
insertions, native support, silence/control flags and generator frequency/family truth
before matcher/comparison inference. It uses SoundFile/FFT/projections rather than the
operational estimator, under the fixed B03 ledger, offline lock and 120s worker bound.
Its source hash identifies the producing LF snapshot; Git may use native checkout
line endings later. Both retained audit passes remain charged in the same ledger.

`listen-index.ps1` validates the C01 report summary and serves the verified new
bundle on loopback 8770. Earlier listeners retain 8766–8769. Native verification is
`indexing verify-native`; media/HTML serving uses the existing exact allowlist.
`verify-index-preservation.py capture|verify` inventories historical artifacts,
configs, frozen adapters, pitch module and the root reference MP3. It excludes only
the declared C01 roots and C01 lock. Capture refuses to overwrite its baseline.
Verification separately identifies the exact C01 navigation section appended to
`config/README.md`; every runtime JSON configuration remains byte-identical.

`verify-index-support.py` independently enumerates C01 full-2.4s containment from
the already-inspected native truth. It retains the closed batch, separates the
.3s short-file denominator and checks that admission is unchanged, with no new
features/scores/queries. Its offline 120s worker uses the same C01 ledger.

`listen-retrieval.ps1` serves the verified C02 bundle on owned loopback 8771; `verify-retrieval-preservation.py` verifies all prior delivery bytes, including C01 staging, allowing only the exact C02 configuration navigation addition.

`listen-refinement.ps1` starts verified C03 playback on loopback 8772. `verify-refinement-preservation.py` checks historical delivery bytes with only the exact C03 config navigation addition allowed.
