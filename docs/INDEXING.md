# C01 passage banks

C01 owns bank plans, bounded row publication, immutable snapshots and exact
per-bank verification. `indexing/` composes the existing native grid, frozen
representation, source validation and array primitives. A06 remains a read-only
reference, requiring a fresh C01-charged `events.compatibility` receipt. Original
audio and pitch off remain defaults. C02 owns aggregation across banks/events.

The committed `manifests/indexing/protocol.json` is the prospective declaration.
The one ten-case development batch uses a common .5s hop. Production candidates
1.2s/.5s and 4.8s/1s change duration and sampling opportunities together. The
admission rule first protects source consistency, then prefers complete event
support, with measured cost breaking ties. It may admit neither. Containment,
IoU and boundary errors are separate quantities.

All new work uses `config/indexing.json` and one cumulative C01 ledger. Fixed
roots are `data/indexes/c01`, `data/features/indexing`, `data/runs/indexing`,
`data/audio/indexing`, `manifests/indexing` and `reports/local/c01`. Existing
queries, transformations and legacy shards are read-only dependencies. Missing
query materialization requires an explicit C01 derivative, never a B03 worker.

Rows describe half-open native samples: duration rounds up, hop rounds to nearest
frame (half up), and a unique end-aligned tail preserves the last real sample.
Short files yield one short supported row; model padding is never source support.
Coverage is an interval union per original/bank, and once per original across
banks. Component regions stay discontinuous, partial and experimental. Broad HPSS
uses no cue samples even when its historical receipt records one; provenance and
exclusions are retained. Guided outputs consume a cue and cannot be generic
components. Component hits play the original mixture; component audition is a
separately labelled option.

Commands, measured outcomes and the C02 handoff are recorded in
`reports/C01_INDEX.md`. No new model, dependency, acquisition or held-out run is
part of this stage.

Run from the checkout in PowerShell with `.venv/Scripts/python.exe`. Numerical
threads are forced to one in each CLI child. Every indexing action except the
idle listener uses the same C01 ledger; changing names/restarting does not grant
more work. `--tier starter` retains 120s, 1 GiB working, 256 MiB decoded/output,
4 GiB combined managed storage and 4 GiB free-space headroom. New roots are in the
shared inventory. A configured allocation bound is distinct from Windows commit
availability; preflight records both, and the pilot measures actual worker peaks.

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.venv/Scripts/python.exe scripts/verify-index-preservation.py capture
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing preflight
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing known-answer
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing generate
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing geometry
```

Read `data/runs/indexing/preflight.json` for the two immutable real plan paths and
`data/runs/indexing/development/fixtures.json` for the three development plan
paths. Build each development plan with `indexing build PLAN --scope full`, then:

```powershell
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing build --bank short --scope pilot
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing verify --bank short --scope pilot
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing build --bank long --scope pilot
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing verify --bank long --scope pilot
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing compare
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing admit
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing components
```

Build each explicit component plan from `data/runs/indexing/components.json` with
`indexing build PLAN --scope full`. Build only the admitted original policy from
`admission.json` with `indexing build --bank LABEL --scope full`; repeat this exact
command to resume. Valid committed arrays are retained, validated recoverable
orphans need no re-embedding, and corrupt arrays are refused. Failed attempts and
their reservations remain visible. Once complete, repeating the build performs
the same single charged reuse pass as `indexing verify --bank LABEL --scope full`.
Choose either command for that pass; a completed reuse refuses an undeclared repeat.

```powershell
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing compatibility
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing snapshot --receipt RECEIPT
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing search LEGACY_BANK
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing search ADMITTED_BANK
.venv/Scripts/python.exe -m similar_sound_search --tier starter --report reports/local/c01/report-command.json indexing report
.venv/Scripts/python.exe -m similar_sound_search --tier starter indexing verify-native
.venv/Scripts/python.exe scripts/verify-index-preservation.py verify
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/listen-index.ps1
```

Use the exact receipt returned by compatibility and bank paths returned by
snapshot. The default revision/materialization is the committed original Loulou
revision, never a mutable library head. `--revision HASH --materialization HASH`
selects another explicit saved materialization. `--allow-partial` makes partial
coverage intentional and visible. `indexing derive-query --revision HASH` is the
explicit missing-materialization path; `indexing search BANK --revision HASH
--derived` reads that derivative. It imports the validated recipe and bindings,
uses C01-owned cache/output paths, and charges its unchanged pitch metadata
estimator within C01's processing-audio allowance; verification scoring stays off.

Metadata writes are bounded by a 32 MiB counted subcap inside a pre-reserved 32 MiB
managed envelope. Arrays, preparations, transforms and clips reserve separate
output before work. Actual final namespace bytes are also reported. Files left by
failed attempts remain charged and are not treated as ready membership.

Snapshots store compact immutable shard/membership hashes, resolved by the C01
reader to exact native row bounds. This preserves the shared 1 MiB metadata-reader
limit. Ranking progress similarly references immutable complete group winners;
final executions still include all eligible winners, not only ten candidates.
Bank/query representations must match exactly, and the unchanged frozen-function
consumer audit runs before scoring. C01 summary paths are contained under
`reports/local/c01`, including an explicit `--report` path.

C02 now consumes these exact historical banks through an explicit read-only
membership/configuration view and a fresh C02-owned legacy receipt. It preserves
this snapshot and exports bounded support/shortlist evidence; see
[RETRIEVAL.md](RETRIEVAL.md). C01 workers and its closed allowance are not reopened.
