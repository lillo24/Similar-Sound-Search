# C04 processing — partial delivery at the metadata ceiling

C04 implements explicit revisions, native row reuse, transactional jobs and the
Python/CLI handoff. All declared fixture scenarios and real worker recovery passed.
**The real catalogue job is incomplete: 145/148 units committed.** It validated
both original banks across 72 recordings, loaded the exact saved query and committed
all 72 per-source scores, with zero new catalogue embeddings or copied arrays.
Aggregation, C03-chain import and complete publication did not finish. A finalized
real warm result and completed-C04 playback route are **not claimed**.

The metadata allowance could not admit another required write. Processing stopped;
no ceiling, counter, pool name or root was reset or enlarged. The immutable fixture
results and existing C03 playable report remain usable. [Machine evidence](C04_PROCESSING_EVIDENCE.json)
records actual inputs, scope, reservations, intermediates and checks.

## Implementation

[Processing contracts](../docs/PROCESSING.md), the [source map](../src/similar_sound_search/processing/README.md)
and [D01 handoff](../manifests/processing/d01-interface.json) own the boundary.
Python/CLI operations include explicit source import, plan, run, status, resume,
cancel, result, inventory and owned saved-query derivation. Plans are immutable
metadata estimates; execution verifies actual source bytes/PCM and native arrays.
Successive revisions and jobs share one fixed C04 pool.

Feature keys include exact file/PCM/decoder/native support and frozen representation.
Labels, ancestry and packing remain separately bound. Compact bundle memberships
resolve individual rows across packing; no historical row ID, producer, array or
closed ledger is rewritten. Conflicting bytes fail. Per-source scores bind the
complete ordered key/byte transcript by digest/count. Eligibility and complete-bank
group ranks use existing C02 fusion, mean scoring, exclusions and ties. Original
audio, legacy mean and pitch off remain defaults.

OS ownership spans claims, reservations and publication. Arrays precede immutable
membership, unit commits, progress and complete-result pointers. Valid orphans
reopen before adoption. Attempts and failed outputs remain retained. Settlement
journals replay once; unobservable reservations remain charged. Source removal
creates tombstones, with no automatic garbage collection.

The [correctness repair](../manifests/processing/consumer-repair.json) preserves the
initial consumer and unchanged encoding/scoring proofs. Windows venv-launcher
termination could leave its actual Python child holding a lock; C04 now launches
the actual worker PID with the same venv paths/prefix. Native parent groups are
excluded, event witnesses match actual native lineage, and domain errors keep
their unit context. No dependency or numerical recipe changed.

The [metadata compatibility declaration](../manifests/processing/metadata-compatibility.json)
preserves earlier declarations and allows only the exact scoped transition.
Runtime source/AST checks precede same-plan resume. Future records intern repeated
row references, share proof/score references and avoid redundant claim-progress
rewrites. An exact validated query matrix may be reused within one worker; it
does not survive the worker or conceal a failed load. Unknown drift blocks.
Historical full-package guards remain intact.

## Declared engineering sequence

Six generated 6s/24kHz WAVs stay outside discovery. Candidate populations contain
two or three sources. The bank starts at 2.4s windows / 1.2s hop; the denser grid
uses 0.6s hop. These are correctness/cost checks, not a quality sweep.

| Scenario | New feature rows | Processing seconds |
| --- | ---: | ---: |
| Cold | 9 | 25.703 |
| Unchanged warm | 0 | 9.562 |
| Add source | 4 | 22.391 |
| Replace source | 4 initially; 0 after coordinator repair | 27.860 + 15.219 |
| Remove source | 0 | 16.454 |
| Changed query | 1 | 16.547 |
| Association/objective | 0 | 9.439 |
| Packing | 0 | 9.250 |
| Denser grid | 6 | 39.937 |
| Label/report metadata | 0 | 9.126 |

Cold pilot/resume validation are both charged. Warm validation read 18 full-source
seconds and used two workers; it was not free. Independent clean rebuilds matched
feature bytes, native membership, exclusions, complete groups, order and shortlist/
display membership. Scalar cosine maximum error was 4.44e-16, within `rtol=0,
atol=2e-15`. The first replacement clean worker timed out at 120s; its output and
charges remain. Its separately declared repair/replay and clean comparison passed.

The real interruption terminated only its tracked actual worker after a six-row
feature unit committed. Resume preserved those exact hashes and encoded only the
other source's six missing rows. Its 13-row independent clean check passed.
Isolated tests cover double resume, contention/crash release, publication faults,
Windows replace failure, cancellation during validation, exhausted ceilings,
disk/memory refusals, missing/corrupt arrays, same-path source changes, lineage and
schema errors. There are 36 unique new native fixture rows; clean and retained
failed-clean outputs bring published/reserved rows to 139 in 54 arrays, 220,416 bytes.

## Real adoption: exact partial scope

Job: `6d5edff624a49b8529ff2add0593f3953f668c7baa140f65568e922979d7176b`.
Plan: `a5017addd669bc2d3461302e5ba742f42d31d4b5ddcbc45b674c33f1e8a3e4bc`.
Final source: `f242ed9`; consumer:
`d1399bb23a9a2edeb716025a04855cb91c3d11c5ebe3ab29b2c2ebd79ca34d4c`.

All **54,939 native rows** were verified/registered by reference: 44,025 legacy
and 10,914 long originals across 72 recordings / 72 groups. Sources checked actual
bytes/PCM; arrays checked exact native membership. C01 snapshot remains
`d6c54710786acdb584e92d2cba25491eb643c996fa622e3194d1b9381f659f87`.
Unique available-file duration remains 11,152.10133786848s; overlapping banks are
not added as new recordings/duration. A03 remains partial against 120.

The exact original Loulou revision
`c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3`
and materialization
`0ebb77012137c086e4cb1f72298e16446b33d96da2de28d7c9ccc5d663a03036`
were loaded/committed. The supplied MP3 is available. Full 218..240s remains native
frames 9,613,800..10,584,000 at 44.1kHz, with 217..241s context. No mutable pitch
head or invented clean excerpt was selected. Layer, rights, version, master
alignment and perceptual relevance remain unverified.

All 72 score units committed. Aggregation wrote 72 individual legacy and 16
event-multi group records before refusal. These are **uncommitted intermediates**,
not a complete snapshot/shortlist or substitute success. Current result is null;
last-complete still names the separate fixture recovery job. C03's twenty-group
execution and repaired media remain historical; the C04 import unit did not run.

## Accounting and blocker

| Counter | Charged / ceiling |
| --- | ---: |
| Worker seconds | 1,495.306 / 3,600 |
| Measured settled seconds | 1,375.306 |
| Unsettled worker 107 reservation | 120s retained |
| Workers | 107 / 256 |
| Full-source read seconds | 42,827.208 / 90,000 |
| Feature windows / feature-audio seconds | 139 / 4,096; 319.2 / 20,000 |
| Feature bytes | 3,752,448 / 33,554,432 |
| Processing/query jobs | 22 / 64 |
| Clips / clip bytes | 0 / 64; 0 / 134,217,728 |
| Counted metadata | 134,197,338 / 134,217,728 |
| Preparation bytes | 3,480,576 / 67,108,864 |
| Managed reserved bytes | 141,450,752 / 536,870,912 |

Only 20,390 metadata bytes remain, insufficient for mandatory settlement reservation.
Early verbose proof/row transcripts and repeated progress/scoring writes had consumed
the pool; later compaction did not refund them. The declared 32 MiB recovery reserve
was prospective, not a protected admission floor. This needs repair before larger use.

The refusal also prevented error/settlement journaling: persisted state is
`in_progress`, `error=null`, **`result=null`**, cancellation requested. Do not read
that as a live worker or success. Pool plus observed `ResourceError` are authoritative.
The 120s pending reservation stays charged, without a settlement journal. All owned
locks were independently acquired/released after stopping; no live C04 worker remains.
No further delivery processing was dispatched after refusal.

Maximum working memory recorded by settled workers was 325,730,304 bytes, below
1GiB; no memory measurement is claimed for the unjournaled final worker. Preflight
separately measured 45,021,413,376 bytes available Windows commit and 6,736,523,264
physical availability. Initial managed storage was 1,545,004,186 bytes; free space
230,607,233,024 bytes. Recorded C04 namespaces total about 66.6 MB. Cold pilot
timing includes startup/decode/encode/publication; separate startup and physical
I/O components were not isolated before the cap.

Setup/isolated tests, preservation and static publication are separate. Public
code declarations and non-inference QA are not individual per-worker metadata
charges; managed namespace inventory includes their files. There were no
acquisitions/downloads, GPU work, dependency/driver changes, deployments or GC.
Other unused counters do not authorize bypassing the metadata ceiling.

## Checks, preservation and playback

Final Windows/Python 3.12.14 regression: **351 tests passed in 271.889s**, including
36 C04 tests. Ruff lint/format, offline editable setup and `pip check` passed.
Isolated C04 starter smoke passed after copying required reference metadata; its
first missing-setup failure remains. Its isolated missing-audio diagnostic does
not describe the supplied MP3. Live scalar/native known-answer passed before
expansion; the unchanged oracle also passes final tests.

Preservation verified 13,496 historical files: 13,495 byte-identical, with only the
exact C04 config navigation addition allowed. An active-lock read was retried after
ownership ended. A locale-induced guide encoding change was restored from the UTF-8
baseline. No old config/ledger/audit/array/media, AGENTS instructions or root MP3
changed. C01's three denied staging folders remain; no deletion was retried.

No new bundle/clip was created. C03 bundle
`b7c1bae8c55f488883a599d4486b85d382b6d66eecabc6bbf028871e4ae48aee`
remains at `reports/local/c03/refinement-6f80c1786000d30144d0a3bf3da4dc777059f6cd391c13393e2dd3f712a6c405/index.html`.
Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/listen-refinement.ps1`
and visit `http://127.0.0.1:8772/`. Native/HTTP/Chrome proofs are historical C03
evidence, not fresh C04 browser checks. `listen-processing.ps1` requires the
unavailable completed real warm result; it is not a delivered live C04 route.

## D01 handoff and remaining work

The versioned API/schema handoff describes immutable source/query/bank references,
progress/errors, run/resume/cancel, current versus last-complete, resource ownership
and exact original/refined/context maps. It is implemented/fixture tested; real
finalization is blocked. D01 must not present orphan groups or the fixture result
as the unfinished catalogue request's success.

A new explicitly authorized stage must repair metadata admission/publication,
protect bookkeeping headroom, declare its owner/allowance, then finish aggregation,
audit the C03 chain, publish the complete result and exercise warm playback. Current
APIs bind C04's fixed pool; renaming/resetting/moving the same job cannot replenish
it. Validated rows, scores, declarations and private outputs remain in this checkout
for a scoped new consumer. Another machine needs exact private inputs/checkpoint/
artifacts. No D01 UI or listening review started; D04 remains the first review.

Delivery PR: [#26](https://github.com/lillo24/Similar-Sound-Search/pull/26).
Fresh delivery inspection found unprotected main, no rulesets, statuses, check
runs, workflow runs or reviews. No hosted CI pass is claimed; local checks above
are the executed validation.
