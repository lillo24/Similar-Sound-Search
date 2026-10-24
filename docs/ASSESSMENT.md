# D02 automatic evaluation contract

D02 uses the separate `sound_search_evaluation` package and one fixed pool at
`data/runs/assessment/pool.json`. The case matrix in
`manifests/assessment/protocol.json` is prospective: 24 development and 16
confirmation queries, 32 generated recordings per split, 31 distinct groups after
one genuine duplicate, and at least 24 eligible groups for every primary query.
Independent performances, mixtures, short/edge/stereo support, multi-example
semantics, absent targets and exact-instance exclusion controls are distinct.

Baseline is original mixture / legacy mean / pitch off. The sole alternative is
the existing event-multi configuration, unchanged. No development-driven revision
is authorized by this protocol. A final candidate/gate is committed before the one
confirmation run. Familiar A04 renderer mechanisms are used with new parameters,
performances, backgrounds and seeds: this is prospective confirmation within
familiar mechanisms, not an untouched musical-source or human relevance test.

The owner adapts genuine generated population/index records to the production
query, score, fusion, result and playback paths. It does not forge C01 provenance.
Default historical app ownership/population and unsupported options remain fixed.
Truth and generator labels never enter retrieval inputs; neutral IDs, actual audio
metadata, native bounds, genuine parents and immutable memberships do.

Group hit and all-positive-group recall at 1/5/10/20 are distinct from one-to-one
event recovery, IoU, truth coverage and conditional boundary errors. Every true
event and every declared case remains in the denominator. Invalid predictions
fail validation. Absents report forced ranking rather than a fictional rejection
threshold; exact-copy controls test ancestry exclusion, not timbre generalization.

One D02 allowance has the prompt's unchanged hard ceilings. The `import_bytes`
counter covers all generated audio plus explicit controlled-reference uploads.
The metadata ceiling is 256 MiB, with 32 MiB protected for terminal bookkeeping.
Prepaid ordinary allocations are prepare 24, development 72, confirmation 56,
delivery 28 and report 12 MiB. Confirmation/delivery/report capacity is reserved
before development. Non-inference QA has at most 64 MiB within the 1 GiB managed
ceiling. No old pool can be written, reset or refunded.

Resource preflight and the small declared cold/reuse pilot precede comparative
scores. Source/model startup, full sequential reads, failed attempts, temporary
writes, amplification, journals and settlement remain charged. Workers retain
120-second actual-PID deadlines, 1 GiB numerical memory, 256 MiB I/O bounds,
one numerical thread/process and 4 GiB storage/free-space headroom. The report
separates pure tests and non-inference QA from charged real-model evaluation.

The three controlled product cases are development ordinals 0, 16 and 20 (positive,
multi-example and absent). Both policies belong to the initial 48 development
executions; identical predictions may be reused by the batch. At most eight further
technical query-policy replays may verify agreement/invariance, never tune quality.
Product media is capped at 60 scored/context clips for these cases, one reference
preview, and two clips for the first predeclared baseline failure example.

The historical D01 results remain readable on 8774 and C03 on 8772. Another complete
search does not fit D01's remaining allowance. D03 must define an explicit runtime
resource policy; normal use cannot rely on deleting/resetting delivery ledgers.
D02 neither packages a distribution nor starts D04 listening review.

## Commands and persistence

Run from the repository with the pinned `.venv` and existing optional CPU model
environment. No dependency or weight acquisition is needed:

```powershell
.venv/Scripts/python.exe -m sound_search_evaluation preflight
.venv/Scripts/python.exe -m sound_search_evaluation generate --split development
.venv/Scripts/python.exe -m sound_search_evaluation validate --split development
.venv/Scripts/python.exe -m sound_search_evaluation index --ordinals 0,4 --tag cold-pilot
.venv/Scripts/python.exe -m sound_search_evaluation index --ordinals 0,4 --tag reuse-pilot
# Inspect pilot cost and exact reuse before the remaining index.
.venv/Scripts/python.exe -m sound_search_evaluation index --split development
.venv/Scripts/python.exe -m sound_search_evaluation serve
```

The three product cases import/save through the normal browser on 8775 before
the CLI registers other development cases. Then `queries --skip-product`, `run`,
and `score` execute the declared development matrix. `resume --job <sha256>`
continues the exact admitted job. A fresh job cannot reuse another job's initial
case claim: it needs a counted technical replay. `replay --ordinals 0,16,20
--tag product-component-agreement` checks agreement. `--tag` distinguishes explicit
technical attempts; it never changes features or policy. Exact retries retain
the claim and useful committed units.

Commit the final candidate and unchanged decision gate before confirmation index
or query encoding. Confirmation uses `generate`, `validate`, `index`, `queries`,
`run` and `score` with `--split confirmation`, once and without tuning.
`report` reads both saved assessments and produces the private report at
`http://127.0.0.1:8775/evaluation/`. Scoring/reporting dispatch no feature work.
Every declared case must exist before scoring; missing/invalid predictions fail
explicitly rather than reducing the denominator.

Macro metrics give equal weight to each present `(positive family, query condition)`
cell; whole-query metrics average within each cell. A distinct-event query enters
both declared family cells. Boundary errors are conditional on one-to-one IoU
matches, with misses retained. Coverage matching independently uses 50% of the
true event; IoU matching uses 0.5. Native grid/support/rank/representative diagnostics
explain remaining misses.

The private report reads allowlisted existing originals for bounded excerpt
playback and displays exact scored native frames. Those players do not create
new crops or replace the product's separately verified exact PCM16 clips. Complete
predictions and both score summaries remain inspectable. The failure example
uses the prospective selection rule, without flattering replacement.
