# B01 — Sound-event selection

19 October 2026 · Windows 11 AMD64 · CPU · Python 3.12.14.

The implementation is delivered: deterministic proposals, independent explicit/manual
selection, native A02 event crops, unordered query handoff, two actual catalogue
searches, verified playback and an audited read-only A06 consumer. **Automatic
selection remains experimental; explicit/coarse selection stays the default.**

The bounded development evaluation is **partial**. Three accompanied reference
regions were initially evaluated with an incorrect zero insertion offset. The saved
predictions remain intact; a declared, zero-inference audit corrects note accounting
and treats three oracle outputs as invalid misses. No replacement model queries or
tuning followed the forty-query cap. Loulou and intended-layer/human relevance remain
unmeasured. B02 is not implemented here.

## Delivered boundaries

The [event owner](../src/similar_sound_search/events/README.md) shares A02 decoding,
preparation and composed maps; A03 original/duplicate validation; A04 construction
truth/scoring; and the unchanged A05 EfficientAT MN04 representation. It introduces
no separator, model download, dependency upgrade, query library or new catalogue grid.

The integration was a separate sub-step (`ee9842e`), following prospective resource
configuration (`1aa9fea`). The development cases/metrics/stop rule were committed in
`1432701` before processing. Initial processing/search code was `e8cb2a7`; declared
boundary/accounting repairs were implemented in `f4e819a`; final report display is
`6567b6f`. [Declarations and evidence](../manifests/events/README.md) retain the hashes.

The compatibility consumer pins A06 index
`d027f2cd5ca817bc320542df16a540346325403bcb967fd248216c8c466731e2`, its original
manifest/recipe/repair/declaration, frozen checkpoint/preprocessing/representation,
native grid, source/group identities and all immutable shards. It verifies original
bytes and feature arrays, stores current consumer audit separately, and never calls
the catalogue feature writer. A06's global `compatible_code`, final-run guards and
exhausted allowance remain closed. An unrelated module can require a fresh consumer
receipt, without feature recomputation. Independent numeric fixtures cover this path.

Explicit B01 context routes new query/source/rank/report work to one fixed ledger and
owned namespace. Omitted context retains A06 defaults; exhausted work is never caught
and silently redirected. All old originals, declarations, predictions, ledgers,
features, frozen adapter bytes and reports remain unchanged.

## Proposals, selection and native crops

The one fixed setting uses 20ms centred frames / 5ms hops, per-channel RMS/positive
spectral flux with channel maxima, 20% relative novelty prominence and a 1e-5 absolute
RMS floor. Absolute-floor activity also seeds isolated quiet attacks. It backtracks
up to 50ms for attacks, requires 40ms release hysteresis below 3% of local peak/floor,
keeps 100ms minimum onset spacing, and caps each authorized region at 30s / 32 proposals.
No analysis downmix/resampling occurs. The next onset does not terminate a prior
event. Overlap, continuous activity, unobserved releases, selection/file edges and the
8s duration cap are explicit warnings. Measurements are heuristics, not probabilities
or instrument/presence labels. [Full contract](../docs/EVENTS.md).

Selection is separate: exact IDs, exact native half-open intervals, or the first three
distinct chronological supported proposals. It never reads retrieval scores or truth.
Native crops preserve channels, rate and samples through A02. Quarter-sample interior
decimal endpoints reproduce integer floor/ceil bounds exactly at rates such as
44.1kHz. No stretching, concatenation, attack/tail normalization or crossfade is applied.
Padding/support and the mismatch with fixed 2.4s candidate windows remain explicit.

The controlled harmonic phrase produced seven proposals, including unresolved merged
spans. Explicit manual intervals `[0,26400)`, `[15600,42000)`, `[31200,57600)` at 24kHz
then extracted its three complete 1.1s notes, including overlapping releases. All
native samples and composed maps were verified. Those manual crops are engineering
truth checks, not automatic-proposal successes or replacement retrieval queries.

The first predeclared real substitute was **Donnie Ozone — Christmas Shopping at the
Dollar Store**, available-file region **10..22s**, native **44,100Hz / stereo**, master
offset unknown. Selection was fixed before catalogue scores. It produced 32 proposals;
the three selected spans were:

| Native half-open frames | Available-file seconds | Status |
| --- | --- | --- |
| `[441000,793800)` | 10.000..18.000 | Duration-capped; release unobserved |
| `[448294,801094)` | 10.165397..18.165397 | Continuous/overlapping activity; duration-capped |
| `[465753,818553)` | 10.561293..18.561293 | Continuous/overlapping activity; duration-capped |

These are distinct nonidentical-PCM, heavily overlapping uncertain spans. **No complete
real note or isolated intended instrument is verified.** Each encoded span is 8s;
candidate-minus-query support mismatch is -5.6s. All have zero model padding. Unknown
master offsets remain null. Accounting-code changes required fresh selection metadata;
exact saved bounds and native audio identities were preserved and reused.

## Corrected development evidence

The [frozen plan](../manifests/events/development.json) contains ten cases and ten
boundary fixtures, one detector setting, coarse/single/multiple/oracle modes,
K=1/5/10, unchanged IoU>=0.5 retrieval scoring, 80ms onset / 120ms release tolerances
and 1e-12 numerical tolerance. Automatic default promotion required note precision and
recall >=0.8, matched attack/tail coverage >=0.95, no retrieval regression in either
automatic mode, and at least one strict retrieval gain. It failed those gates.

Actual note truth uses A04's individual 1.1s note intervals, composed through **actual
insertion positions**, retaining full releases beyond selected edges. The initial
zero-offset assumption was wrong for three cases. Two phrases start at 0.75s and are
cut by the fixed 0..2.4s selection; the planned +12dB reference starts at 3s and has no
designated target inside that selection. The correction was declared in
[boundary-audit-plan.json](../manifests/events/boundary-audit-plan.json) after initial
score inspection. It validates sources and scores saved proposals, without detector
or model inference, changing no cases, settings, predictions or retrieval truth/pools.

| Reference stratum | Proposals | Overlapping truth notes | One-to-one matches | Censored truth notes |
| --- | ---: | ---: | ---: | ---: |
| Clean harmonic | 7 | 3 | 1 | 0 |
| Clean pluck | 3 | 3 | 0 | 0 |
| Clean FM | 7 | 3 | 1 | 0 |
| Clean noise | 10 | 3 | 1 | 0 |
| Harmonic -12dB reference | 13 | 3 | 1 | 0 |
| Harmonic 0dB reference | 9 | 3 | 1 | 2 |
| Planned harmonic +12dB; target absent in selection | 13 | 0 | 0 | 0 |
| Noise 0dB reference | 11 | 3 | 1 | 2 |
| Silent control | 0 | 0 | 0 | 0 |
| Target-absent accompaniment | 13 | 0 | 0 | 0 |
| Ten boundary fixtures combined | 23 | 11 | 9 | separately flagged |

Overall corrected boundary results: **15/109 matches (13.76% precision), 15/32 notes
(46.875% recall), 17 missed notes, 94 false/unresolved proposals, 57 split candidates,
12 merged spans and 76 boundary-censored proposals**. Conditional matched onset/release
absolute errors are 28.0ms / 26.7ms; they do not erase misses. Minimum matched attack
coverage is 0%, tail coverage 42.5%. Silence returns an explicit empty state. The
sustain fixture matches its known selected bounds but still reports an unobserved end;
numeric boundary matching alone does not establish a complete release.

Retrieval uses the same fixed pools/grid/matcher/mean-distance rule, with pitch off:

| Query mode | Hit@1 | Hit@5 | Hit@10 | Render targets recovered @1 / @5 / @10 |
| --- | ---: | ---: | ---: | ---: |
| Coarse reference | 5/8 | 7/8 | 7/8 | 5/9 · 7/9 · 8/9 |
| First selected proposal | 5/8 | 7/8 | 7/8 | 5/9 · 7/9 · 8/9 |
| Several unordered proposals | 4/8 | 7/8 | 7/8 | 4/9 · 7/9 · 8/9 |

These eight candidate-positive cases include the target-absent planned +12dB reference;
all original denominators remain visible. Two explicit absent controls are separate.
Silence abstains in every mode; non-target accompaniment still forces rankings, which
do not establish target presence. The three incorrectly mapped oracle queries are
invalid and counted as misses: the incomplete oracle diagnostic is 3/8 hit@1 and 6/9
recovery@10, with no replacement inference. It is not a complete oracle comparison.

Clean/mixture strata and conditional retrieval localization errors are available in
[results.json](../manifests/events/results.json). Four correlated procedural families,
shared backgrounds and fixed small pools do not establish independent generalisation,
human timbre agreement, commercial-song recall or intended-layer selection. No new
held-out run occurred. Grey1977's scoring exclusion remains unchanged.

## Actual catalogue searches and playback

The completed historical index still contains **72 recordings / 44,025 passages /
123 shards / 67,638,144 vector-file bytes** over 11,152.101 seconds of unique audio.
Both actual B01 searches validate/read those features and exclude the source/duplicate
parent group. Each scores **43,690 windows across 71 eligible groups** and returns
**ten distinct recording candidates**, without a relevance claim.

| Search | Query ID | Result ID |
| --- | --- | --- |
| One event | `9db5979b03ac70bd0bba0832d2350cea6dc1b5e73728437352b65ecccb6bbd74` | `278a11b63ddb8712e74fcd310dd453bf10e21c71a3607fd4c82b4c9083733c19` |
| Three unordered events | `b5a6bc099e4da910341e91124c655fdae6b4ef91392efc08087f19cf8581130e` | `0988c29a0c6bf779940f326d8c3876af34d079ccef4ee823a0a24df1bb777705` |

One necessary query reuse permuted the three examples and repeated one. It returned
the **same query ID, three unique examples and existing feature hash**, without new
inference. Parent exclusions are unioned before PCM deduplication. Independent tests
check duplicate parents and numerical mean-distance equivalence/order invariance.

Open the private delivery bundle with:

```powershell
.\scripts\listen-events.ps1
# http://127.0.0.1:8767/ ; Ctrl+C stops the listener
```

The bundle is
`reports/local/b01/events-78466f787617894f47c9a24025d6c004a5a12af59e9a08cdac49257f27c381fd/index.html`.
It has three HTML pages / seventeen unique verified WAVs, original context and encoded
crops, proposal/selection warnings, separate single/multiple result pages, per-example
distances, timbre mean, pitch/total and duration mismatch. PCM16 conversion/gain and
native source maps are verified; query audio itself retains native float samples.

Chrome passed event-player and real-catalogue candidate **load/play/pause/seek** on
the final single/multiple pages. Candidate playback was observed advancing, paused,
then sought to 2.2s in a 4.4s clip with readyState=4 and no media error. One earlier
tab's reload/screenshot timed out; a fresh tab completed verification. No extension
or driver was changed. This closes the current B01 playback gap, not a human judgment.

HTTP tests verified every new page/WAV hash, full GET, bounded 206 byte ranges,
no-store headers, 404 containment and 416 invalid ranges. The unchanged
`.\scripts\listen-search.ps1` route on port 8766 also served its saved page and eleven
matching WAVs. No A06 compute was invoked. Servers used for QA are stopped afterward;
the scripts restart the saved reports without consuming compute allowance.

## Exercised commands and resumption

[commands.json](../manifests/events/commands.json) retains the actual bounded command
sequence, including refused/failed attempts. The following PowerShell commands use
returned owned paths (all were exercised; do not repeat the entire compute sequence
as a smoke test):

```powershell
$b01Python = '.\.venv\Scripts\python.exe'
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-inputs.json events inputs
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-controlled-propose.json events propose data/runs/events/inputs/controlled.json
$b01Control = (Get-Content reports/local/b01-controlled-propose.json -Raw | ConvertFrom-Json).proposal
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-controlled-manual-current.json events select $b01Control --intervals 0:26400 15600:42000 31200:57600
$b01Manual = (Get-Content reports/local/b01-controlled-manual-current.json -Raw | ConvertFrom-Json).selection
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-controlled-manual-extract-current.json events extract $b01Manual
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-real-propose-1.json events propose data/runs/events/inputs/alternative-1.json
$b01Proposals = (Get-Content reports/local/b01-real-propose-1.json -Raw | ConvertFrom-Json).proposal
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-real-select-current.json events select $b01Proposals --auto
# Explicit-ID path was also exercised: events select PROPOSAL_JSON --ids ID ...
$b01Selection = (Get-Content reports/local/b01-real-select-current.json -Raw | ConvertFrom-Json).selection
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-real-extract-current.json events extract $b01Selection
$b01Events = Get-Content reports/local/b01-real-extract-current.json -Raw | ConvertFrom-Json
& $b01Python -m similar_sound_search --tier starter events prepare-query $b01Events.single_input
& $b01Python -m similar_sound_search --tier starter events prepare-query $b01Events.multiple_input
```

The historical searches used
`events rank --index INDEX_JSON --query QUERY_JSON --receipt RECEIPT_JSON`, then
`events report RESULT_JSON`. The latest current-code receipt is returned by
`reports/local/b01-compatibility-delivery.json`; it validates the same historical
features, with zero re-embedding. The recorded rank outputs bind their producing
consumer receipt. New ranks/reuse consume remaining time/read allowance; no optional
catalogue rerank was performed after delivery repairs.

The comparison was exercised with `events compare` at `e8cb2a7`, and its saved-result
correction with `events audit-boundaries` at `f4e819a`. Their producing-code identities
remain frozen; subsequent code drift is refused. Do not delete progress or reset a
ledger to replace invalid queries. `events known-answer` passed in the B01 namespace.

```powershell
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-event-report.json events event-report data/runs/events/inputs/report-final.json
.\scripts\listen-events.ps1
.\scripts\listen-search.ps1
```

An interrupted WAV-only report copy initially lacked a conversion receipt and failed
explicitly; the repair copies/validates both files and resumes retained work. Old
selection metadata was also correctly rejected after the accounting change; current
records retain identical bounds/audio/features. A concurrent start was refused before
a worker began. All spent charges and original evidence are retained. Native/composed
source corruption, incompatible checkpoint/preprocessing/schema, stale code/bounds,
missing shards or altered media fail with context; no covert index rebuild occurs.

Loulou remains ready through `events propose config/event_source.example.json` once
actual audio is supplied at its explicit excerpt path. Match its 0..22s example to
the actual available file; keep version/offset uncertainty. Only a verified full-track
source may use 218..240 available-file seconds. No user-library scan or new acquisition
was performed.

## Resources, checks and preservation

The one B01 ledger is retained at `data/runs/events/`. [Resource evidence](../manifests/events/resources.json)
includes retries, conservative reservations, processing counts and timing by action.

| Counter | Charged | Ceiling |
| --- | ---: | ---: |
| Aggregate compute-worker seconds | 1,231.445 | 3,600 |
| Workers | 126 | 256 |
| New feature windows/events | 48 | 4,096 |
| New feature allocation | 3,088,384 bytes | 64 MiB |
| Processed feature audio | 95.185s | 12,000s |
| Audio validation/read equivalents, including repeats | 70,153.465s | 90,000s |
| Query/rank jobs | 5 | 16 |
| Comparison batches / cases / mode queries | 1 / 10 / 40 | 1 / 10 / 40 |
| Proposal inputs / events | 22 / 148 | 32 / 1,024 |
| Query preparation reservation | 23,103,488 bytes | 64 MiB |
| Event/fixture preparation reservation | 20,816,320 bytes | 128 MiB |
| Playback clip allocations / reserved bytes | 58 / 54,287,936 | 128 / 128 MiB |
| Managed output reservation | 104,847,449 bytes | 256 MiB |
| HTTP attempts / downloads | 0 / 0 | 0 / 0 |

There are no pending B01 worker reservations. Read seconds count repeated validation
of available-file durations, not wall time or additional unique catalogue hours.
Three necessary consumer integrity passes reflect initial and repaired consumer
identities; none re-embeds a catalogue passage or finishes A06's failed repeat.
[The accounting declaration](../manifests/events/accounting-audit-plan.json) adds
343.247 seconds of initially omitted parent-original hash reads once, without refunds;
future B01 preparation charges them directly. Observed native peak working set at
feature/rank checkpoints was **299,352,064 bytes**, below the configured 1 GiB ceiling;
other stages retain allocation preflight estimates. CPU/numerical concurrency remains
one, workers 120s, input/decoded/output 256 MiB, combined managed storage/free headroom
4 GiB. Original A03/A05/A06 exhausted allowances remain untouched.

Validation passed:

- **168 offline tests**, final quiet full run 85.923s; no model downloads/delivery-ledger use.
- Ruff lint and format checks (69 Python files), `git diff --check`.
- Offline editable wheel build/install with `--no-index --no-deps --no-build-isolation -e .`, and `pip check`.
- Starter offline smoke in a separate owned project root to preserve earlier diagnostic files.
- B01 known answers, fixed comparison/audit, both real catalogue searches and one query reuse.
- Native samples/maps, HTTP/media integrity, containment/ranges and Chrome controls.

Exact standard validation commands are in [RUNTIME.md](../docs/RUNTIME.md#validation).
The starter smoke used `sound-search --root reports/local/b01-smoke-project --tier starter smoke`
after copying only the resource configuration and missing-reference manifest into that
temporary root. Installation, tests, browser/HTTP QA and preservation-audit costs are
separate from B01 compute-worker accounting. Two localhost timeout/retry tests failed
during concurrent I/O; unchanged tests passed in the final quiet full run. No hosted
GitHub Actions workflow is defined, so no hosted CI pass is claimed.

The before/after audit verifies **7,944 earlier files / 1,038,273,179 bytes**, with
**zero changed hashes, sizes, modification times or missing files**. It covers private
audio/features/reports/ledgers, prior public evidence/manifests/prompts, frozen adapters
and configuration. [Sanitized proof](../manifests/events/preservation.json) binds the
retained private baseline. New ignored artifacts remain in this primary delivery
checkout and survive branch cleanup; a fresh clone requires matching private assets.

## B02 handoff

Keep explicit/manual crops as the reliable default and automatic proposals experimental.
B02 should compare any optional isolation/extraction with the unchanged native/no-isolation
baseline, under its own prospective finite plan. Validate actual insertion/region geometry
before inference; retain target-absent and censored cases, parent exclusions and duration
mismatch. Do not reuse these inspected cases as a new holdout, reset prior ledgers, or
claim that the three real spans isolate the desired sound. Loulou still needs actual
audio/version/offset evidence. Human relevance review remains D04; no judgments were
requested for this engineering delivery.
