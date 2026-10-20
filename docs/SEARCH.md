# A06 local passage search

B01 adds [event-selection commands](EVENTS.md) and an explicit audited read-only
consumer of these historical features. A06's exhausted ledger and final-run guard
remain closed; saved A06 playback through `listen-search.ps1` is still independent
of compute. Use B01 commands for new event queries and receipts.

A06 uses the unchanged A05 representation and separate `config/search.json` search policy.
Original recordings are decoded serially; 2.4-second windows advance by 0.25 seconds
with one unique end-aligned tail. Compact immutable shards hold at most 512 vectors.
A development-only 64-window cost pilot confirmed this batch size: 2.135 seconds of
extraction, 326,160,384 bytes peak working set. No catalogue rankings or held-out
scores informed that decision. No second window duration was introduced.

The fixed A06 accounting owner is `data/runs/search/`; there are no alternative job names.
Its lifetime ceilings are 7,200 worker seconds, 512 workers, 60,000 catalogue window
attempts, 160,000 processed window seconds, 180,000 sequential-read audio seconds,
256 MiB feature allocation, 24 query jobs, 64 MiB query preparation, one resumable
final evaluation (2,000 window attempts), 64 pilot windows, and 64 playback clips
within 128 MiB. Charges precede work and uncertain interrupted work is retained.
Transfer allowance is zero: restore the already pinned checkpoint/inputs explicitly.
Existing A03/A04/A05 allowances and the starter per-worker/input/disk ceilings stay fixed.

The full catalogue sizing estimate is 44,025 MN04 vectors (67,622,400 float32 bytes).
The new allowances cover one full index, validation/reuse, the final check and a small
playable demonstration with conservative interruption headroom. They do not authorize
new acquisition, another development comparison, paid compute or deployment.
Installation, inference, validation, indexing and report costs are recorded separately.
See [measured evidence](../reports/A06_SEARCH.md) for actual coverage and final results.

The delivery ledger has now consumed this fixed worker-time allowance, including
retained interruptions and a 4.555-second forced-termination overrun. Further A06
compute commands refuse; do not reset the ledger or raise its ceiling. The complete
index, both query/results and exported reports remain usable evidence. The independent
`listen-search.ps1` / `search serve` listener verifies playback bundles without inference
or charging a new compute job. The extra full-index repeat stopped after 57 refreshed
recording receipts; both earlier complete catalogue ranks reused existing eligible
shards and single-query preparation reused its features. [Resource evidence](../manifests/search/resources.json)
retains the exact costs and unrun additional repeats.

## Commands, inputs and restoration

Use the pinned [ordinary/optional setup](MATCHERS.md#setup-and-explicit-commands).
Stop running console commands/report servers before reinstalling the Windows console
launcher. Runtime requires the original 72 files, matching A03 private ready registrations,
prepared bundles, generated A04 audio and the exact local MN04 checkpoint. Git only
restores public metadata. Restore those existing assets to their recorded project paths
from the delivery checkout/backup, preserving hashes and registrations. No A06 command
acquires audio/weights; do not restart the exhausted A03 or A05 jobs. Missing or changed
inputs fail with their step/identity. Optional CPU inference was exercised on Windows.

Global flags precede `search`. Run these from the delivery repository root:

```powershell
.\.venv\Scripts\sound-search.exe --tier starter search pilot
# Fix substitute crops without rankings; generated correctness fixture is separate.
.\.venv\Scripts\sound-search.exe --tier starter search demo-inputs
.\.venv\Scripts\sound-search.exe --tier starter search diagnostic-inputs
.\.venv\Scripts\sound-search.exe --tier starter search known-answer
# Commit implementation/configuration after development checks, then declare once.
.\.venv\Scripts\sound-search.exe --tier starter search declare
.\.venv\Scripts\sound-search.exe --tier starter search final-run
.\.venv\Scripts\sound-search.exe --tier starter search final-score
# Full available originals, not thirty-second analysis derivatives.
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-index.json search index
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-demo-query.json search prepare-query config/local/a06-demo.json
$a06Index = (Get-Content -Raw reports/local/a06-index.json | ConvertFrom-Json).index
$a06Query = (Get-Content -Raw reports/local/a06-demo-query.json | ConvertFrom-Json).query
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-demo-rank.json search rank --index $a06Index --query $a06Query
$a06Result = (Get-Content -Raw reports/local/a06-demo-rank.json | ConvertFrom-Json).result
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a06-demo-report.json search report $a06Result
# One practical opening command; Ctrl+C stops its loopback-only listener.
.\scripts\listen-search.ps1
```

`prepare-query` requires an explicit JSON input, not an implicit library/name scan:

```json
{
  "schema_version": "a06-query-input-1",
  "label": "Explicit selected sound",
  "examples": [{"path": "data/audio/incoming/permitted.wav", "start": "2", "end": "4.4", "context": "config/local/context.json"}]
}
```

Each example supports `path`, paired `start`/`end`, and either A02 `context` or a
self-hashed prepared `parent_record`. Explicit external files are supported; private
paths stay local. A02 floors crop start and ceils end to native frames, preserves channels
and the complete selected content, and composes lineage back to the root original.
Query preparation keeps the current file's native rate; the unchanged adapter performs
its own documented mean/resampling/padding. No overlong content is truncated: select
at most thirty seconds/example, at most eight examples. A mixed excerpt can emphasize
accompaniment. Equal selected PCM examples collapse; the mean of unique per-example
distances is order-invariant. Results retain each distance and duration mismatch.

For multiple examples replace the preparation input with `config/local/a06-multiple.json`.
The preset substitute uses the first sorted development-side recording and first non-silent
scheduled 2.4s crop from starts 2,4.4,… below thirty seconds, then the adjacent example;
this is an engineering intent, without a verified instrumental layer or perceptual label.
The generated positive uses `--engineering config/local/a06-engineering.json` on `index`
and `--include-self` on `rank`; it never enters real discoveries.

Loulou is missing/unverified. A ready-to-run **unrun** full-file selection command is:

```powershell
# Only after full marked-version audio and context/offset evidence are supplied.
.\.venv\Scripts\sound-search.exe --tier starter prepare data/audio/incoming/loulou-marked-full.wav --rate 44100 --channels preserve --start 218 --end 240 --context config/local/loulou-context.json
```

Inspect the actual file first and replace `44100` with its native rate; never apply 218s
to a short supplied excerpt. For an approximately 22s marked excerpt use its entire
available file as the query, retaining unknown offsets. No filename authenticates Loulou.

## Index/result and pitch contracts

Windows use integer native frames: duration ceils `milliseconds*rate/1000`, hop rounds
to nearest native frame (half upward); one unique final tail ends exactly at the source
end. Files shorter than 2.4s use the entire available file, without extending result bounds
for model padding. All mono/model-rate processing is transient, after original validation.
Index manifests bind recording/asset, byte/PCM, source record/provenance, decoder,
representation/checkpoint and separately versioned search policy. Shards are immutable
float32 matrices with shared bounds, hashes and finite/shape checks; JSON stays <=1 MiB.
Code identity canonicalizes Python line endings; frozen A05 adapter source hashes still
use their exact `.gitattributes`-preserved bytes. No database/ANN service is used.

One exact mean timbre distance selects one best **scored** passage per recording/known
duplicate group. Ties use score, recording ID, start, end. Titles/artists/source truth never
affect similarity. Parent originals and established byte/PCM/provider-family groups are
excluded, across all examples. An artist's other recordings remain eligible. Unknown
edited/lossy copies remain a limit. `--include-self` explicitly produces a diagnostic.
Results are lower-better ranked candidates, without calibrated probabilities/presence.

Pitch is off by default. `rank --pitch-weight 0.03` enables a separately visible contribution
up to 0.05 cosine-distance units. Timbre still selects each recording's passage; pitch only
orders those passages. The 8kHz classical estimator requires at least two stable 2048-frame
blocks, >=.75 narrow fundamental spectral concentration, >=.9 autocorrelation, <=.5 semitone
spread/agreement, in 50..500Hz. Silence, noisy/polyphonic/unstable/out-of-range inputs abstain.
Penalty is `weight*mean(min(1,abs(semitone difference)/12))`; any example/candidate abstention
means zero pitch contribution. It is a small development/known-note diagnostic, not Set B
pitch completion or part of the final held-out check. The acoustic alternative is explicit
`--method acoustic` for both index and query; it uses Euclidean distance and never silently
replaces EfficientAT.

## Playback, reuse and recovery

Playback crops come from a verified full sequential **original mixture** decode, preserving
native channels/rate/time. PCM16 WAV is browser-compatible; conversion rounds to nearest
integer without dither. Only a peak above PCM16 range receives a constant declared attenuation
to 32767/32768; gain is visible and stored. No clipping, loudness normalization, model-rate
playback, separated stems or compressed seeks are used. Exported samples must exactly equal
the declared converted original crop. Query playback composes A02 maps back to its root.
Scored/selected intervals and +/-1s clipped playback context are distinct; clip zero has an
exact original-frame offset. Unknown offsets visibly use available-file/excerpt-relative
labels, including provider full tracks with unverified external master alignment.

HTML and media live under ignored `reports/local/a06/RESULT_ID/`. `search serve FILE --port 8766`
or `listen-search.ps1` serves only that verified bundle on `127.0.0.1`, through exact HTML/media
allowlists, with no-store responses. It never exposes the repository, private records or
arbitrary paths. Single bounded byte ranges on exported WAVs support browser seeking;
multipart/malformed/out-of-file ranges fail with HTTP 416. Missing/stale media produces
a visible failure. The idle page runs no
index/inference job and needs no network/login/telemetry. Direct relative-file media also
works when the browser permits local files; exercised evidence uses the loopback server.

Repeat `index`, `prepare-query`, `rank` or `report` with the same inputs to validate/reuse.
Every repeated sequential decode/worker still consumes finite A06 time/read allowance;
completed features retain cold costs. Interrupted missing shards resume without resetting
charges; failures have nonzero exit and explicit partial coverage. Default ranking refuses
a partial index; `--allow-partial` consciously returns its measured union/recording coverage.
Do not delete a ledger, change jobs or raise caps. Corrupt completed inputs/shards/clips fail
and remain available for inspection; quarantine only the named owned damaged artifact before
resuming. Old indexes/results remain evidence when code/recipe identity changes.

On Windows, another process holding an accounting/publication file open can make atomic
replacement fail with an access-denied error. Preserve the explicit failed report and
uncertain reservation, close the reader and repeat the unchanged command. Inspect ledger
snapshots after an operation finishes; do not poll a live ledger with a file-locking reader.

The final declaration supplies the strengthened A04 held-out guard. Original choice remains
A05; an arbitrary `stage:A06` object fails. `final-run` only uses frozen EfficientAT, exact
A05 grid/preprocessing/cosine, pitch zero and empty refinement. Predictions are saved before
truth scoring, retaining all eighty query denominators. Technical resume uses the same
immutable declaration/run and retained charges; re-scoring is the same experiment. Code or
configuration drift refuses further inference. Document any inspected results before a fix;
do not select/tune models using final outcomes. Human Grey1977 and Loulou relevance stay
unavailable and D04 remains the first required listening review.


## Recorded execution repair after final-score inspection

The first full-catalogue rank exceeded one 120-second worker. Ranking now validates
and scores four recordings per serial worker, persisting bounded progress before the
next worker. Distance, mean aggregation, tie/exclusion/pitch rules and scored intervals
are unchanged. A repeat verifies sources/shards and retains the same result identity.
No feature is re-embedded by this repair and all interrupted work remains charged.

`manifests/search/execution-repair.json` records that held-out scores were already
inspected, the exact old/current executing-code maps, the unchanged declaration/index
identities, and complete original source proofs. Runtime checks those original bytes
against the frozen declaration and compares syntax trees of the unchanged math,
extraction and scorer functions. Only the four listed coordinator/identity modules may
differ; additional drift fails. The original pre-inference declaration and saved final
predictions/results stay unchanged. This is a technical execution repair, not another
held-out experiment or model/algorithm choice. Physical workers still have 120 seconds,
concurrency one, and the original A06 lifetime caps.
## Optional B02 query processing

[B02](SEPARATION.md) supplies its own explicit context, validated transformation
handoff, fixed ledger/output roots and newly audited read-only A06 consumer receipt.
The shared query hook unions original/cue ancestry before identical-PCM dedup. Omitted
context remains A06; `parents()`, feature identity, distances/ties, pitch-off default,
historical final-run guard and original report page are unchanged. B02 renders derived
queries separately and always plays catalogue candidates from original mixtures.
