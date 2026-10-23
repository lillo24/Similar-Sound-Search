# D01 — Local search interface

D01 acceptance is complete on the actual Windows delivery checkout. The application
imports audio, selects/auditions native intervals, saves/reloads B03 query revisions,
searches all 72 existing recordings asynchronously and plays the selected result's
actual scored passages with separate context. It is backed by real catalogue/model
work, alongside explicitly generated engineering fixtures. Human similarity remains
unmeasured; D02 evaluation, D03 packaging and D04 listening review were not started.

The fixed D01 pool now has insufficient source-read/ordinary metadata allowance for
another full search. Completed results remain available, including in a fresh browser.
No pool, cap, prior charge or historical reservation was reset. This limit does not
invalidate the completed acceptance results below.

## Run and reopen

From the repository root with the existing pinned Python 3.12 `.venv` and local
private inputs/model present:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-sound-search.ps1
```

Open **http://127.0.0.1:8774/**. Keep the terminal open; Ctrl+C stops admission and
waits for its own bounded worker. Startup, shutdown and server restart were exercised
on Windows 11/Python 3.12.14. Port conflicts fail explicitly. All owned delivery
listeners/browser sessions are stopped; their ignored artifacts remain in this checkout.

Choose **Open a completed search** in the Search panel: the Loulou warm job starts
`12941fbd`, and the generated two-example job starts `589ac27a`. Opening a completed
result restores its resolved revision/materialization/policy without launching a
worker or changing the pool. Submitting Search is a separate, charged operation and
can now fail admission. Refresh restores the current job; controls also explicitly
cancel, resume and reopen it. The default remains original mixture/legacy mean/pitch
off. Experimental event retrieval is separate; C03 refinement accepts only its exact
historical chain. Unsupported options fail explicitly.

[Application contracts/recovery](../docs/APPLICATION.md), the
[source map](../src/similar_sound_search/application/README.md), the
[D02 product boundary](../manifests/application/d02-interface.json) and
[typed machine evidence](D01_INTERFACE.json) own the reproducible details.
A public clone can run isolated code/tests; Git does not restore private catalogue
audio, model or ignored B/C artifacts. No acquisition, deployment or dependency/driver
upgrade is part of this delivery.

## Admission and ownership repair

The `application/` subsystem wraps existing A02/B03/C04/C02 primitives. Every inherited
Python file remains byte-identical to C04's source map, including the Windows actual
worker-PID fix. The new bank reader separates immutable C01 membership reuse from
the historical importer that still requires the exact original Loulou query. Source
bytes/PCM, native membership, array hashes and score supports receive D01 proofs.
No catalogue arrays are copied or re-embedded. Old producer identities and package
guards remain enforced; unknown Python drift blocks work. Exact scoped declarations
archive previous consumers/ASTs before later control/metadata repairs. Renderer
checksums are separate from semantic feature keys.

One precommitted pool owns all new work and retries. Ordinary metadata is limited
to 96 MiB; at least 32 MiB of the unchanged 128 MiB ceiling is protected. Admission
reserves the complete publication path. Every write charges serialized destination,
atomic temporary and overhead; pool replacements are bounded and counted. A 256 KiB
protected slot precedes each attempt and pays for terminal state, error/success
journal, settlement and recovery. It does not use the exhausted ordinary writer.
Settlement applies a delta once, preserving later control charges. Failed writes and
unobservable reservations retain their costs. Only unspent logical reservations
are released; no actual write is refunded.

Population groups are committed in chunks of eight with a bounded lossless storage
codec, preserving exact values/order and full native supports. The metadata-only
preflight proposed 217 records, counted 2,494,054 publication bytes and a largest
counted record of 512,626 bytes, with both 72-group baseline comparisons exact.
It ran no audio inference. The shared 1 MiB record-reader limit remains unchanged.

The original request estimates proved too small for repeated recovery and new-score
serialization. Those blocks are retained, including durable protected error and
settlement records. Each affected request received one prospective 8 MiB allocation
for an enumerated remaining path **from the same fixed D01 pool**:

| Request | Initial allocation | Final allocation | Remaining-path admission prefix |
| --- | ---: | ---: | --- |
| Real adoption | 20 MiB | 28 MiB | `37fcbf8ffe8045e9` |
| Two-example search | 21 MiB | 29 MiB | `2cf023d88759257d` |

No hard ceiling increased. The corrected fresh-request estimate budgets conservative
per-source score/progress payloads and full group/control geometry: 52,517,120 bytes
for one example, 55,422,464 for two and 84,665,408 for eight, before the request's
rounded admission margin. All fit the original ordinary ceiling when empty; they
cannot fit the current remaining allowance. Preflight's earlier smaller estimates
remain historical evidence rather than being rewritten as successful predictions.

Original recovery freshly hashed all source bytes and reopened every array. The
later new-query recovery freshly validated query materialization, reopened all
candidate arrays and independently checked committed source scores/supports against
them, retaining earlier full source/PCM proofs. It does not claim another full
catalogue original scan. Only remaining media/publication units then ran. Normal
warm validation retains full sequential original-source reads, including MP3.

Read-only status checks probe OS ownership and distinguish current process evidence
from durable state, stale/interrupted work, cancellation pending, blocked admission
and complete publication. Leftover lock files are not live workers. Duplicate request
IDs reuse the same job; conflicting payloads fail. Resume persists a protected pending
acknowledgement before returning HTTP 202. Closing a tab/server does not reset the
request, feature commits or budget. An all-write filesystem refusal raises explicit
`PersistenceError`; it cannot promise a durable write the filesystem refused.

## Exact real acceptance

| Path | Job | Result | Completion |
| --- | --- | --- | --- |
| Adopt and finalize C04 | `1c0ef69a1a5156319dec8a976cab164de576d13ba9cc00f5c24b4355b361a678` | `c71cd6e7f7a804d3669683e8d6b1dc46c5c52caec12beba6764032c8a8b54136` | 99/99 |
| Unchanged warm original | `12941fbd35737b6fb7df959d4fbbf9a1425fd5d5c1ba208cb01eb55e943ebef0` | `cec00d3807ab7daa477695c059ad138f2378e8419f3d50ca2a59d8b3f889a26b` | 99/99 |
| Generated two-example query | `589ac27a30d60007e1a7f8ad6fdd695499d23ca0f17b55e858b00d624be0fd6b` | `1c40c05c46a11d671bf38e57dca5acde9d68959ecf48528501580a71ec02ea19` | 98/98 |

Each result covers 72 recordings, 44,025 legacy and 10,914 long native rows, complete
groups for both arms, twenty-group shortlists and ten displayed songs. No result is
padded. Default players use the actual legacy representatives, not the C03 report.
Additional retained passages are distinct native references in details; the first
passage has scored/context players. Complete group references remain available to D02.

The original Loulou query is exactly revision
`c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3`,
materialization `0ebb77012137c086e4cb1f72298e16446b33d96da2de28d7c9ccc5d663a03036`.
It retains **9,613,800..10,584,000** native frames at 44.1 kHz (218..240s), with
217..241s context. The full 22-second mixture is ready to load and audition. File
availability does not verify recording identity, rights, intended layer or master
alignment; the query does not become a discovery recording.

D01 freshly adopted all 72 C04 source/score units by reference and recomputed
aggregation instead of promoting orphan groups. Full legacy and event-multi group
order, scores and native representatives match the pinned C02 baseline: maximum
score difference **0.0**. The C03 query/shortlist/anchor/local-row/producer chain and
separate repaired report consumer passed. Scalar/block audits retain `rtol=0,
atol=2e-15`; ranking rules were not relaxed. Adoption and warm search encoded zero
features. The warm search generated zero clips and charged 21,844.741 source-read
seconds, rather than treating validated reuse as free.

In the real browser, the file picker imported a generated six-second 24 kHz mono
reference. Keyboard selection moved one native frame; waveform drag and numeric
selection were exercised. The selected mixture was auditioned; two intervals were
added/reordered, named, saved and reloaded. Revision
`3b3c46459b21c31d4757395275d0ecf411688f835981573920aea35ace8110f3`
materialized as `20c4b2fa9e2fa5cc59410a9b3fd258187080c75e4109e63dc97a35f64d2b5201`,
with [4,800,55,200) and [74,400,132,000) native frames (2.1s and 2.4s).
It encoded exactly **two query examples**, generated query-dependent scores/rankings
for every recording and reused all unchanged candidate arrays. Its top-ten order
differs from the original query. C03 refinement for this new query was explicitly
rejected. This generated sound is an engineering reference, not a substitute relevance
assessment for Loulou.

That same job was cancelled before its first unit, the owned app stopped/restarted,
and the persisted request resumed. It kept the same job identity and two committed
feature encodes through recovery; refreshing reopened its exact result. The global
D01 last-complete points to this job. A failed/current operation never relabels an
older result as its output. Original/other completed searches remain independently
selectable with their own immutable bindings.

## Validation and retained failures

- **382 tests passed in 235.980s**, with numerical threads one; focused application
  checks passed 31 tests. Ruff lint/format and JavaScript syntax checks passed.
- Offline editable installation with no dependency downloads, `pip check`, exact core
  and optional CPU-model lock versions, isolated starter smoke and independent four
  scalar-pair/eleven-native-interval known answers passed. Known answers called the
  pure validator directly, avoiding a write to the closed C04 pool. The smoke's
  historical missing-reference manifest is isolated from the actual supplied MP3.
- Small isolated pools cover ordinary exhaustion with protected terminal settlement,
  repeated/idempotent settlement, failure while recording failure, Windows replacement
  errors, all-write refusal, low disk/memory, real OS contention/actual-PID termination,
  retained uncertain reservations, before/after-publication crashes and orphan reuse.
  Other tests cover missing/corrupt inputs/media, optimistic revision conflicts,
  duplicate submission, unsupported settings, dedup/all-parent exclusion and a small
  independently scored native catalogue with exact result-to-player binding.
- Real Chrome **155.0.8059.85** controls tested load, advancing time, pause and seek
  for **20 original-result players, 20 new-query players and all 32 preserved C03
  players**, plus reference previews. The final fresh browser opened both completed
  results with no ledger changes and restored the same job after refresh. Desktop
  1360×1000 and mobile 390×844 layouts passed without horizontal overflow. Passed
  phases recorded zero page/console errors or external application requests.
  A final cached-preview job additionally verified that active work locks file,
  query, selection and policy controls and ignores waveform drags, preserving the
  job binding. It encoded no features and generated no clips.
- Independent native QA checked all **40 default/new-result clips** against full
  decoded originals with exact PCM16 rounding, source offsets, gain, frame count,
  rate, channels and scored/context endpoints. All passed without new features/clips.
- HTTP checked those 40 players' complete hashes/MIME/length, prefix/suffix ranges,
  invalid/multipart/out-of-range rejection, strict Host/Origin/token boundaries,
  traversal/raw-path refusal and cross-result media rejection. Candidate media cannot
  use a reference-preview endpoint; even an existing foreign clip is rejected from
  a result. Thirty status polls and actual duplicate submission left the pool unchanged;
  conflicting retries failed. **Actual symlink creation was refused by Windows
  (`OSError`)**; outside-path refusal was verified and no bypass attempted.

Private screenshots, driver logs and native/HTTP checks are retained under
`reports/local/d01/`, including `app-final-desktop.png`, `app-final-mobile.png`,
`browser-warm-reopen.json`, `browser-resume-observe.json` and `http-qa.json`.
The public JSON exports sanitized counts, IDs, hashes and native answers, without
private audio, user paths or session tokens. The exporter dispatches no work.

Earlier failures remain visible: the initial A06 containment assumption, per-worker
deadline accounting, exact consumer-reference resume comparison and both ordinary
metadata blocks. Their fixes were declared before subsequent work. Browser drivers
also retained an incorrect native-player keyboard-seek attempt and polling/refresh
races; corrected drivers used real pointer seeking and awaited the actual transition.
The application resume acknowledgement race and Windows idle peer-disconnect
traceback were repaired and regression tested. A full earlier suite run encountered
producer drift while code was edited; later immutable-scope full runs passed. These
failed attempts were not reclassified as successful or removed.

## Costs and preservation

| D01 charged counter | Used | Fixed ceiling |
| --- | ---: | ---: |
| Worker seconds / workers | 2,452.230 / 106 | 3,600 / 256 |
| Source-read seconds | 85,949.160 | 90,000 |
| New query feature windows | 2 | 1,024 |
| Charged processing seconds / feature bytes | 9 / 134,144 | 6,000 / 33,554,432 |
| Processing/query jobs | 22 | 64 |
| Clips / clip bytes | 39 / 22,566,324 | 64 / 134,217,728 |
| Counted metadata bytes | 73,613,272 | 134,217,728 |
| Preparation / import bytes | 1,216,832 / 576,058 | 67,108,864 / 134,217,728 |
| Managed output debit, including QA reservation | 91,602,222 | 536,870,912 |

Metadata additionally reserves its full 128 MiB envelope within the managed ceiling.
Ordinary/protected spent bytes are 64,373,390 / 9,239,882; both active reservations
are zero. Unspent acceptance hold is 6,899,712 bytes; it is not a new pool. D01 has
zero uncertain worker seconds. The processing counter includes inherited B03 pitch
metadata accounting although pitch stays off; exactly 4.5s of selected query audio
produced the two new feature rows. Non-inference browser/HTTP/preservation QA has a
prepaid 64 MiB managed allowance and about 18.7 MB of retained files. It is separate
from numerical operations, which remain charged above.

Measured worker peak was 393,711,616 bytes; coordinator/server peak 124,706,816;
the largest recorded server-plus-worker bound was 497,651,712. A snapshot of owned
Chrome processes during new-query QA totalled 477,790,208 working bytes; summed
per-process peaks of 488,378,368 are not a simultaneous measurement. Starter limits,
one numerical worker, lazy model per worker, 120s actual-PID deadlines and 4 GiB
storage/free-space headroom were retained. No GPU, new paid service, telemetry,
automatic GC, download or driver change ran.

The read-only preservation audit verified **15,490 historical files**, with zero
changed/missing files and zero unexpected additions. Four new files belong to two
new immutable shared A02 prepared bundles. Historical configurations, arrays,
ledgers, root MP3 and C03 bundle are unchanged. C01's three staging folders denied
previously with “blocked by policy” were inventoried and retained; deletion was not
retried through another route.

C04 is still **partial 145/148**, job
`6d5edff624a49b8529ff2add0593f3953f668c7baa140f65568e922979d7176b`, plan
`a5017addd669bc2d3461302e5ba742f42d31d4b5ddcbc45b674c33f1e8a3e4bc`, result null.
Its metadata stays 134,197,338 bytes, workers 107 and charged seconds 1,495.306,
including the unsettled **120-second reservation**. Its orphan groups, attempts,
stale persisted state and fixture last-complete were not rewritten or presented as
the completed real result. D01 owns the separate successful publication.

Preserved C03 bundle `b7c1bae8c55f488883a599d4486b85d382b6d66eecabc6bbf028871e4ae48aee`
also remains playable through `scripts/listen-refinement.ps1` on 8772. That listener's
HTML matched its immutable hash during D01 QA. The application exposes it separately
at `/historical/`; its original numerical/native proof remains historical, while the
32-player browser check above is fresh D01 evidence.

## D02 handoff

Use the stable [interface declaration](../manifests/application/d02-interface.json)
and `application.api` for upload/registration, exact native B03 selection/save/load,
query-dependent submission, status, cancel/resume and complete-result reads.
`job.run` coordinates bounded workers; read routes never dispatch them. Result schema
`d01-result-1` binds query, policy, population, complete groups and cards. Scoped
`/result-media/<result-id>/<media-id>` resolves exact native scored/context playback.
The isolated deterministic fixtures expose both successful and failure states without
spending this delivery pool. Baseline and acceptance identities are public metadata;
matching private artifacts are required for real integration.

D02 must inspect remaining allowances and define any separately authorized work
prospectively; a fresh full-catalogue run does not fit this D01 remainder. Technical
correctness and inspected generated results do not establish human sound similarity.
D03 packaging and the first required D04 listening review remain later tasks.
