# C02 candidate retrieval and result aggregation

C02 implements exact event supports, one experimental rank fusion, bounded
original-timeline consolidation and a versioned C03 shortlist. Implementation and delivery validation are complete. Original audio, legacy mean-example retrieval and pitch off remain
defaults. C03 refinement has not been started.

## Ownership and frozen policy

Pulled `main` to `1d6aaa9` and used isolated branch `codex/c02-retrieval` in the
primary checkout, with no extra worktree. Protocol/configuration were committed
as `11ef395` before scoring, implementation as `f9c64c7`, and inspected native
geometry/C03 metadata import as `f7325c9` before feature extraction.
The metadata-only correction is `6187618`; final tested consumer hashes were
published as `26faee7` before the fresh legacy delivery audit.
The [protocol](../manifests/retrieval/protocol.json) fixes all weights, case/truth
selection, support limits, ablations, metrics, accounting and stop conditions.

C02 uses read-only historical C01 membership/configuration paths and a separate
C02-owned fresh legacy receipt. Its legacy wrapper binds the historical bank hash
and fresh audit while comparing identical row membership/semantics. C01's snapshot,
receipt, arrays and closed allowance are not rewritten or reused as authorization.
B03 revisions/materializations are read-only, including every source/cue exclusion
before PCM deduplication. Missing dependencies require explicit C02 recipe import
and owned materialization, never an old worker or a success-shaped fallback.

The legacy baseline averages unique-example distances at the same candidate row.
The event policy instead retrieves each unordered example independently. Validated
original/processed variants of the same native parent support one event; maximum
variant credit caps correlated contributions. Per-event credits average complete
bank ranks using `61/(60+rank)`. Half the strongest event plus half mean event
credit favors both a strong match and agreement. Larger credits rank first;
baseline cosine distances rank lower first. Neither is a presence probability.

Primary fusion uses only the complete original 2.4s/.25s and 4.8s/1s populations,
44,025 and 10,914 rows across the same 72 groups. C01's 402-row short pilot and
region-only HPSS banks remain partial diagnostics. Opportunities per original/bank
are retained; rank fusion does not eliminate duration/hop/population bias.
Copied bank references, query order and exact PCM duplicates cannot multiply votes.

Each streamed shard uses the frozen float64 cosine reduction. Sixteen raw rows per
variant/bank/group survive before grouping; complete group summaries are retained
before twenty-group shortlist and ten-group display cuts. One exact scored row
anchors a cluster: positive intersection/minimum length at least .5, same recording
and at most eight seconds of envelope. The anchor never expands transitively.
Adjacent/disjoint intervals remain separate. At most three non-overlapping actual
representatives survive per duplicate group. An envelope or context is unscored.

## Fixed development and representation diagnostics

The fixed batch contains 37 recordings / 33 distinct eligible groups, including
28 declared distractor groups. Four familiar A04 procedural development families
have alternate performances; a generated hybrid contains pluck and FM events at
disjoint native positions. This is inspected development, not a fresh holdout or
human timbre truth. The twenty-group cut is smaller than the 30-33 eligible groups.

All saved WAVs passed independent reconstruction and FFT insertion-lag checks
before inference, committed in [geometry](../manifests/retrieval/geometry.json).
Twelve cases exercise single/multiple/conflicting examples, repeats, nonzero/tail
insertions, accompaniment, exclusions, absent targets and silence. Three arms are
fixed: legacy mean, event-aware legacy and the same event policy over both banks.
Exact-tail correctness, excluded/absent denominators and silence are separate.
Group hit@1/5/10/20, recall of all eligible positive groups, actual retained passage
support, containment, IoU and boundary error are distinct metrics. Native-grid,
support-selection, grouping and shortlist losses are retained separately.

| Primary development policy | Group hit@1 | Hit@5 | Hit@10 | Hit@20 | All-positive group recall@20 | Passage hit@20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Legacy mean | 6/7 | 7/7 | 7/7 | 7/7 | 12/12 | 6/7 |
| Event-aware legacy | 6/7 | 7/7 | 7/7 | 7/7 | 12/12 | 7/7 |
| Event-aware two-bank | 6/7 | 6/7 | 6/7 | 7/7 | 12/12 | 7/7 |

Both experimental policies have zero paired top-one gains/losses versus baseline.
The two-bank policy loses one top-five/top-ten success. The boundary query's known
groups remain in the baseline shortlist, but its single mean winner misses the
declared native overlap criterion; retaining secondary event supports recovers
usable passages. This is a support-retention gain, not a source-ranking or human
relevance improvement. Long-window containment is not automatically accurate
localization; IoU and boundary errors remain separate.

All three policies retain twelve positive group instances at twenty across the
seven primary cases. Exact-tail and repeated-example diagnostics remain separate;
excluded/absent positives have no success denominator, and all three silence arms
fail explicitly. The 28 distractor groups are deterministic parameter changes of
the familiar procedural mechanisms, not 28 human-verified instrument identities.
The baseline remains default, with no post-result weight or threshold adjustment.

Two additional scoped HPSS diagnostics use existing validated outputs with no new
separator run. Original and harmonic query variants share an independently bound
native parent interval; partial one-region candidate banks cannot claim full-corpus
rank/coverage meaning. The scalar oracle includes 33 groups where the old mean
objective/top twenty loses a needed disjoint event, while individual-event support
recovers it. This is an engineering correctness result.

## Resource and preservation boundary

One fixed C02 ledger caps aggregate worker time at 3,600 seconds / 256 workers,
120,000 source-read seconds, 2,048 new engineering/query windows, 12,000 feature-audio
seconds, 8 MiB features, 64 query/materialization/rank jobs, 64 clips / 96 MiB,
64 MiB counted metadata, 64 MiB query preparation, 64 MiB other audio preparation
and 384 MiB new managed output. No new discovery-bank features, acquisition,
separator processing, learned calibration, model/dependency change or deployment.
Starter 120s/1 GiB/256 MiB/4 GiB limits, concurrency one and free-space headroom
are unchanged. All new namespaces participate in shared inventory.

Windows preflight observed 55,922,253,824 available commit bytes, separately from
9,323,008,000 free physical bytes, against an 811,486,528-byte largest-worker
allocation estimate. The first two completed development units validated four
sources / eighty windows in 33.547 worker seconds, with 287,522,816-byte peak
working set. A conservative 400-second development estimate leaves a declared
1,500-second delivery/reuse reserve within the existing ceiling.

One inline progress publication exceeded the shared 1 MiB limit after 572 valid
windows, before comparison. Its failed command/log and original encoded progress
remain under `reports/local/c02`. Compact immutable array-metadata references shrink
completed progress to 45,583 bytes. The
[metadata integration](../manifests/retrieval/metadata-integration.json) binds the
exact consumer and proves unchanged audio/encoder functions plus native-grid and
feature-identity statements. All saved arrays were validated and reused, including
the already-published unit whose progress publication failed. A Windows file-replace
permission error interrupted migration once; the unchanged retry retained charges.
No historical data, prediction, case, cap or feature recipe was replaced.

Development completes with 624 candidate windows / eight query vectors; the scoped
representation check adds one query vector, totaling 633 newly encoded windows.
There are zero new discovery rows and zero separator inputs.

The pre-work preservation inventory contains 10,618 historical files /
1,389,093,936 bytes. It includes every C01 staging copy. Their previously denied
deletion is untouched; they are not worktrees. The C01 report command block receives
only the requested documentation correction: `-m similar_sound_search` before CLI
flags using `$c01Python`; its standalone script command/results/allowance stay intact.

## Exercised Windows commands

Run from the checkout in PowerShell. Completed comparisons are closed; these are
reproducibility/evidence commands, not permission to replenish an old allowance.
`build-development` and `search` resume only validated committed units; repeated
complete search refuses and `verify` provides the one charged reuse validation.

```powershell
$c02Python = '.venv/Scripts/python.exe'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& $c02Python -m unittest discover -s tests
& $c02Python -m ruff check src tests scripts/verify-retrieval-preservation.py
& $c02Python -m ruff format --check src tests scripts/verify-retrieval-preservation.py
& $c02Python -m pip install --no-index --no-deps --no-build-isolation -e .
& $c02Python -m pip check
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/preflight-command.json retrieval preflight
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/known-answer-command.json retrieval known-answer
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/generate-command.json retrieval generate
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/geometry-command.json retrieval geometry
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/build-development-command.json retrieval build-development
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/build-development-resume2-command.json retrieval build-development
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/compare-command.json retrieval compare
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/diagnostics-command.json retrieval diagnostics
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/compatibility-command.json retrieval compatibility
$c02Receipt = (Get-Content reports/local/c02/compatibility-command.json -Raw | ConvertFrom-Json).receipt
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/search-command.json retrieval search --receipt $c02Receipt
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/reuse-command.json retrieval verify --receipt $c02Receipt
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/report-command.json retrieval report
& $c02Python -m similar_sound_search --tier starter --report reports/local/c02/native-command.json retrieval verify-native
& $c02Python scripts/verify-retrieval-preservation.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/listen-retrieval.ps1
```

The isolated starter smoke uses `--root reports/local/c02/starter-smoke`; its
reference-independent plumbing does not imply the delivery Loulou audio is absent.
Private catalogue audio, checkpoint, arrays and saved-query dependencies are present
in this delivery checkout but are not supplied through public JSON to a fresh clone.
Missing prerequisites fail explicitly. The supplied full Loulou 218..240s mixture
and 217..241s context are preserved, including native event frames
9,613,800..10,584,000 at 44.1 kHz. Version/alignment/master offset/rights/intended
layer/complete event boundaries remain unverified. It adds no discovery recording.

## C03 handoff

Read the immutable `c02-c03-shortlist-1` execution reference from
`data/runs/retrieval/execution.json`. `retrieval.engine.read_shortlist(owner, ref,
arm="event-multi")` validates exact immutable group/source/support references and
rank/policy binding; the default arm remains `legacy-mean`. Complete eligible group
records, twenty shortlisted groups and ten displayed groups remain separate.

Each `c02-c03-group-1` carries snapshot/bank identity through its execution,
query/event/variant identity, actual scored representative row/shard/native bounds,
per-example distances, rank credits, original context and support, source/duplicate/
cue exclusions, support truncation and representative-selection rule. Context and
display envelopes do not inherit an uncomputed embedding. C03 must budget and audit
its own audio/arrays/current consumer and cannot spend closed C01/C02 funds or
reopen their workers. Finer timing, targeted extraction and original-mixture
rechecking belong there. Human/Loulou relevance is unmeasured.

## Verification trace

The final unchanged full suite passed **285 tests in 313.258s**, including 39 C02
tests. An earlier full run encountered four 100 ms localhost timeouts and one
retry-count assertion in existing catalogue tests. All 26 catalogue tests then
passed in isolation in 30.174s, followed by the clean full run; neither their code
nor timeouts changed. Logs remain in `reports/local/c02`. Ruff check and format,
pinned offline editable setup, `pip check`, isolated starter smoke, PowerShell
listener syntax and inline report-JavaScript syntax passed. No hosted CI is
configured, and no hosted check is claimed.

The real C02 execution is
`a1390a76b77c76aa53c3c97d6adfd5dc5ed38b5f0e9ad9ad2bf890f7a0554d67`.
Every arm retains all 72 eligible group summaries, a twenty-group shortlist and
ten displayed groups. The C03 metadata import independently reopened all three
twenty-group shortlists. The legacy complete winner digest is
`5ba261379bb3aa9c0a254af1bd25a4fda52bf2026efb5b0e9dae68ee24c65b53`,
identical to C01/B03 in every field/order/distance/native interval/query/exclusion.
The experimental top ten changes seven positions and overlaps nine baseline groups;
these differences are unmeasured Loulou relevance, not verified gains.


## Final costs, preservation and playback

[Machine-readable evidence](C02_RETRIEVAL_EVIDENCE.json) preserves the complete
case/arm results, immutable references, accounting and QA records without private
absolute paths. C02 consumed 1,365.208 of 3,600 worker seconds across 93 of 256
workers, 61,837.510 of 120,000 source-read seconds, 633 of 2,048 feature windows
and 1,713.9 of 12,000 feature-audio seconds. There were 50 of 64 query jobs,
25 of 64 clips, 6,411,776 of 8,388,608 reserved feature bytes, 24,868,280 of
100,663,296 clip bytes, 65,226,291 of 67,108,864 metadata bytes and 121,189,432
of 402,653,184 total managed reserved bytes. One development batch and 38 of
48 case/policy evaluations completed. No reservations remain pending. HTTP,
browser QA, setup and tests are separately measured outside processing workers.

Preservation checked 10,618 historical files totaling 1,389,093,936 bytes:
10,617 are byte-identical; the only allowed change is the exact C02 navigation
addition to config/README.md. No historical runtime configuration, ledger, array,
frozen module or supplied MP3 changed. The three previously denied C01 staging
folders remain intact; no deletion retry was attempted.

The verified local report is
`reports/local/c02/retrieval-ca3eece6fef719146b5bca003da638b3c51dd7e808e37aad1d63bc64f992e8a0/index.html`.
All 32 players passed exact native PCM16/sample/gain/map checks. All 25 unique WAVs
passed HTTP byte hashes, MIME, range and path rejection checks. Installed Chrome
155.0.8059.85 with bundled Playwright 1.62.1 passed all 32 load/play/advancing-clock,
pause and seek checks using 128 trusted keyboard events in 11.591 seconds, without
media or page errors. The first QA driver waited for buffering before activation;
its corrected trusted-play-first driver passed without any application change.
Both attempts are retained. The owned browser context and port-8771 test listener
are closed; prior listeners and bundles were untouched. No deployment occurred.

![Verified C02 playback](local/c02/browser-qa.png)


Delivery PR: [#22](https://github.com/lillo24/Similar-Sound-Search/pull/22).
