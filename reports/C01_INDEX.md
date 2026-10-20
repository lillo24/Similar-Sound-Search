# C01 passage and component index

Delivery checks are in progress. Original audio and pitch off remain defaults.
The fixed development batch is closed; the admitted 4.8s/1s experimental original
bank is being constructed. No C02 retrieval aggregation has been implemented.

## Declaration and producing versions

Pulled `main` to `4b0fbf3` and used isolated branch `codex/c01-index` in the primary
checkout. There was no extra worktree. The prospective protocol/configuration was
committed as `f664db2`, the implementation as `fb3f194`, and actual source/native
geometry as `c1e4bd4`, before C01 feature inference. The protocol is
[`manifests/indexing/protocol.json`](../manifests/indexing/protocol.json); actual
72-source identities, native dimensions, grid estimates and inspected generated
inputs are in [`geometry.json`](../manifests/indexing/geometry.json).

Plans pin full producing versions separately from samples-affecting identities.
Display titles, timing and unrelated coordinator hashes do not enter feature
keys. An immutable snapshot pins the exact committed row set; progress, pending
reservations and failures remain separate. Source population changes require an
explicit new plan. General invalidation, scheduling and cache management remain
C04 work.

The one additional duration is experimental. Duration-only development uses a
common .5s hop; production 1.2s/.5s versus 4.8s/1s are combined policies with
different opportunities. The legacy 2.4s/.25s default is unchanged.

## Fixed development result and geometry correction

Ten prospectively selected cases / thirty case-bank arms used four familiar A04
development mechanisms, two candidate performances each, and an additional short
file. None is a fresh holdout or a human timbre judgement. Six alternate-performance
cases are primary; exact-waveform, silence and absent-target controls stay separate.
Native WAV reconstruction and independent isolated-waveform FFT correlation
verified actual insertion/support before any feature inference.

| Common-.5s development grid | Alternate-family hit@1 | Hit@3 | Paired gains/losses versus 2.4s | Strict full-2.4s containment opportunities |
| --- | ---: | ---: | ---: | ---: |
| 1.2s | 5/6 | 6/6 | 0 / 1 | 0/10 |
| 2.4s | 6/6 | 6/6 | 0 / 0 | 5/10 |
| 4.8s | 5/6 | 6/6 | 0 / 1 | 10/10 |

The initial support counter included the .3s short-file source in full-query
cases, producing 1/11, 6/11 and 11/11. Those immutable results remain intact.
[`support-verification.json`](../manifests/indexing/support-verification.json)
re-enumerates only geometry under the already-declared full-2.4s criterion,
retains all ten cases/rankings/failures/localization results, and verifies that
admission is unchanged. Its bounded offline verifier was charged to C01 and
committed as `b099e55`; no feature, score, query, threshold or source was replaced.

Both candidates met the predeclared allowance of at most one primary-case loss.
The long policy won the full-event-support rule and fit projected time/read/
feature limits with delivery reserves. This admits an engineering indexing policy;
it does not show improved source consistency. Containment is not localization
accuracy. IoU, boundary error and winning-passage overlap remain separate per-case
measurements, including partial short-file support. Absent queries still force a
ranking because there is no calibrated presence threshold; silence fails explicitly.

## Components and query boundary

Original-only indexing remains the default. Existing B02 broad HPSS outputs for
Donnie Ozone's 9..17s region were validated and reused, with harmonic/percussive
names. The same contract was exercised on one generated 8s mixture. Each of four
component plans contains thirteen rows: fifty-two component windows in total.
Only the controlled mixture required new DSP: one processing input / eight
separator-input seconds. These are region components, not identified instruments
or full-track stems. Generated controls remain outside discovery coverage.

The real broad receipt records a cue but its actual HPSS method ignores cue
samples. C01 retains that cue, full transformation/config/DSP/output identities,
all ancestry and native maps. The existing guided receipt actually consumes a
cue and was explicitly refused as a universal component. Nonfinite, clipped,
near-silent, missing, mismapped or altered components fail without an original/
zero-vector fallback. Component examination plays the original mixture, with
derived audition separately labelled.

C01 reads the exact original B03 revision
`c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3`
and materialization
`0ebb77012137c086e4cb1f72298e16446b33d96da2de28d7c9ccc5d663a03036`.
The mutable B03 head has pitch enabled and is deliberately not selected. The full
Loulou 218..240s original mixture and 217..241s context remain intact; native
event bounds are 9,613,800..10,584,000. Technical availability does not verify
recording version, marked-version alignment, master offset, intended layer,
rights or complete notes. This query does not add a discovery recording.

The read-only B03 adapter charges C01 and preserves immutable local bindings,
source/cue identities and every contributing exclusion before unique-PCM
deduplication. Missing materialization has an explicit C01-owned recipe-import/
derivative path. Its optional `owner.feature_root` hook leaves B03 defaults and
semantic feature keys unchanged. No B03 worker/allowance is reopened.

## Resource and preservation boundary

All new processing is offline, CPU-only and uses the existing pinned checkpoint/
dependencies. The fixed caps are 7,200 worker seconds, 512 workers, 180,000
source-read seconds, 26,000 new feature windows, 65,000 feature-audio seconds,
128 MiB reserved feature output, sixteen query jobs, 64 clips / 128 MiB clips and
512 MiB new managed output. Pilot windows, generated queries, processing,
failures and retries share this allowance. Starter 120s/1 GiB/256 MiB/4 GiB
limits, numerical concurrency one and free-space headroom remain unchanged.

Preflight observed 1,645,096,960 available Windows commit bytes, distinct from
5,736,837,120 free physical bytes. The largest source decodes to 80,353,728 bytes;
its configured worker allocation estimate is 811,486,528 bytes. Cold real pilot
costs included complete sequential decode/hash, process/model startup, metadata
and publication: four units each, 50.376s short and 54.641s long. Their charged
reuse passes were 7.078s and 6.985s, with zero re-embedding. The pilot used 788
real windows; all development features/queries bring the pilot total to 1,088.

New namespaces are `data/indexes/c01`, `data/features/indexing`,
`data/runs/indexing`, `data/audio/indexing`, `manifests/indexing` and
`reports/local/c01`. They participate in shared inventory. Metadata has its own
32 MiB counted subcap inside a pre-reserved 32 MiB envelope. Source verification
is full sequential decoding/hashing per bounded unit, including reuse; compressed
random seeking is not assumed. One lazy adapter is shared within each worker.

The history baseline inventories 9,590 files / 1,302,972,805 bytes, including all
old ledgers/features/reports, root MP3, configs, frozen model modules, pitch and
line-ending policy. Only declared C01 namespaces and its new lock are excluded.
Final verification and delivery totals will be recorded below. A03's 72/120
shortfall and unknown master offsets are preserved. A06 remains 44,025 rows /
123 original shards, covering 11,152.101338 unique available-file seconds;
105,660 overlapping encoded seconds are not unique catalogue duration.

## Validation, playback and C02 handoff

The initial full offline run passed 240 tests in 140.809s; the final component
extension passed all 23 C01 tests in 20.927s. Pinned editable setup with
`pip install --no-index --no-deps --no-build-isolation -e .`, `pip check`, Ruff,
PowerShell listener syntax and an isolated starter smoke passed. The isolated
smoke is plumbing evidence and does not make a claim about delivery query
availability. Final checks and native/HTTP/browser evidence remain to be added.

Exact commands, resume/verify rules and the listener startup are in
[`docs/INDEXING.md`](../docs/INDEXING.md). The new listener uses 8770; existing
8766–8769 bundles remain separate. No deployment or human relevance review is
part of C01.

C02 should open an explicit snapshot/bank-record hash, then use
`indexing.reader.read_bank` and `rows` for float32 arrays, stable row identities,
native signal/original bounds and source/component ancestry. Do not identify a
population by bank policy ID alone. Complete eligible group winners and their
per-example distances are retained before top-ten truncation. Distances are
unordered mean-example cosine, lower-better, with pitch zero and no presence
threshold. Each bank is searched independently. C02 must decide calibration,
opportunity bias across durations/hops, multiple-event combination, shortlist
coverage and overlap aggregation; it must preserve source/duplicate/cue exclusions
and avoid treating correlated banks/components as independent votes. C03 owns
query-dependent extraction/refinement. C01 does not start either stage.
