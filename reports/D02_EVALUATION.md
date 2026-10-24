# D02 — Automatic evaluation and bounded improvement

24 October 2026. D02 is complete: **40/40 declared cases, 80 initial policy
executions and eight technical executions** produced valid saved results. The
sole unchanged alternative, event-multi, **fails the prospective gate in both
splits**. Keep **original mixture / legacy mean / pitch off**. Event recovery
improves, but two development cases and one confirmation case lose previously
recovered positive groups at twenty. No model, threshold or default was promoted.

The [complete machine-readable evidence](D02_EVALUATION.json) retains every case,
native truth/match/miss, group denominator, forced score, diagnostic ordering,
failure attribution, source identity and resource counter. The private per-case
report contains 130 playable controls and forty complete-prediction links. These
are **prospective confirmation results within familiar A04 mechanisms**, not
unseen-music, human timbre or Loulou relevance evidence. D03 packaging and D04
listening review were not started.

Delivery trace: [PR #30](https://github.com/lillo24/Similar-Sound-Search/pull/30),
isolated plan branch `codex/d02-evaluation`. Ignored private evidence remains in
the delivery checkout; no separate task worktree was created.

## Prospective protocol and scope

Base main was `9b376c1ae6d8eb20ed6d57cf648f9e6b49c48fa0`; D01 was already merged
through PR #28. The matrix/configuration was committed before comparative inference
(`d6c10cf`). [Protocol](../manifests/assessment/protocol.json)
`893aa664d48c02297837cd188c94e4fbdc11c0c8530eca59b1800eb8ca3f1a47` fixes the
generator parameters/seeds, parents, splits, neutral IDs, input recipes, populations,
two policies, matching rules, costs and gate. There is no revision dimension.
The [final candidate](../manifests/assessment/candidate.json)
`3273c4ae09e61bcfa1397504731c79bde88ea2fc968484bda6e56e531085e38c` was committed
in `05f6eca` after the development gate failed and **before confirmation generation,
index/query encoding or inference**. Confirmation ran once, unchanged.

| Split | Candidate recordings / distinct groups | Primary queries | Absent / exact-parent diagnostics | All queries |
| --- | ---: | ---: | ---: | ---: |
| Development | 32 / 31 | 20 | 2 / 2 | 24 |
| Confirmation | 32 / 31 | 12 | 2 / 2 | 16 |

All primary queries have 31 eligible groups. Exact-parent diagnostics exclude their
genuine parent/PCM group and have 30; they carry no constructed relevance targets
and test exclusion rather than source-generalization success. Candidate 31 is a
real byte/PCM duplicate of candidate 24, sharing its group. Independent performances
of a positive character remain distinct eligible groups. No family label is an
ancestry exclusion. The two splits share neither performances, source parameters,
background realizations nor seeds.

Four familiar construction mechanisms—harmonic, plucked, FM and filtered noise—use
new character parameters and independently seeded detuning, spectrum, modulation
and background. Candidates include pitch-varied positives, matched-pitch hard
negatives, independently masked mixtures, multiple occurrences, off-grid placements,
source start/end events, complete short support and native 44.1 kHz stereo.
Development singles span base, pitch +6 semitones, masked −3 dB and 1.1s-reference
conditions. Confirmation singles use base/pitch conditions; both splits also have
four two-example queries: two alternatives of one character and two selections
containing genuinely distinct characters. Hard negatives and absent presets are
construction proxies, not human irrelevance labels.

Retrieval receives neutral IDs, genuine sources/parents and immutable native input
recipes. Family/positive lists, clean components and insertion times remain in the
construction/audit/truth side. Both splits passed independent full-byte closure and
decoded mixture algebra, achieved-level, lag, clipping/silence, short/stereo and
native-time audits before their model work. All original outputs are immutable.

## Production path and prediction contract

The separate [`sound_search_evaluation`](../src/sound_search_evaluation/README.md)
owner supplies a genuine generated population through five explicit application
seams. It uses production B03 save/materialization, frozen EfficientAT MN04,
C04 source/cache/score validation, C02 complete-population aggregation and D01
result/media contracts. The 72-recording discovery catalogue is unchanged.
Only the three representative cases incur full UI/card/media publication; the
other cases retain complete compact numerical predictions. Batch results are
component evidence, while the three normal browser/API cases are product evidence.

Both policies reuse the same source/query features and numerical supports. Native
banks remain **2.4s / 0.6s hop** and **4.8s / 1s hop**, including the unique tail.
There are 452 recording-membership rows per split, with 436 newly encoded candidate
rows after genuine duplicate reuse. Across both splits, 872 candidate and 48 query
feature rows give **920 new windows**. Each comparison ranks every eligible group;
twenty shortlisted groups and ten displayed cards are separate cuts. Original group
order, score direction, retained representatives/supports, exclusions, query identity,
shortlist and displayed-card binding survive the prediction adapter. Padding and
unscored context never count as scored support.

The CPU representation is the unchanged 384-dimensional EfficientAT MN04 final
convolution spatial mean, cosine distance, arithmetic-mean channels and fixed
32 kHz polyphase frontend. Checkpoint `mn04_as_mAP_432.pt` is 4,066,513 bytes, SHA256
`899a8c6217063f6941793102a2780b3dd788ab11fce468d9cf5f0577c453321c`;
upstream code revision is `a425fdce92572e602a1d5634799bd9f1f2efa806`. The JSON records
the exact frontend, code/configuration, pins, native population/input/truth/ancestry
hashes and every prediction hash. Predictions were persisted before truth scoring.
`score` and `report` perform no matcher/feature inference and reject missing cases.

## Paired primary results and decision

Metrics macro-average equal-weight present `(positive family, query condition)`
cells, averaging whole-query values within each cell. A distinct-character query
enters both declared family cells. Observations within a constructed family are
dependent; there is no trial-independence confidence interval.

| Split / metric | Legacy mean | Event-multi |
| --- | ---: | ---: |
| Development group hit@1 | 62.50% | 72.50% |
| Development all-positive-group recall@10 | 74.79% | 77.08% |
| Development IoU event recall@10 | 50.94% | 67.50% |
| Development all-positive-group recall@20 | 95.00% | 94.79% |
| Development IoU event recall@20 | 62.50% | 83.28% |
| Confirmation group hit@1 | 100.00% | 100.00% |
| Confirmation all-positive-group recall@10 | 71.18% | 68.75% |
| Confirmation IoU event recall@10 | 47.14% | 69.27% |
| Confirmation all-positive-group recall@20 | 89.24% | 91.32% |
| Confirmation IoU event recall@20 | 56.77% | 84.64% |

The gate requires complete valid compliant outputs, no macro hit@1 or IoU event
recall@10 loss, a strict improvement in at least one, and **no newly lost positive
group at twenty in any primary case**, separately on both splits. Both pass validity
and aggregate hit/event conditions, but fail coverage:

| Split / ordinal | Case ID prefix | Newly lost group prefix | Query semantics |
| --- | --- | --- | --- |
| Development 18 | `be72f6ee897b` | `21b37513df28` | Two distinct characters |
| Development 19 | `eb0faf40e503` | `40813c1c68f7` | Two distinct characters |
| Confirmation 9 | `34157af07a38` | `5af9d238756a` | Two alternatives of one character |

Full IDs, retained condition/case regressions and metrics at 1/5/10/20 are in the
JSON and tables below. The positive confirmation aggregate at twenty does not
erase its individual loss. Event-multi remains the existing labelled experiment;
it is not a qualifying D03 replacement. No second candidate or threshold was tried.

### Localization and missed events

Actual native **representatives** match one-to-one with targets at IoU ≥ 0.5.
The independent half-truth-overlap diagnostic is reported separately. One broad
passage cannot recover two events. Boundary errors below are conditional on IoU
matches; every miss remains in the event denominator.

| Split / arm | Matched / targets at 10 | Misses | Mean matched IoU | Mean truth coverage / prediction containment | Median absolute start / end error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development legacy | 88 / 176 | 88 | .7664 | .8960 / .8398 | .311s / .289s |
| Development event | 116 / 176 | 60 | .7696 | .9242 / .8243 | .227s / .227s |
| Confirmation legacy | 50 / 112 | 62 | .7908 | .8975 / .8622 | .227s / .227s |
| Confirmation event | 76 / 112 | 36 | .7814 | .9240 / .8350 | .227s / .227s |

For development case 0, a native 24 kHz representative `[14400,72000)` matches
truth `[8952,66552)` with IoU .827179 and +.227s start/end error. The stereo
44.1 kHz representative `[52920,158760)` versus truth `[44673,150514)` has IoU
.855435 and approximately +.187s errors. A 4.8s `[0,115200)` representative covering
a 2.4s `[0,57600)` target has truth coverage 1, IoU .5, prediction containment .5
and +2.4s end error. Better containment is therefore not automatically better timing.

At twenty, legacy/event misses divide into **60/20 representative-selection or
passage-cap losses and 8/10 group-rank losses** on development; confirmation has
**40/10 representative/cap losses and 11/8 rank losses**. No primary miss is assigned
to a missing eligible group, unreachable native grid or lost raw numerical support
in this suite. The diagnostic preserves grid reachability and retained support for
each miss; it does not claim to distinguish consolidation from every cap internally.

All four absent queries still return forced nearest groups. Their score orders and
top values are retained below and in JSON. Neither cosine minima nor normalized
event rank-fusion scores are presence confidence. There is no frozen rejection
threshold, false-accept-rate claim or human ground truth. Constant group-ID ties
and seeded random permutations use the same eligible groups, without feature work;
they are ranking controls and make no event-localization claim.

## Actual product and preserved delivery checks

Development cases **0 / 16 / 20** traversed real file import, native selection,
B03 save/load, submit/poll and complete result/media publication through the normal
browser on 8775 with the frozen model. The positive case was cancelled after its
query-feature counter increased, then resumed after owned-server shutdown/restart.
The same job and its useful units survived; resume encoded no replacement query.
Exact duplicate submission reused the request/job. Conflicting retries, unsupported
options, stale/corrupt inputs, cross-result media, exhausted ordinary capacity,
failure while recording failure and protected settlement have isolated fault tests.
No delivery input was deliberately corrupted.

Each case returned ten cards from 31 complete groups. **Sixty scored/context
players** passed fresh independent source-frame/channel/sample/gain verification
and actual Chrome play/pause/pointer-seek checks. One reference preview also played.
Range requests returned 206/64 bytes; reload and repeated status/result reads
preserved the pool byte-for-byte. Desktop and 390px layout passed. Accepted final
runs had zero unexpected page/console errors or external requests; earlier driver
failures are retained rather than included as successful final runs.

Three paired component replays matched the product cases' complete numerical/native
semantics, supports, banks and order exactly. A fourth paired replay followed actual
browser reorder/duplicate-add/save: the canonical two-example revision and ancestry
remained exact. These are **eight charged technical policy executions**, all with
zero new feature encodes. Different job/attempt IDs and timing are not semantic drift.

The report's 130 controls play existing generated originals with displayed bounded
native intervals, plus the exact scored/context failure clips. All controls passed
play/pause/pointer-seek; all forty cases/prediction links, reload, HTTP range and
390px layout passed without pool writes. Original-file players and separately
verified PCM16 product clips remain explicitly distinguished. The example rule was
frozen: first development primary baseline IoU miss at ten, then its highest-ranked
known-positive representative. Case 0 is selected; that representative may itself
match while other events remain missed. There is no flattering replacement.

The three exact D01 job/result pairs from the prompt reopened through the versioned
API without dispatch. Result/source/media bindings were checked read-only; **60
desktop and six narrow D01 controls** passed after the two shared CSS fixes for
long reference filenames. Player JavaScript and crop math are unchanged. Historical
native evidence is preserved; no new D01 numerical search is claimed.

C03's unchanged bundle
`b7c1bae8c55f488883a599d4486b85d382b6d66eecabc6bbf028871e4ae48aee` started on 8772;
three representative controls, range, reload and narrow layout passed. Its inherited
single-request server encountered connection refusals during unpaced Chrome metadata
loading and logged peer-abort traces. The final driver serialized unmodified HTTP
requests; this is a scoped regression pass, not a repaired historical server or an
unpaced all-player claim. Earlier failures and the driver body-wait mistake remain
in private QA. All owned foreground servers/browser contexts were stopped.

## Correctness repairs, resources and preservation

The [current consumer](../manifests/assessment/consumer.json)
`6926132ca5410a4200a97d339c9a3eebbaffabd3fc3b714e2245f834d84d1619` preserves all
earlier D02 declarations, the exact D01 consumer and unchanged inherited numerical
hash `faaa5b2f4ea303977b19dad336ee5911d1666018bcd95a317465ee94edce6487`.
Unknown drift still fails. Retained repairs are explicit:

- Before inference, native directory-entry scans replaced slow repeated Windows
  stats while still inventorying every managed root. Coordinator publication gets
  a fresh bounded budget after a child. The earlier audit publication refusal and
  its reservation remain charged. An independent byte-audit receipt-placement
  refusal also retained its full reads before the successful repeated closure.
- The first product aggregation rejected genuine PCM aliases as conflicting row
  witnesses. D02 now binds recording-specific native membership IDs for the aliases,
  retaining shared vectors, immutable raw score artifacts and identical distances,
  bounds and supports. The strict consumer and independent scalar/fusion test were
  declared before any accepted prediction. Frozen C02 aggregation is untouched.
- During development, bounded lossless JSON packing reduced new score/aggregate/
  prediction storage; old plain references remain exact. Hash, stream and 8 MiB
  decoded bounds are independently tested. The two CSS-only mobile fixes preserve
  `app.js`/`index.html` and are pinned by a separate exact UI proof.

Only one D02 pool was used. Initial stage reservations protected confirmation and
reporting before development. Measured admissions added 18 MiB development and
20 MiB confirmation ordinary capacity within the unchanged 256 MiB ceiling, with
32 MiB protected. Only completed preparation's **unspent** reservation was released;
no spent charge, retry, old ledger or capacity limit was reset/refunded. All attempt
reservations are settled, protected reserved bytes and uncertain worker seconds zero.

| Charged D02 resource | Used | Fixed ceiling |
| --- | ---: | ---: |
| Worker seconds / workers | 1,906.557 / 90 | 3,600 / 256 |
| Sequential source-read seconds | 16,815.700 | 90,000 |
| New feature windows / feature-audio seconds | 920 / 2,955.2 | 4,096 / 20,000 |
| Feature bytes | 8,622,080 | 33,554,432 |
| Processing/query jobs | 74 | 128 |
| Clips / clip bytes | 46 / 8,646,496 | 64 / 134,217,728 |
| Counted metadata bytes | 223,433,434 | 268,435,456 |
| Preparation / generated-plus-upload bytes | 15,474,944 / 75,500,896 | 67,108,864 / 134,217,728 |
| Managed output debit, including 64 MiB QA reservation | 175,353,280 | 1,073,741,824 |

The managed policy also reserves the complete 256 MiB metadata envelope: together
443,788,736 bytes, below 1 GiB. Protected metadata spent is 9,690,490 bytes.
Peak recorded worker working memory is 293,761,024 bytes; the largest recorded
worker/coordinator-server overlap bound is 393,236,480. Starter 120s actual-PID
deadlines, 1 GiB numerical working memory, 256 MiB I/O, numerical concurrency one,
combined 4 GiB managed storage and 4 GiB free-space headroom stayed enforced.
Non-inference QA/report artifacts occupy about 55 MB of their prepaid 64 MiB;
tests/setup and read-only playback are separate from charged model/audit work.
The final fresh physical inventory measured 1,833,173,033 managed bytes across
all stages, below 4 GiB, with more than 209 GB disk free at the recorded snapshot.
No download, new package/driver, GPU, external rating, paid service, telemetry,
deployment or automatic garbage collection ran.

The final preservation audit verified **17,330 historical files**, with zero changed
or missing files and zero unexpected additions. It permits 96 new files in 48
immutable shared A02 preparation bundles. All old configurations, ledgers, arrays,
media, reports, MP3 and C01 denied staging remain byte-identical; no denied deletion
was retried. D01 retains its 2,452.230 seconds / 85,949.160 reads / 73,613,272 metadata
bytes. C04 remains partial 145/148 with its separate unjournaled 120-second
reservation. D02 has not settled or recast either history.

## Runnable commands and validation

[ASSESSMENT.md](../docs/ASSESSMENT.md) documents explicit preflight, generate/validate,
byte closure, index, query, run/resume, score, report and serve commands. Existing
immutable jobs resume by exact ID; re-running first-time admission after a measured
extension is intentionally refused. A fresh public clone lacks private checkpoint/
catalogue artifacts and cannot claim these real-model or historical delivery checks.
Independent tests and the isolated smoke remain runnable without them.

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.venv/Scripts/python.exe -m unittest discover -s tests -q
.venv/Scripts/python.exe -m ruff check src tests scripts
.venv/Scripts/python.exe -m ruff format --check src tests scripts
.venv/Scripts/python.exe -m pip check
# Existing saved evaluation; no model work is dispatched by serve.
.venv/Scripts/python.exe -m sound_search_evaluation serve
```

Open `http://127.0.0.1:8775/evaluation/`. The default app launch remains
`scripts/start-sound-search.ps1` on 8774; C03 remains `scripts/listen-refinement.ps1`
on 8772. Both completed routes remain readable at their execution caps.

The final complete suite passed **404 tests in 236.507s**. Its 22 D02 tests include
scalar/native oracles, complete group versus window ranking, reversed scores,
duplicates, missing cases, out-of-bounds intervals, one-to-one denominators, coverage
versus IoU, exact ties, gate regressions, emitted PCM, aliases, packed storage and
protected failure handling. Existing application tests cover actual process locks,
interruption, idempotency, HTTP/origin/token/range and media isolation. Earlier
399-test validation retained two pre-existing 20s CLI boundary timeouts; all seven
boundary tests passed on retry, and the final full run passed without timeout
changes. No Python source was edited during the final full run; live model work
kept its pinned numerical/runtime source unchanged.

Ruff lint and format passed (224 Python files); JavaScript syntax passed. Pinned
offline core setup built/installed the editable wheel and passed `pip check`.
Every installed core and optional CPU lock pin matches, including Torch 2.6.0+cpu;
the optional environment was reused. The installed console entry point passed
starter smoke in a new D02-owned workspace, preserving the old smoke report.
Independent pure known answers passed four scalar pairs and eleven native intervals.
No hosted workflow or required check is configured; no hosted CI pass is claimed.

## Concrete D03 packaging handoff

| Requirement | Handoff |
| --- | --- |
| Configuration | Original mixtures, legacy mean, pitch off. Event-multi remains explicitly experimental after both gates fail; no transforms, automatic selection, unsupported pitch or new-query refinement. |
| Runtime/dependencies | Python 3.12.14, project 0.3.0; unchanged `requirements.lock` and Windows AMD64 CPU `requirements-models.lock`. JSON contains exact pins, lock SHA256s, checkpoint/frontend and source maps. No GPU service is required. |
| Required private assets | Existing MN04 weights; registered source audio and B03 bindings; C01/C04 candidate arrays, source/score records and exact D01 results/media; C03 immutable bundle. D02's generated audio/index/query/prediction/assessment/report roots are separate evaluation fixtures. Public metadata does not prove local availability. |
| Schemas/fixtures | `d01-result-1` and `/result-media/<result-id>/<media-id>` bind complete query/arm/population/cards/native crops. `d02-prediction-1` expands through the bounded lossless Context reader. Three D01 exact baselines and three D02 product IDs are preserved in JSON; deterministic isolated fault fixtures live in `tests/test_application.py` and `tests/test_assessment.py`. |
| Pass/fail automation | Full 404-test command, Ruff, JS syntax, locked dependency check, isolated smoke and pure known answers above. Saved scoring/reporting never infer; any missing case, invalid source/media/hash, unsupported setting or exhausted allocation is explicit failure. |
| Costs | D02 charged CPU/read/write/memory counts above; saved per-attempt journals preserve startup, useful units, failures and timing. The 72-source real app's distinct D01 costs remain in its report. These small generated runs are not real-catalogue throughput estimates. |
| Recovery | Exact immutable retries, pending acknowledgements, source-bound cancellation, actual-PID interruption, committed-unit resume and independent protected terminal settlement. Never replace an unavailable result with empty success or silently borrow a historical owner. |
| Runtime resource policy | **Required D03 design:** define an explicit separately bounded runtime owner/admission/retention policy with protected terminal capacity, working/I/O/time/disk/free-space caps and one numerical worker. Preserve delivery ledgers. Normal use must never depend on deleting/resetting them. D01 cannot admit another complete real search; D02's small remaining delivery reservation also cannot admit a fresh full product search. Read-only demos remain usable. |
| Remaining quality | Rank/cap losses, variable native localization, lower confirmation group recovery@10, opportunity bias of multiple windows and uncalibrated absents. This suite supplies no human agreement, unseen-musical-source or verified Loulou layer relevance. D04 remains the first required listening review. |

A06's eighty queries were previously inspected and are not a fresh holdout.
Grey1977 still has zero eligible human-scoring pairs. Loulou retains the full
218..240s available-file mixture at native frames 9,613,800..10,584,000, 44.1 kHz,
and 217..241s context. Intended layer, marked-version/master offset, rights and
relevance remain unverified. No new labels were requested or invented.

## Complete cuts and paired case audit

These tables are rendered from the saved public JSON. Percentages are descriptive;
case rows preserve actual integer denominators. L/E means legacy mean / event-multi.

### All primary macro cuts

| Split | Arm | Cut | Group hit | All-positive-group recall | IoU event recall | Half-truth coverage recall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| development | legacy-mean | 1 | 62.50% | 9.38% | 7.03% | 7.03% |
| development | legacy-mean | 5 | 100.00% | 47.50% | 32.66% | 33.28% |
| development | legacy-mean | 10 | 100.00% | 74.79% | 50.94% | 52.50% |
| development | legacy-mean | 20 | 100.00% | 95.00% | 62.50% | 64.53% |
| development | event-multi | 1 | 72.50% | 11.46% | 9.84% | 10.47% |
| development | event-multi | 5 | 100.00% | 46.04% | 39.53% | 40.78% |
| development | event-multi | 10 | 100.00% | 77.08% | 67.50% | 70.00% |
| development | event-multi | 20 | 100.00% | 94.79% | 83.28% | 86.41% |
| confirmation | legacy-mean | 1 | 100.00% | 14.93% | 11.20% | 11.20% |
| confirmation | legacy-mean | 5 | 100.00% | 52.08% | 35.68% | 36.72% |
| confirmation | legacy-mean | 10 | 100.00% | 71.18% | 47.14% | 48.18% |
| confirmation | legacy-mean | 20 | 100.00% | 89.24% | 56.77% | 59.64% |
| confirmation | event-multi | 1 | 100.00% | 14.93% | 17.97% | 18.49% |
| confirmation | event-multi | 5 | 100.00% | 55.90% | 57.29% | 60.94% |
| confirmation | event-multi | 10 | 100.00% | 68.75% | 69.27% | 72.92% |
| confirmation | event-multi | 20 | 100.00% | 91.32% | 84.64% | 88.80% |

### Conditions and retained regressions

Means below are over whole primary queries within each condition, rather than the
separate equal-family/condition macro above. Every paired case remains below them.

| Split / condition | Queries | Hit@1 L/E | IoU event recall@10 L/E | Positive-group recall@20 L/E |
| --- | ---: | ---: | ---: | ---: |
| development / base | 4 | 75.00% / 75.00% | 56.25% / 71.88% | 100.00% / 100.00% |
| development / pitch +6 | 4 | 25.00% / 50.00% | 50.00% / 71.88% | 95.83% / 95.83% |
| development / masked −3dB | 4 | 75.00% / 100.00% | 37.50% / 53.12% | 87.50% / 87.50% |
| development / short 1.1s | 4 | 50.00% / 75.00% | 65.62% / 75.00% | 100.00% / 100.00% |
| development / multi alternatives | 2 | 50.00% / 50.00% | 50.00% / 68.75% | 91.67% / 100.00% |
| development / multi distinct | 2 | 100.00% / 50.00% | 40.62% / 56.25% | 87.50% / 83.33% |
| confirmation / base | 4 | 100.00% / 100.00% | 53.12% / 71.88% | 91.67% / 95.83% |
| confirmation / pitch +6 | 4 | 100.00% / 100.00% | 53.12% / 71.88% | 87.50% / 91.67% |
| confirmation / multi alternatives | 2 | 100.00% / 100.00% | 37.50% / 62.50% | 91.67% / 83.33% |
| confirmation / multi distinct | 2 | 100.00% / 100.00% | 31.25% / 62.50% | 83.33% / 87.50% |

### Every declared case

`F` identifies the constructed character family; it is not an exclusion group.
Primary rows have known positive groups/events. Absent and exact-parent rows have
zero constructed targets; dashes are not dropped or failed cases. All forty
predictions are complete and valid. Group counts are eligible / known positive.

| Split / case | Recipe | Groups | Hit@1 L/E | Matched events@10 L/E / targets | Positive groups@20 L/E |
| --- | --- | ---: | ---: | ---: | ---: |
| development 0 | F0 base | 31 / 6 | 1 / 1 | 3 / 4 / 8 | 6 / 6 |
| development 1 | F0 pitch +6 | 31 / 6 | 0 / 0 | 2 / 2 / 8 | 5 / 5 |
| development 2 | F0 masked −3dB | 31 / 6 | 1 / 1 | 2 / 2 / 8 | 4 / 4 |
| development 3 | F0 short 1.1s | 31 / 6 | 1 / 1 | 6 / 6 / 8 | 6 / 6 |
| development 4 | F1 base | 31 / 6 | 1 / 1 | 4 / 5 / 8 | 6 / 6 |
| development 5 | F1 pitch +6 | 31 / 6 | 0 / 1 | 3 / 5 / 8 | 6 / 6 |
| development 6 | F1 masked −3dB | 31 / 6 | 1 / 1 | 3 / 5 / 8 | 6 / 6 |
| development 7 | F1 short 1.1s | 31 / 6 | 0 / 1 | 4 / 3 / 8 | 6 / 6 |
| development 8 | F2 base | 31 / 6 | 0 / 0 | 5 / 6 / 8 | 6 / 6 |
| development 9 | F2 pitch +6 | 31 / 6 | 0 / 0 | 5 / 8 / 8 | 6 / 6 |
| development 10 | F2 masked −3dB | 31 / 6 | 0 / 1 | 1 / 2 / 8 | 5 / 5 |
| development 11 | F2 short 1.1s | 31 / 6 | 1 / 1 | 5 / 7 / 8 | 6 / 6 |
| development 12 | F3 base | 31 / 6 | 1 / 1 | 6 / 8 / 8 | 6 / 6 |
| development 13 | F3 pitch +6 | 31 / 6 | 1 / 1 | 6 / 8 / 8 | 6 / 6 |
| development 14 | F3 masked −3dB | 31 / 6 | 1 / 1 | 6 / 8 / 8 | 6 / 6 |
| development 15 | F3 short 1.1s | 31 / 6 | 0 / 0 | 6 / 8 / 8 | 6 / 6 |
| development 16 | F0 multi alternatives | 31 / 6 | 0 / 0 | 3 / 3 / 8 | 5 / 6 |
| development 17 | F1 multi alternatives | 31 / 6 | 1 / 1 | 5 / 8 / 8 | 6 / 6 |
| development 18 | F2,3 multi distinct | 31 / 12 | 1 / 1 | 6 / 10 / 16 | 12 / 11 |
| development 19 | F0,3 multi distinct | 31 / 12 | 1 / 0 | 7 / 8 / 16 | 9 / 9 |
| development 20 | absent-target | 31 / 0 | — | — | — |
| development 21 | absent-target | 31 / 0 | — | — | — |
| development 22 | exact-instance-exclusion | 30 / 0 | — | — | — |
| development 23 | exact-instance-exclusion | 30 / 0 | — | — | — |
| confirmation 0 | F0 base | 31 / 6 | 1 / 1 | 4 / 4 / 8 | 5 / 5 |
| confirmation 1 | F0 pitch +6 | 31 / 6 | 1 / 1 | 2 / 5 / 8 | 4 / 4 |
| confirmation 2 | F1 base | 31 / 6 | 1 / 1 | 2 / 4 / 8 | 5 / 6 |
| confirmation 3 | F1 pitch +6 | 31 / 6 | 1 / 1 | 5 / 5 / 8 | 5 / 6 |
| confirmation 4 | F2 base | 31 / 6 | 1 / 1 | 5 / 7 / 8 | 6 / 6 |
| confirmation 5 | F2 pitch +6 | 31 / 6 | 1 / 1 | 5 / 6 / 8 | 6 / 6 |
| confirmation 6 | F3 base | 31 / 6 | 1 / 1 | 6 / 8 / 8 | 6 / 6 |
| confirmation 7 | F3 pitch +6 | 31 / 6 | 1 / 1 | 5 / 7 / 8 | 6 / 6 |
| confirmation 8 | F0 multi alternatives | 31 / 6 | 1 / 1 | 3 / 5 / 8 | 5 / 5 |
| confirmation 9 | F1 multi alternatives | 31 / 6 | 1 / 1 | 3 / 5 / 8 | 6 / 5 |
| confirmation 10 | F2,3 multi distinct | 31 / 12 | 1 / 1 | 7 / 12 / 16 | 11 / 11 |
| confirmation 11 | F0,3 multi distinct | 31 / 12 | 1 / 1 | 3 / 8 / 16 | 9 / 10 |
| confirmation 12 | absent-target | 31 / 0 | — | — | — |
| confirmation 13 | absent-target | 31 / 0 | — | — | — |
| confirmation 14 | exact-instance-exclusion | 30 / 0 | — | — | — |
| confirmation 15 | exact-instance-exclusion | 30 / 0 | — | — | — |

### Ordering controls and absent forced scores

Ordering controls use the frozen macro weights and same eligible groups. Their
scores order groups only; there is no fabricated event-localization output. Random
seed 882711 is combined with each neutral case ID; ties use group-ID ascending.

| Split / control | Hit@1 | Hit@10 | All-positive-group recall@10 | All-positive-group recall@20 |
| --- | ---: | ---: | ---: | ---: |
| development / constant-tie-group-id | 32.50% | 100.00% | 41.88% | 62.71% |
| development / seeded-random-order | 47.50% | 90.00% | 35.42% | 66.46% |
| confirmation / constant-tie-group-id | 37.50% | 83.33% | 29.86% | 67.36% |
| confirmation / seeded-random-order | 16.67% | 91.67% | 43.06% | 66.67% |

| Absent case | Groups returned | Top legacy cosine distance (lower better) | Top event rank-fusion score (higher better) |
| --- | ---: | ---: | ---: |
| development 20 | 31 | 0.09643826 | 1.00000000 |
| development 21 | 31 | 0.09709732 | 1.00000000 |
| confirmation 12 | 31 | 0.04434108 | 1.00000000 |
| confirmation 13 | 31 | 0.05179148 | 1.00000000 |

### Measured bounded-worker latency

These are settled worker elapsed sums from immutable attempt journals, including
startup, failed work, cancellation and retries. They exclude browser interaction
and idle server time; they are not real-catalogue throughput predictions.

| Operation | Worker attempts | Settled worker seconds |
| --- | ---: | ---: |
| two source cold index | 1 | 25.421 |
| two source reuse index | 1 | 45.172 |
| product case 0 | 3 | 51.797 |
| product case 16 | 1 | 22.609 |
| product case 20 | 1 | 28.157 |

The measured two-source reuse pilot was slower than cold indexing despite zero
new encodes. Fresh byte/dependency validation, storage and startup still cost time;
these isolated observations do not establish a cache speedup or service latency SLA.
