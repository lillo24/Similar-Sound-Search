# A06 — Local exact passage search evidence

Measured 14 October 2026 on the delivery Windows CPU checkout. The implementation,
single frozen held-out check and full-original catalogue index are complete. Both
single and multiple-example catalogue demos return ten distinct recording candidates
with original stereo playback. No human/Loulou relevance is claimed.

## Frozen implementation and validation

Started from main `89b9ff7`, after pulling the A06 prompt. Numeric A06 caps were
committed in `20a8a9e` before long work; implementation/configuration froze at `564ba0c`.
The pre-inference declaration was committed at `0512e0c`, before any held-out inference.
No held-out matcher scores had been inspected before that declaration. After scoring,
no algorithm/model/configuration choice was changed and no second model was selected.

[Search commands/contracts](../docs/SEARCH.md), [source owner map](../src/similar_sound_search/search/README.md)
and [record map](../manifests/search/README.md) describe delivered operations. Shared
changes only expose validated full originals, generalize truth-independent split routing,
strengthen the held-out guard, route known-answer output to its accounting owner and
add the A06 lock/managed paths. A05 adapters/checkpoint/choice/versions/allowances remain
unchanged. No dependencies, models, training, separation, refinement or cloud service
were added. The batch ends at A06; D04 remains the first required listening review.

Ordinary and optional setup, dependency consistency, Ruff lint/format, all **144 offline
regression tests in 96.652 seconds**, starter offline smoke and A06-routed independent
known answers passed. The pre-freeze 142-test run passed in 68.943 seconds; two additional
tests cover the later serial-ranking repair and its unchanged-code proof. Ordinary tests
neither import pretrained inference nor consume the delivery final attempt. Twenty-five
new tests cover boundaries, brute-force ranks,
query invariance/exclusions, partial/resumable work, original samples, pitch abstention,
corruption/containment and declaration/technical-resume behavior. Original 119 tests are
unchanged. There is no hosted-CI pass claim; hosted/required checks are inspected before merge.

Windows setup initially failed because the running report server held the console
launcher. The owned server was stopped, editable installation repaired, and pip's old
rollback metadata preserved outside site-packages. Optional setup then passed with
218,227,265 existing wheel bytes and unchanged renderer tools. No checkpoint was downloaded.
This repair preceded the final declaration and did not alter representation/source identities.

Python 3.12.14, NumPy 2.2.6, SciPy 1.15.3, SoundFile 0.13.1/libsndfile 1.2.2, Torch
2.6.0+cpu, CPU/numerical threads one; GPU unused. Live pretrained evidence is Windows,
not a claim of optional Linux inference compatibility. Package/preparation versions stay
0.3.0/a02-preparation-3 to preserve existing artifact identities.

## One final controlled held-out check

The self-hashed [declaration](../manifests/search/final-check.json) binds the unchanged
A05 choice/shortlist, authoritative comparison pair, exact configuration/checkpoint,
2.4s/.25s/tail grid, held-out split, pitch zero, empty refinement, code/environment and
fixed A06 accounting owner. Original choice stays stage A05. A free-form stage:A06
object is rejected. All eighty predictions were saved before truth/scoring, with their
denominators retained. Results are [recorded publicly](../manifests/search/final-results.json);
raw predictions, vectors, progress and full scores remain ignored.

| Binding | SHA256 |
| --- | --- |
| A05 choice | `95dce46b16760b002358b1aec3db8adb9b5df1c1f2033ee70b0b5121c2dea051` |
| Protocol | `07af66b37db00d6a6dd4bea87c9636b06aa9dbd43c75e8164be4568bd94b0048` |
| Suite | `d4c59416e5d4bb4aeddfbefa933a3a0f18691a25957e3623f1743d2951806441` |
| EfficientAT configuration | `5a487b946d748d48ec2945dae97e51f07bd0e8b106fa6c49c98df9e84a4035e9` |
| A06 declaration | `5885ce947f3a4bae9a21c129f19e091bb2778903781b5a6875c75fefe16258b2` |

Run `a06-final-4b0b011a0bf4869e5625bf138f4b145bd4ceb20c438116084b122a51d363a389`
completed 80/80 queries (72 target-present, eight absent, 88 target events), 1,368
unique windows and 3,283.2 processed window seconds. Source-consistency query hit@1
is **21/24 = 87.5%**, compared with the development 24/24. Source-consistency event
recovery is **21/32 at K=1**, 29/32 at K=5 and **32/32 at K=10**. The default is unchanged;
weaker performance is reported rather than used to choose another model.

| Condition | Queries / targets | Hit queries 1 / 5 / 10 | Recovered events 1 / 5 / 10 | First-rank median | Conditional boundary MAE at 1; matched / missed |
| --- | ---: | --- | --- | --- | --- |
| absent:0 | 8 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | undefined | undefined; 0 / 0 |
| exact_instance:-12 | 8 / 16 | 6 / 8 / 8 | 6 / 12 / 15 | 1.0 | 0.208333s; 6 / 10 |
| exact_instance:0 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 | 0.093750s; 8 / 0 |
| exact_instance:12 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 | 0.406250s; 8 / 0 |
| exact_waveform | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 | 0.000000s; 8 / 0 |
| performance | 8 / 8 | 6 / 8 / 8 | 6 / 8 / 8 | 1.0 | 0.000000s; 6 / 2 |
| pitch | 8 / 8 | 5 / 8 / 8 | 5 / 8 / 8 | 1.0 | 0.000000s; 5 / 3 |
| source_consistency:-12 | 8 / 16 | 6 / 8 / 8 | 6 / 13 / 16 | 1.0 | 0.291667s; 6 / 10 |
| source_consistency:0 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 | 0.125000s; 8 / 0 |
| source_consistency:12 | 8 / 8 | 7 / 8 / 8 | 7 / 8 / 8 | 1.0 | 0.392857s; 7 / 1 |

Families aggregate all ten conditions, including two absent queries each. Each family
has eighteen target-present queries and twenty-two target events; observations are
dependent. No independent-window significance/confidence interval is claimed.

| Family | Queries / targets | Hit queries 1 / 5 / 10 | Recovered events 1 / 5 / 10 |
| --- | ---: | --- | --- |
| procedural:harmonic:1 | 20 / 22 | 14 / 18 / 18 | 14 / 22 / 22 |
| procedural:pluck:1 | 20 / 22 | 16 / 18 / 18 | 16 / 19 / 21 |
| procedural:fm:1 | 20 / 22 | 18 / 18 / 18 | 18 / 20 / 22 |
| procedural:noise:1 | 20 / 22 | 14 / 18 / 18 | 14 / 20 / 22 |

Refined lists are empty. The conditional boundary error excludes misses, which remain
in target denominators; several successful endpoints differ by hundreds of milliseconds.
Eight absent top cosine distances are `0.542515, 0.561896, 0.600177, 0.618041,
0.549783, 0.713720, 0.446142, 0.635766`. No rejection rule/probability calibration exists,
so false accepts remain undefined. Grey1977 has zero eligible scoring pairs and no
human agreement result. Small preset families, fixed placement/grid bias, reused
backgrounds, single-label catalogue bias and unknown pretraining overlap remain limits.

Final adapter loads totaled 9.312 seconds, extraction 24.578, rank computation 0.046;
measured model cost 33.935 seconds. Outer inference took 175.859 seconds and scoring
10.891; startup/validation/atomic publication are separate from model time. Actual array
bytes are 2,111,488; measured peak working set 282,996,736 bytes versus the conservative
805,306,368-byte reservation. Exactly one final attempt and 1,368 final windows were
charged; the final evaluation had no technical interruption or repeat model selection.
The later post-inspection catalogue execution repair is recorded below.

## Development cost pilot and original-playback correctness

The 64-window native-original development pilot took 2.135 extraction seconds, 5.691
adapter-load seconds and 326,160,384 bytes peak working set. Its pre-ranking decision
retained 2.4s windows/.25s hop, 512-vector shards and one duration; no catalogue rankings
or held-out scores informed this choice. The old per-window allocation scheme is not used.

The separate generated fixture has a known stereo target at original 3.0..5.4s in an
8s, 48kHz available file. A02 crop/resample 48→16→24kHz produces a full query mapped
to original 3.1..5.3s and, with its synthetic known offset 10s, recording 13.1..15.3s.
Diagnostic retrieval returned the planted 3.0..5.4s scored interval, with 2.0..6.4s
playback context. Query-boundary difference is ±.1s; mapping correctness is independent
of that model localization. Generated positives never enter real-catalogue discoveries.

Each playback crop preserves original channels/rate/time and verifies every exported
PCM16 sample against the declared original crop conversion. Gain 1 was used for both
engineering clips. Their browser durations were exactly 2.2 and 4.4s. Chrome loaded them,
played/paused, sought to 2.2s and paused after advancing to 3.168249s; full seekable spans
were observed. The initial full-file server responses exposed a zero seekable span; the
pre-freeze repair adds bounded single byte ranges on the existing owned-media allowlist.
A temporarily moved owned clip produced visible HTTP 410 stale/missing-media text;
restoration recovered the unchanged media. [Browser evidence](../manifests/search/browser-qa.json)
is technical playback evidence, not a listening judgment. No external master/MP3 seek
claim follows from WAV playback.

The real-catalogue loopback bundle also returned HTTP 200 and its report title appeared
in Chrome. An initial HTTP 410 bundle-verification response cleared on unchanged recheck.
Later browser-control attempts timed out, and the connected Chrome extension explicitly
required an update. Those attempts do not establish play/pause/seek for the eleven
catalogue clips through that unavailable capability. The earlier
two-clip engineering report exercised the identical delivered playback/server code in
Chrome; all catalogue clips additionally passed independent original-sample verification.

Loulou is absent from explicit project input locations, with the original manifest
still missing/unverified. The development-side Deadly Combo crop was deterministically
selected before rankings, starting at native available-file 2s, lasting 2.4s; the multiple
query adds its adjacent crop and deduplicates a repeated first example. These are labelled
alternative engineering demos without a verified selected layer. Full/excerpt-ready input
instructions and the unrun Loulou command are in SEARCH.md; no substitute validates Loulou.

## Exact exercised commands

Global flags precede the subcommand, from the delivery root in PowerShell. The setup
repair and browser server use the same existing environment and do not acquire models.

```powershell
.\scripts\setup.ps1 -PythonExecutable .\.venv\Scripts\python.exe
.\scripts\setup-models.ps1
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\ruff.exe format --check src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-starter-smoke.json smoke
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-known-answers.json search known-answer
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-pilot-run.json search pilot
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-demo-selection-run.json search demo-inputs
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-known-inputs-run.json search diagnostic-inputs
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-known-index.json search index --engineering config/local/a06-engineering.json
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-known-query.json search prepare-query config/local/a06-known-query.json
# The actual fixture paths are retained in the two private CLI reports above.
$a06KnownIndex = (Get-Content -Raw reports/local/a06-known-index.json | ConvertFrom-Json).index
$a06KnownQuery = (Get-Content -Raw reports/local/a06-known-query.json | ConvertFrom-Json).query
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-known-rank.json search rank --index $a06KnownIndex --query $a06KnownQuery --include-self
$a06KnownResult = (Get-Content -Raw reports/local/a06-known-rank.json | ConvertFrom-Json).result
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-known-report.json search report $a06KnownResult
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-final-declaration.json search declare
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-final-run.json search final-run
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-final-score.json search final-score
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-index.json search index
```

The opening wrapper was also exercised with the engineering bundle:

```powershell
.\scripts\listen-search.ps1 -Report reports/local/a06-known-report.json -Port 8767
```

Its allowlisted HTML returned HTTP 200; a repository `AGENTS.md` path request returned
404. Ctrl+C stops the owned listener. No repository-root server was used.

The preservation audit passed for **7,121 earlier files / 935,022,634 bytes**, comparing
SHA256, exact sizes and nanosecond modification times, in 69.107 seconds. This includes
the previous audio, weights, dependency wheels, feature data, public manifests and
A03/A04/A05 accounting; no earlier allowance was reset or charged by A06. Audit/tooling
time is separate from model/worker timing. The final audit also passed for all 7,121
files, in 327.564 seconds under the later host load.

The first full index stopped after 43 recordings when a native worker exited with
status 3221225477 and no valid JSON. The failure and partial index were preserved. An
unchanged resume verified earlier shards and passed the interruption point; no code,
configuration, representation or library version was changed, and all uncertain window
allocation remained charged. The native cause is unestablished. Held-out scores had
already been inspected; this is a post-inspection technical index resume, without a new
evaluation or algorithm choice.

## Full-original catalogue and discovery demonstration

[Catalogue coverage](../manifests/search/catalogue-index.json) records index
`d027f2cd5ca817bc320542df16a540346325403bcb967fd248216c8c466731e2`:
**72/72 local ready recordings**, 70 provider full tracks and two unknown-offset
excerpts. Every full available-file duration is covered. Original and indexed-union
duration are both **11,152.101337868482 seconds = 3.097806 hours**. The 44,025 windows
process 105,660 overlapping window-seconds; these are not unique source hours.
All external master offsets remain unverified.

There are 123 immutable float32 shards, 67,622,400 vector bytes and **67,638,144 actual
array-file bytes** including headers. Cold extraction totaled 1,450.212 seconds,
adapter loads 623.834 seconds and original validation 277.868 seconds. Peak measured
working set was **351,547,392 bytes**, within the unchanged 1 GiB ceiling. Outer worker,
query/report and repeated validation costs are recorded separately; they include startup,
source verification and atomic publication. No model-rate derivatives replaced originals.

After the native stop, an unchanged resume subsequently reached a 120-second worker
deadline after 52 recordings. Both partial states and uncertain charges were retained;
the next unchanged resume completed all 72 without re-embedding committed shards.
The first all-catalogue rank also exceeded one worker deadline. The post-inspection
[execution repair](../manifests/search/execution-repair.json), committed at `29324ff`,
limits source validation/ranking to four recordings per serial worker with durable
progress. Original code proofs and runtime syntax checks preserve feature extraction,
distance/aggregation/tie/exclusion rules, grid and scoring. The same index/declaration
identities remain valid; held-out inference was not repeated.

The predetermined Deadly Combo selection uses native available-file 2.0..4.4s.
Query `89a6c264f6a9528efd792be6726287a6f42e7dde86bbef548cc0c96eeb2bd80c`
scores 43,402 eligible windows after excluding its parent's duplicate group. Result
`94fd356a653622972226c45c116b23a008280ac3017b984dbfd1d3d77de03867`
returns ten distinct groups among 71 eligible groups. The top ranked candidate is
Donnie Ozone, *Rap Style (Four Track Mixx)*, available-file 112.75..115.15s, cosine
distance 0.36549. Deadly Combo's other recording *Nuthin'* remains eligible and occurs
at rank four: artist identity does not exclude an entire artist. These are candidates
without confirmed sound-layer relevance.

The multiple input contains the first crop, its adjacent crop and a repeated first
example. It prepares two unique examples, query
`cf31a1ee58c5b3419ae28fc0c98d90ae8bc492e7381416eeab6ddfcb2f05483a`,
and returns ten distinct groups, result
`975ac0d6713bf63b8e9a07ad157b12e7b04126799d1b16c84583828643b81dc6`.
The [sanitized demo record](../manifests/search/catalogue-demo.json) retains all candidate
IDs/native bounds, per-example distances, query load/extraction costs and playback gains.
The single report has eleven verified original stereo clips; the multiple report has
twelve. Playback context remains separate from every scored 2.4-second interval.

Actual single rank/report outer CLI costs were 231.266/41.547 seconds, and multiple
preparation/rank/report were 23.313/209.156/41.797 seconds. Single preparation reused
the previously prepared identical example in 12.015 seconds; original extraction was
0.044 seconds with 3.787 seconds adapter load. Single/multiple measured rank validation
and scoring were 74.740/62.305 seconds, with approximately 250.2 MB peak working set.
These costs include source/shard verification; they do not imply interactive latency.

The actual catalogue demonstration commands, expanded from the tested helper, were:

```powershell
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-demo-query.json search prepare-query config/local/a06-demo.json
$a06Index = (Get-Content -Raw reports/local/a06-index.json | ConvertFrom-Json).index
$a06Query = (Get-Content -Raw reports/local/a06-demo-query.json | ConvertFrom-Json).query
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-demo-rank.json search rank --index $a06Index --query $a06Query
$a06Result = (Get-Content -Raw reports/local/a06-demo-rank.json | ConvertFrom-Json).result
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-demo-report.json search report $a06Result
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-multiple-query.json search prepare-query config/local/a06-multiple.json
$a06MultipleQuery = (Get-Content -Raw reports/local/a06-multiple-query.json | ConvertFrom-Json).query
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-multiple-rank.json search rank --index $a06Index --query $a06MultipleQuery
$a06MultipleResult = (Get-Content -Raw reports/local/a06-multiple-rank.json | ConvertFrom-Json).result
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-multiple-report.json search report $a06MultipleResult
.\scripts\listen-search.ps1
```

The practical opening command is `.\scripts\listen-search.ps1`; visit
`http://127.0.0.1:8766/` and Ctrl+C stops the listener. The default playable report is:

`reports/local/a06/94fd356a653622972226c45c116b23a008280ac3017b984dbfd1d3d77de03867/index.html`

This primary delivery checkout used only the isolated `codex/a06-local-search` branch;
no temporary worktree owns the only copy of its ignored index/query/report. GitHub PR
delivery follows AGENTS.md; the task's linked PR records review, merge and commits.

## Reuse, fixed resource totals and remaining verification gaps

Both complete catalogue ranks read existing feature shards, with no additional embedding,
and validated every original including excluded parents. Single preparation returned
`reused: true` for the same query/feature identity, retaining original model cost.
Independent comparison confirms all **123 vector arrays retain exact SHA256, byte size
and nanosecond modification time** after repeated validation.

The extra completed-index repetition first failed when Windows denied atomic ledger
replacement. The failed report and its uncertain **120-second reservation** remain
preserved. Repeating the unchanged command refreshed 57 of 72 per-recording receipts,
then its last worker was terminated at the remaining **8.164-second deadline**. That
repeat reports **failed**, not a complete warm-validation pass. Its outer CLI wall
time was 1,343.844 seconds. The already completed index retains all 72 originals/full
coverage; its immutable features are not missing or re-embedded. Additional rank/report/
real-self diagnostic repetitions in the helper were **not run** after exhaustion. The
generated known-target self diagnostic and both original reports had already passed.

[Exact final resource evidence](../manifests/search/resources.json) preserves:

| Lifetime measurement | Consumed / unchanged ceiling |
| --- | ---: |
| Charged worker seconds | 7,204.555 / 7,200 |
| Worker dispatches | 369 / 512 |
| Indexed window attempts | 44,561 / 60,000 |
| Processed window seconds | 110,392.6 / 160,000 |
| Sequential-read audio seconds | 94,227.439 / 180,000 |
| Reserved feature bytes | 84,348,416 / 268,435,456 |
| Query jobs | 6 / 24 |
| Query preparation bytes | 8,701,824 / 67,108,864 |
| Exported clips / bytes | 25 / 64; 18,162,880 / 134,217,728 |
| Final attempts / windows | 1 / 1; 1,368 / 2,000 |
| Acquisition bytes / HTTP attempts | 0 / 0 |

The 4.555-second overrun is actual forced-termination/settlement time, retained above
the unchanged ceiling; it did not authorize another worker or increase an allowance.
Per-action measured worker times total 7,084.555 seconds; the additional 120 seconds
is the retained uncertain reservation. Indexing/validation totals 6,200.875 seconds,
query preparation 57.017, ranking 506.458, reports 101.376, final inference 169.125 and
scoring 6.734; pilot/input/declaration/known-answer costs are separate in the record.
These are worker-accounting timings, distinct from outer CLI time and model-only costs.
The final preservation audit and repeat were slower while additional host load was
observed; its causal contribution was not isolated. No unrelated user process was stopped.

Further A06 compute refuses at the exhausted fixed ledger. Do not reset counters, raise
caps or start a replacement job to repeat this stage. The default listening command
verifies the existing owned bundle independently, with no indexing/inference. This
delivery remains usable from the merged primary checkout. The later catalogue-browser
control gap requires an available compatible Chrome extension; no early D04 listening
judgment is requested.

A01/A02 foundation is complete. A03 ingestion is implemented with a partial 72/120
acquisition outcome. A04 controlled engineering is complete, published human eligibility
partial/unavailable. A05 development comparison is complete. A06 implementation, full
local index, two discovery demos and the single controlled final check are complete;
the extra full-index repeat and later catalogue UI control retain the explicit gaps above.
Human sound relevance, actual Loulou, Linux pretrained inference, arbitrary compressed
master seeking, automatic source/event selection and separation remain unverified/deferred.
This batch ends at A06.
