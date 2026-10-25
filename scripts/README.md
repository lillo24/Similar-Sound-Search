# Local setup

`listen-d04.ps1` opens the private, reference-first D04 review using the existing
installed interpreter. `d04-review.py` prepares only verified saved clips or serves
the separate stdlib companion; [its subsystem map](listening_review/README.md)
separates immutable input, feedback, playback and preservation responsibilities.
`d04-check.py` records the finite D04-only preparation allowance; it cannot refill
an application pool. See [LISTENING.md](../docs/LISTENING.md) for launch, feedback,
resource boundaries and missing-private-artifact prerequisites.

`build-distribution.py` builds the D03 non-editable wheel, copies the exact cached
18-wheel dependency closure, inventories public configuration/notices and emits a
versioned offline archive. It uses the retained private cache-location inventory
from delivery authoring; public wheel identities live in `manifests/distribution/dependencies.json`.
`declare-distribution-consumer.py` prospectively freezes the exact core/adapter/UI
maps, checks unchanged AST outside declared provider boundaries and retains scoped
persistence/HTTP repair predecessors. Neither script initializes another runtime
allowance. [PACKAGE.md](../docs/PACKAGE.md) owns the installed product workflow.
`export-distribution-evidence.py --workspace <private-root>` reads retained local
acceptance receipts and exports sanitized `reports/D03_PACKAGE.json`. It validates
complete native/browser/preservation evidence and unspent normal capacity; it never
dispatches inference or initializes state. The narrative report records the exact
scope of the installed artifact iterations.

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

`declare-processing-consumer.py` pins/proves the classified C04 consumer before
inference and refuses an existing declaration. `exercise-processing.py` runs the
finite fixture/clean and historical/warm sequence in one pool.
`exercise-processing-recovery.py` terminates only its own tracked real worker after
durable commit, resumes and clean-checks it. `verify-processing-preservation.py
capture|verify` checks earlier bytes including denied staging; only exact C04 config
navigation is allowed. `listen-processing.ps1` resolves a completed C04 job to
preserved C03 playback on foreground loopback 8773.

`declare-processing-repair.py` is the one explicit correctness-repair proof,
preserving the initial consumer and all spent work; it refuses an existing repair.

`declare-processing-metadata-compatibility.py` pins the exact metadata-only upgrade
and unchanged numerical/reservation proofs. It permits the same paused plan to
resume under the declared new consumer, without replacing old records or charges.

`export-processing-evidence.py` reads retained records for static public reporting;
it dispatches no work and cannot settle/replenish the exhausted pool. Real C04
finalization is partial; `listen-processing.ps1` has no completed warm real job.
Use preserved C03 playback until a newly authorized owner repairs/finalizes the chain.

## D01 application

`start-sound-search.ps1` runs the local app on 8774 in the foreground using the
existing pinned environment; Ctrl+C stops admission and waits for its own worker.
`application-worker.py` is the explicit actual-PID worker boundary.
`exercise-application.py` drives the predeclared adoption/warm/native acceptance
sequence against the one D01 pool; completed delivery actions must not be rerun to
reset evidence or budgets. HTTP/browser QA is separately retained under ignored
`reports/local/d01/` and does not substitute for native verification.

`declare-application-*.py` are exact one-shot source/AST compatibility declarations
for the retained repair history, preserving old producers and failing on unexpected
drift. `admit-application-*-finalization.py` admit only an enumerated remaining path
from the same fixed pool after a recorded metadata block; neither resets a limit.
`verify-application-preservation.py capture|verify` refuses to replace its baseline
and checks all earlier artifacts/configuration, including the retained C01 staging.
`export-application-evidence.py` reads completed records into the typed public D01
summary, refuses missing/failed QA and strips paths/tokens/audio. It dispatches no
workers, settles no attempts and cannot reset the finite allowance.

## D02 automatic evaluation

`freeze-evaluation-protocol.py` is the one-shot prospective matrix/config writer.
`declare-evaluation-consumer.py` pins the five product seams, unchanged numerical
map, separate evaluation source map and two-source cold/reuse pilot.
`evaluation-worker.py` is the actual-PID boundary for
`python -m sound_search_evaluation`; it reports failures and never retries.
`verify-evaluation-preservation.py capture|verify` compares every old artifact,
including denied C01 staging, and permits only new immutable shared preparation.
See [ASSESSMENT.md](../docs/ASSESSMENT.md) for commands and finite replay rules.

`declare-evaluation-inventory-repair.py` archives the exact first D02 declaration
and pins the pre-inference fresh-scan/publication/storage repair. It refuses to
run after any feature encoding or query-policy claim. `verify-assessment-bytes.py`
independently hashes every emitted source/reference against its recorded bytes;
its additional reads and metadata are charged to D02 without changing originals.

`declare-evaluation-publication-repair.py` pins the pre-inference record-owner
placement fix, preserving previous consumers. `admit-evaluation-remaining.py`
checks exact cold/reuse pilot outcomes and records the remaining-path forecast;
actual pool guards remain authoritative and no ceiling is increased.

`declare-evaluation-membership-repair.py` pins genuine PCM-alias membership IDs;
`declare-evaluation-storage-repair.py` pins lossless bounded metadata packing.
Both preserve earlier producers, numerical values and retained failure evidence.
`declare-evaluation-layout.py` proves the two CSS-only mobile fixes and unchanged
player code. `admit-evaluation-metadata.py` reserves measured development space;
`admit-evaluation-confirmation.py` releases only completed preparation's unspent
reservation and reserves the measured confirmation remainder within the same cap.
`freeze-evaluation-candidate.py` pins the unchanged candidate and development gate
before confirmation. `export-evaluation-evidence.py` reads saved assessments and
verified acceptance/preservation evidence into the sanitized public JSON; it performs
no inference, settlement, ledger reset or historical mutation.
