# C01 passage and component index

C01 implementation and delivery verification are complete. Original audio
and pitch off remain defaults. The admitted 4.8s/1s experimental original bank
contains 10,914 windows / 123 shards across all 72 recordings. No C02 retrieval
aggregation has been implemented.

[`C01_INDEX_EVIDENCE.json`](C01_INDEX_EVIDENCE.json) contains the sanitized bank,
snapshot, query, development, execution, accounting and verification records.
Private arrays, audio and local playback files remain in the delivery checkout.
Delivery uses [PR #20](https://github.com/lillo24/Similar-Sound-Search/pull/20)
into `main`; that PR is the durable head/check/merge record.

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
Final preservation verified 9,589 byte-identical files and the exact documented
C01 navigation addition to `config/README.md`, with no other changed, missing or
unexpected files. Runtime configuration JSON is unchanged. A03's 72/120 shortfall
and unknown master offsets are preserved. A06 remains 44,025 rows / 123 original
shards, covering 11,152.101338 unique available-file seconds; 105,660 overlapping
encoded seconds are not unique catalogue duration.

Feature production finished with zero failed units at 2,100.494 aggregate worker
seconds / 168 workers. C01 totals at that boundary were 11,668 encoded windows,
53,713.5 feature-audio seconds, 23,723.383719 source-read seconds and 28,866,560
reserved feature bytes. The producing package matches `fb3f194` exactly.

Before the delivery audit, the declared six-file consumer update was published:
compact immutable references preserve the unchanged 1 MiB JSON limit; bank/query
descriptors and frozen functions are checked; complete group-winner progress uses
hashed records within the fixed metadata allowance; complete-build repeats perform
the one charged validation pass. The strict geometry summary and silence-error
boundary were corrected without rerunning the closed real batch. No feature
identity, encoder, sample grid, native row mapper, distance or group-selection loop
changed, as recorded by [integration](../manifests/indexing/consumer-integration.json)
and [publication](../manifests/indexing/consumer-publication.json) proofs. The
support verifier's exact producing bytes are retained locally and in Git's
`b099e55` snapshot; later formatting does not replace its receipt.

The unchanged completed-bank command validated all 72 original sources / 123
long-bank shards with zero new windows: 152.795 worker seconds / 191.750s CLI
wall time. The fresh C01 legacy audit then validated all 72 recordings and 123
original shards with zero new features. Its receipt is
`668e623e66e2dc71d712a1c2411ccf37e67c54e1eadf1690c8c67daf998f3f60`.
The delivered snapshot is
`d6c54710786acdb584e92d2cba25491eb643c996fa622e3194d1b9381f659f87`;
its `partial-optional-banks` state preserves the rejected-duration pilot and
region-only components rather than concealing them behind full original coverage.

| Discovery bank | Intended / actual rows | Shards | Original coverage | Status |
| --- | ---: | ---: | --- | --- |
| Original 2.4s/.25s | 44,025 / 44,025 | 123 existing | All 72 recordings; 11,152.101338 unique seconds | Default; read-only, zero copied/re-embedded rows |
| Original 1.2s/.5s | 22,237 / 402 | 4 | Two pilot sources; 202.874308 unique seconds, remaining gaps explicit | Partial experimental; no full expansion |
| Original 4.8s/1s | 10,914 / 10,914 | 123 new | All 72 recordings; 11,152.101338 unique seconds | Complete experimental |
| Real harmonic 2.4s/.5s | 13 / 13 region rows | 1 | One 8s region of one recording | Partial catalogue coverage; experimental |
| Real percussive 2.4s/.5s | 13 / 13 region rows | 1 | Same 8s region | Partial catalogue coverage; experimental |

Each generated harmonic/percussive control also has thirteen rows and eight
supported seconds, outside discovery. Across banks the catalogue remains 72
recordings / 72 groups; the same original seconds are counted once. Full region
grids do not imply full-track component coverage. No C01 feature unit failed.

The C01 legacy execution
`a249b6159ddf3317b2c00b411d565ec66a80077e5e8d14992b41339774de090c`
scored all 44,025 rows and matched B03's complete 72-group timbre winners exactly,
including all fields, distances, deterministic order, native intervals, query
identity and exclusions. The complete winner-list digest is
`5ba261379bb3aa9c0a254af1bd25a4fda52bf2026efb5b0e9dae68ee24c65b53`.
Administrative execution IDs differ. No B03 receipt was borrowed for authorization.

The separate long-bank execution
`94c68ec52c013cbce510cfe1c3a69483aa87fc7256128d1c4cc31b56ac776fbe`
scored all 10,914 rows and retained all 72 eligible group winners before its ten
displayed candidates. Its distances are not fused with the legacy list. The full
22s mixed query is longer than either indexed passage duration; no intended layer
or perceptual relevance follows from these engineering demonstrations.

Final cumulative processing stayed within every precommitted ceiling:

| Resource | Charged / ceiling |
| --- | ---: |
| Aggregate worker seconds | 2,914.190 / 7,200 |
| Workers | 243 / 512 |
| Source-read seconds | 96,318.450249 / 180,000 |
| New encoded windows | 11,668 / 26,000 |
| Feature-audio seconds | 53,713.5 / 65,000 |
| Reserved feature bytes | 28,866,560 / 134,217,728 |
| Query/rank jobs | 12 / 16 |
| Playback clips | 28 / 64 |
| Clip bytes | 32,982,728 / 134,217,728 |
| Counted metadata bytes | 29,166,502 / 33,554,432 |
| Preparation bytes | 26,689,920 / 33,554,432 |
| Reserved managed bytes | 122,093,640 / 536,870,912 |

At final evidence export, the new managed namespaces occupy 86,120,670 bytes,
including 167 feature arrays / 17,943,424 bytes and retained test staging. Processing used one real
region, one new controlled separator input / eight seconds and fifty-two component
windows. HTTP/download acquisition was zero. Pending worker/read reservations
are zero. Setup, offline fixture tests, preservation inventory and browser/HTTP
verification are reported separately from inference; no old stage allowance was
spent. Automatic approval review rejected deletion of the three C01 staging
folders with `blocked by policy`; these ignored local copies were retained within
the storage allowance. They are not worktrees.

## Validation, playback and C02 handoff

The final full offline run passed **246 tests in 147.319s**, including all 28 C01
tests; Ruff check/format passed across source/tests and C01 verification scripts.
Pinned editable setup with
`pip install --no-index --no-deps --no-build-isolation -e .`, `pip check`, Ruff,
PowerShell listener syntax and an isolated starter smoke passed. The isolated
smoke is plumbing evidence and does not make a claim about delivery query
availability. No hosted CI is configured; no hosted check is claimed.

The delivered bundle has thirty players / twenty-eight unique WAVs. Independent
native QA passed all thirty mappings, PCM16 samples/gain, native bounds, frame
counts, rates and channels. HTTP QA passed WAV hashes, MIME/length, valid prefix
and suffix ranges (206), invalid/multipart ranges (416), and outside-bundle/path
rejection (404). Chrome loaded all thirty controls and passed trusted play,
pause and seek checks with advancing playback times and no media errors. All
players were paused, the temporary viewport override was cleared, the owned tab
was closed and the owned 8770 listener was stopped after QA.

Local evidence is `data/runs/indexing/native-qa.json`,
`reports/local/c01/http-qa.json`, `reports/local/c01/browser-qa.json`,
`reports/local/c01/browser-qa.jpg` and
`reports/local/c01/preservation-after.json`. The bundle is
`reports/local/c01/index-90eea3081f32080cf22e09d7ccfd42c46e700fbbba05f748dde6b931b5abe8ac/index.html`,
with manifest hash
`035b9e94ee158e7a4a70d948670a1420358faaf780bbfd69b32e45e063d2968f`.

Exact commands, resume/verify rules and the listener startup are in
[`docs/INDEXING.md`](../docs/INDEXING.md). The new listener uses 8770; existing
8766–8769 bundles remain separate. No deployment or human relevance review is
part of C01.

The delivery checkout contained the private catalogue audio, pinned checkpoint,
A06 arrays and exact saved B03 dependencies. A fresh clone does not receive those
private dependencies from the public metadata; absent prerequisites fail
explicitly instead of producing an empty successful search.

The exercised PowerShell forms below name the preserved command summaries and
immutable bank records. These are historical verification commands, not a request
to reopen the closed C01 allowance. The repeated completed `build` is the required
reuse check; the same command also resumes an interrupted, incomplete bank.

```powershell
$c01Python = '.venv/Scripts/python.exe'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/preflight-command.json indexing preflight
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/short-pilot-build.json indexing build --bank short --scope pilot
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/short-pilot-verify.json indexing verify --bank short --scope pilot
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/long-pilot-build.json indexing build --bank long --scope pilot
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/long-pilot-verify.json indexing verify --bank long --scope pilot
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/catalogue-long-command.json indexing build --bank long --scope full
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/reuse-command.json indexing build --bank long --scope full
$c01LegacyBank = 'data/indexes/c01/legacy/69166ae8d5f9857c546119a257579ce4f9b39bc2638e03be0ff2383e06333229.json'
$c01LongBank = 'data/indexes/c01/banks/e25294d24c9243958c7af2456353ba3d8641a26d5a40c50bf8b2cb1608b67cc0.json'
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/original-query-command.json indexing search $c01LegacyBank
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/long-query-command.json indexing search $c01LongBank
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/report-command.json indexing report
& $c01Python -m similar_sound_search --tier starter --report reports/local/c01/native-command.json indexing verify-native
& $c01Python scripts/verify-index-preservation.py verify
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/listen-index.ps1
```

C02 should open an explicit snapshot/bank-record hash, then use
`indexing.reader.read_bank` and `rows` for float32 arrays, stable row identities,
native signal/original bounds and source/component ancestry. Do not identify a
population by bank policy ID alone. Complete eligible group winners and their
per-example distances are retained before top-ten truncation. Distances are
unordered mean-example cosine, lower-better, with pitch zero and no presence
threshold. Each bank is searched independently. The receipt binds this C01
consumer version: C02 must declare its own owner/budget and fresh audited legacy
consumer, preserve these immutable row references and avoid spending the closed
C01 allowance. C02 must decide calibration,
opportunity bias across durations/hops, multiple-event combination, shortlist
coverage and overlap aggregation; it must preserve source/duplicate/cue exclusions
and avoid treating correlated banks/components as independent votes. C03 owns
query-dependent extraction/refinement. C01 does not start either stage.
