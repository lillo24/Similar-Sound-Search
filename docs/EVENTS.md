# B01 sound-event selection

B01 adds bounded event proposals and explicit selection to the existing original-audio
preparation/search path. It does not isolate an instrument or establish the intended
sound layer. Automatic proposals remain experimental unless the prospectively frozen
development rule supports them. Separation is B02; query-library management and further
pitch work are B03. The first required listening review remains D04.

## Integration boundary and prospective limits

The first implementation sub-step explicitly separates a B01 search accounting context
from the unchanged default A06 context. New artifacts belong to `data/runs/events/`,
`data/features/events/`, `reports/local/b01/` and `manifests/events/`. A06 commands must
continue using their original closed ledger and final-check authorization. No caught
exhaustion error redirects work into B01.

The B01 consumer will validate the historical A06 index/recipe and original execution
repair, frozen representation/checkpoint/preprocessing, grid, sources/groups and shard
identities before read-only use. Current consumer audit identity stays separate from
historical feature identity. The old whole-tree A06 final-run guard is not relaxed.
An unrelated module may require a fresh consumer receipt, never feature recomputation.
`events/compatibility.py` pins the completed historical index, manifest, repair and
declaration; checks unchanged preprocessing/model/scorer modules and original protected
function AST proofs; verifies every source byte hash and immutable feature array; and
writes a B01-only consumer receipt. Each search revalidates the receipt's metadata and
current consumer code, then verifies the originals and arrays it reads. No index writer
or adapter is called during compatibility. Changing consumer code requires a new receipt.

`events.context.Context` supplies the fixed B01 output paths and explicit cumulative
accounting to shared query/source/rank/report helpers. Their default remains A06. The
boundary tests use temporary ledgers, independently calculated vector distances, stale
receipts and relevant/unrelated code drift. The old execution-repair test now supplies
its historical code map explicitly and asserts that the current larger tree is rejected;
this is the required historical-guard behavior, not a relaxed A06 exception.

Numeric limits in `config/events.json` are committed before audio processing, including
the pilot. The one persistent B01 allowance is 3,600 worker seconds, 256 dispatches,
4,096 new feature events/windows, 12,000 processed feature-audio seconds, 90,000 decoded
source seconds, 64 MiB feature allocation, 16 query/rank jobs, 64 MiB query preparation,
128 clips/128 MiB playback, 32 proposal inputs/1,024 proposed events, 128 MiB event
preparation and 256 MiB total new managed output. Each proposal region is at most 30s,
with at most 32 events and three automatically selected examples. Existing starter
worker, memory, input/output, combined-disk and free-space ceilings remain unchanged.
No HTTP/download allowance exists. Interruptions retain charges. Old ledgers, audio,
features, declarations and results are immutable inputs, not new B01 work.

The initial detector shortlist has one deterministic envelope/flux configuration.
The development cases, decision rule, metrics/tolerances and stop rule will be committed
before comparison scores are inspected. Budget is reserved for both real-catalogue
queries, original playback and one necessary reuse check; optional repetitions stop
after sufficient verification. Installation, tests and preservation audits are reported
separately from the finite compute ledger.

## Detector and extraction contract

`events propose` accepts a `b01-source-1` JSON: explicit `path` under project
`data/audio`, `region` with integer `start_frame`/`end_frame` or decimal
`start_seconds`/`end_seconds`, and optionally `context` (A02) or `parent_record`
(prepared A02), never both. An optional `sha256` pins the available file. Regions
are half-open, at most 30 seconds, with no extra context read into analysis. Decoding
is full sequential/native float32 through A02; full-source validation reads are charged.
Only explicit project input locations are considered; no user-library scan occurs.

The deterministic `envelope-flux-1` setting uses centred 20ms Hann/RMS frames, 5ms
hops, maximum per-channel RMS and maximum per-channel positive magnitude spectral
flux. It does not downmix or resample. Flux prominence is 20% of region maximum
(at least the 1e-5 RMS floor); absolute-floor activity rises also seed quiet isolated
attacks. Peaks are at least 100ms apart. Earliest attacks win within that gap; at most
32 chronological proposals are retained, with the omitted count explicit. Low-energy
analysis-frame counts expose activity below the relative envelope threshold.

Attack backtracking is at most 50ms, including the half analysis frame. Releases
require 40ms below max(1e-5, 3% of that event's local peak); support includes the
analysis frame. The next onset never sets an event's end. Continuous accompaniment
can therefore produce overlapping long spans: `attack_in_continuous_activity`,
`overlapping_activity_unresolved` and `release_not_observed` explicitly withhold
completeness. Selection/file edges and the 8-second cap are censored, not observed
releases. Short transients below 60ms remain visible but are unsupported query crops.
Slow attacks, modulated/noise events and quiet overlapping layers can still split,
merge or be missed; the development records retain those failures. No energy or
novelty measurement is an instrument label, calibrated confidence or target-presence test.

`events select` requires exactly one of `--ids ID ...`, `--intervals START:END ...`
(native integer frames), or `--auto`. Manual intervals remain usable independently
of detector quality. Automatic selection takes up to three distinct chronological
supported spans, with uncertainty retained and no truth, filename or score input.
Explicit reordering reproduces the same selection; playback retains temporal order.
`events extract` verifies native samples/channels/rate using A02 immutable bundles
and maps. It emits single and unordered-multiple `a06-query-input-1` handoffs with a
versioned B01 binding. No concatenation, time stretching, crop normalization or
crossfade is applied. Quarter-sample interior decimal seconds make A02's floor/ceil
crop exact even for nonterminating 44.1kHz fractions; the stored authority is the
integer half-open interval. Crop playback and original context are separate.

Query identity deduplicates selected PCM, unions parents before deduplication, and
keeps the existing stable mean of per-example distances. Permutation tolerance is
1e-12. Discovery excludes every known source/duplicate parent. Pitch stays off;
existing A06 optional pitch behavior is untouched. Actual support, adapter padding
(right zeros below 1,024 resampled 32kHz frames) and mismatch with fixed 2.4s
catalogue windows are recorded. The frozen matcher still applies its own declared
mean-channel preprocessing; this detector's stereo-safe analysis does not alter it.

## Fixed development decision

`manifests/events/development.json` was committed before B01 scores. It contains
four clean alternate-performance cases (one per development procedural family),
four accompanied-reference cases (harmonic -12/0/+12dB and noise 0dB), and two
absent controls (exact silence and non-target accompaniment). Each uses the same
original candidate pool for coarse, first proposal, up to three unordered proposals,
and oracle-bound diagnostic modes. Accompanied references use a constructed
exact-instance mixture's first complete phrase; retrieval candidates contain the
alternate performance, with shared backgrounds explicitly correlated. The original
A04 protocol/suite/truth are read-only; a self-hashed subset relabels B01 strata.
No held-out predictions are run or used to select settings.

Individual A04 note bounds include 1.1s releases and 0.65s inter-attack overlap.
They are composed into the selected insertion for proposal evaluation. Retrieval
truth still refers to the complete 2.4s rendered phrase; K=1/5/10 and IoU>=0.5 use
the unchanged A04 scorer. Note matches maximize one-to-one cardinality under
80ms onset/120ms offset tolerances, then minimize total boundary error. Attack
coverage uses the first 25ms and tail coverage the final 200ms. Unmatched proposals
whose onsets fall inside truth are split candidates; spans containing two complete
truth notes are merge diagnostics. These diagnostics add no true-positive credit.
All misses, absent outputs and abstentions remain in their proper denominators.

Ten small B01 fixtures add independently known isolated, long overlapping release,
slow attack, short transient, noise, vibrato, close notes, anti-phase stereo,
censored sustain and silence boundaries. Seeds from these related recipes do not
provide independent timbre generalisation. Oracle crop bounds are evaluation-only.

Automatic selection can become default only if note precision/recall both reach
0.8, minimum matched attack/tail coverage reaches 0.95, both automatic query modes
are no worse than coarse hit@1 and recovery@10, and at least one retrieval measure
strictly improves. Otherwise explicit/coarse stays default and proposals remain
experimental. One fixed batch stops without tuning. A comparison batch counts as
one of the 16 query/rank jobs and additionally charges ceilings of one batch, ten
cases and forty mode queries. Each actual catalogue query preparation/rank charges
its own job; inference windows, reads, workers, bytes and retries are also charged.

## Commands and safe resumption (Windows)

Use the pinned local environment and `--tier starter`. Each successful command writes
an owned JSON summary; read its returned path for the next command. For example:

```powershell
$b01Python = '.\.venv\Scripts\python.exe'
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-inputs.json events inputs
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-controlled-propose.json events propose data/runs/events/inputs/controlled.json
$b01Proposal = (Get-Content reports/local/b01-controlled-propose.json -Raw | ConvertFrom-Json).proposal
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-controlled-select.json events select $b01Proposal --auto
# Explicit equivalent: events select $b01Proposal --ids EVENT_ID ...
# Explicit manual path: events select $b01Proposal --intervals 0:26400 15600:42000
$b01Selection = (Get-Content reports/local/b01-controlled-select.json -Raw | ConvertFrom-Json).selection
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-controlled-extract.json events extract $b01Selection
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-comparison.json events compare
& $b01Python -m similar_sound_search --tier starter --report reports/local/b01-compatibility.json events compatibility
```

Real demonstrations use `alternative-1.json` etc. from the frozen list, stopping at
the first with at least two distinct usable proposals before any catalogue search.
Prepare the returned `single_input` and `multiple_input` using `events prepare-query`.
Use `events rank --index INDEX_JSON --query QUERY_JSON --receipt RECEIPT_JSON`, then
`events report RESULT_JSON`. `events event-report INPUT_JSON` accepts
`b01-report-input-1` with `extraction`, `single_report`, `multiple_report` paths,
all owned B01 artifacts. The report contains source/region, proposals/selection,
uncertainty, original context and encoded crops plus separate search/score pages.

```powershell
.\scripts\listen-events.ps1
# Open http://127.0.0.1:8767/ ; Ctrl+C stops the listener.
# A06 playback remains independent: .\scripts\listen-search.ps1 (port 8766).
```

Repeat the same failed command to resume retained complete units, never delete a
ledger to gain allowance. Immutable corrupt/stale inputs fail with context. Restore
the exact missing input rather than rebuilding A06 features. A new current-code
receipt revalidates sources/shards; unchanged feature bytes remain historical.
Rank repeats revalidate actual originals/shards. Comparison progress rejects code
or plan drift; no second batch is authorized by a restart. Unfinished charged
units may be retried within the remaining ceilings. No B01 command exposes A06's
final-run or model acquisition. The idle listener performs no compute and exposes
only exact bundle HTML/media paths, with hashes and bounded byte ranges.
