# C03 original-mixture candidate refinement

C03 implements bounded native timing refinement of the explicit C02 `event-multi`
twenty-group shortlist. It preserves song order and every original passage as
inspectable evidence. Original audio, legacy retrieval and pitch off remain defaults.
Finer placement is experimental: a lower distance does not establish sound presence,
true onset/end boundaries, human similarity or Loulou relevance. C04 is not started.

## Prospective ownership and fixed policy

Pulled clean `main` from C02 merge `2ee1b22` to C03 prompt `9048cdc`, then created
isolated branch `codex/c03-refinement` in the primary checkout. No extra worktree
was created. `b1fd31c` committed configuration/protocol before C03 inference.
`710423d` implemented the owner; `7f8b43d` pinned producer receipts, exact semantic
import and measured batching; `46396af` finalized original playback verification
and C04 accounting metadata before the expensive delivery audit.

[Contracts](../docs/REFINEMENT.md), [configuration](../config/refinement.json) and
[protocol](../manifests/refinement/protocol.json) own the reproducible policy.
The exact input execution is
`a1390a76b77c76aa53c3c97d6adfd5dc5ed38b5f0e9ad9ad2bf890f7a0554d67`,
arm `event-multi`, C01 snapshot
`d6c54710786acdb584e92d2cba25491eb643c996fa622e3194d1b9381f659f87`.
No arm substitution/union or new group is allowed. The 72-recording/72-group
catalogue, 44,025 legacy rows and 10,914 long rows are unchanged; unique available
source duration remains 11,152.101338s. Short and HPSS banks remain partial;
A03 remains partial against 120 requested recordings.

The first two saved representative anchors per group are selected in their saved
order without truth/audio inspection. Each keeps its native width and selecting
variant objective; mean objectives stay means. Starts are -500..500 ms in 125 ms
steps, including the exact original interval, rounded half away from zero, clamped
and deduplicated at source edges. There are at most nine opportunities per anchor;
edge/short inputs have fewer. No duration sweep, padding beyond real support,
stretching or claim that an envelope has an embedding. Exact ties favor the
original, then smaller displacement and earlier start. Two durations remain
separate objectives. All per-example original-mixture distances are retained.

Every imported source/group/row/shard/native interval and opportunity count is
checked against exact historical membership, array metadata/bytes and cosine
distances. Current C03 authorization is a new legacy audit receipt; historical
receipts/configuration are not rewritten. New compact feature bundles use actual
native original samples and separate producing-code receipts. Their semantic keys
exclude labels and include source bytes/PCM, bounds, channels/rate and frozen
representation. Historical row references remain historical; new rows use C03 IDs.

Extraction is prospectively omitted. B02 did not pass promotion gates; the full
22s Loulou mixture has no verified clean cue and exceeds B02's processing limits.
There are zero separator inputs, conditioning seconds and real processed regions.
Candidate-source and conditioning-query roles/exclusions remain explicit, and
processed distances cannot stand in for original-mixture verification.

## Fixed development comparison

One twelve-case/twenty-four-policy batch imports C02's saved compact development
supports through a separate explicit adapter. No C02 worker or `retrieval compare`
is reopened. The 37 recordings/33 groups are familiar procedural development,
including alternate performances, disjoint events, boundary/start/tail examples,
short queries, long-window interference, absent/excluded targets and silence.
Independent exact waveform reconstruction and FFT insertion-lag checks ran before
C03 predictions. Unavailable/corrupt support and wrong native membership are
covered by isolated failure oracles. No A06 holdout or human ratings are reused.

Both policies start with exactly the saved twenty-group shortlist and preserve
group ranks. Reported outcomes separate all eligible true events, conditional
shortlisted events, reachability by selected anchors/local geometry, selected
passage losses and the retained-original guard. A group hit and at-least-one-event
hit are distinct from recall of all known events. IoU, full containment, overlap
and native start/end error are separate. The guard always retains original
passages; it does not use truth to choose a production interval.

Two two-group pilot workers completed before expansion, with about 277 MB peak
working memory. Reopening the full source and saved local bundle reproduced the
pilot anchor with zero new feature windows; measured reuse was 0.016s inside the
worker, separate from process/model startup and publication. Subsequent development
units are at most four groups, delivery units at most two. Earlier conservative
64 KiB bundle reservations remain charged; later compact bundles reserve vector
bytes plus twice their identity size and 8 KiB overhead. No ceiling was enlarged.

## Measured development outcome

Across the seven primary cases, source-consistency hit@1/5/10/20 remains
**6/7, 6/7, 6/7, 7/7** in both policies because song order is unchanged.
At least one known event survives in all seven cases. Counting every independently
known performance/event gives the following end-to-end denominators:

| Evidence | Known events retained / 21 |
| --- | --- |
| Complete unrefined C02 representatives | 19 / 21 |
| Same two preselected anchors before timing | 18 / 21 |
| Selected finer original-mixture placements | 18 / 21 |
| C03 output including all retained originals | 19 / 21 |

The boundary case accounts for the difference: a third C02 representative supports
one extra event but is outside the two-anchor processing cap. It remains explicitly
unprocessed and retained, rather than being presented as a new timing loss or as
verified refinement. Matched-anchor timing has zero paired half-event-coverage
gains/losses. Across the 21 comparable native event pairs, IoU and summed boundary
error improve in four, worsen in three and stay equal in fourteen. Long enclosing
windows remain different from precise onset/end localization. There is no quality
promotion; refinement stays opt-in and legacy defaults stay unchanged.

The harmonic case retains its existing scoring/selection miss even though its
local geometry includes a supported interval. The full machine-readable evidence
retains shortlist, upstream support/cap, local reachability and scoring-loss
decomposition, individual IoU/containment/frame/second errors and conditional
shortlist/local-domain denominators. Absent and parent-excluded controls have no
positive denominator; silence is two explicit unsupported policy outcomes.
No declared case was replaced or removed.

## Multi-event engineering demonstration

The saved `conflict` case uses two distinct pluck/FM examples and retains six of
six known performance/events before and after refinement. Its hybrid group's
4.8s anchor remains bound to its original selecting FM variant, with both example
distances retained. The actual interval moves from frames 24,000..139,200 to
27,000..142,200 at 24 kHz (1.000..5.800s to 1.125..5.925s). Its objective distance
falls from 0.1730154056 to 0.1621317622, while the other example's distance is
0.2973824454. This is a sliding mixture window over disjoint known events, not
precise separation/boundaries or a sequence match. The immutable group record is
`1fa900e1f405e0e03a85a62827fe422b8d9d74fc70472b0fed3029233013f315`;
its original generated source remains `data/audio/retrieval/hybrid.wav`.

## Validation and preservation trace

The full regression suite passed 312 tests in 146.711s, including the original 27 focused C03
tests. The renderer repair adds three tests; the final suite passed **315 tests in
211.274s**, with all 30 C03 tests passing. The confirmation after final source code also passed all 312 tests in 160.972s. Ruff lint/format,
offline editable setup, `pip check`, isolated starter smoke and the C03 independent
native/scalar known-answer command passed. No hosted CI is configured or claimed.

The first full run exposed a C02 test that bound the historical repair fixture to
the live package's entire source map, which necessarily changes in later stages.
Only that test now supplies the pinned C02 consumer for its historical success
case; the production stale-consumer guard and rejection case remain unchanged.
The C02 module's 39 tests then passed in 4.593s. No historical runtime code, model,
preprocessing, distance function, grid or configuration was weakened.

A smoke check initially reused C02's isolated smoke folder. Its overwritten summary
was recovered exactly from archived stdout and verified against the original
SHA-256; the newly created C03 lock there was removed. All subsequent smoke output
is C03-owned. The historical inventory recheck verified 12,119 files with 12,118
byte-identical and only the exact C03 config README navigation addition allowed.
The initial inventory helper had inherited exclusions for two C02 files; those
were added with unchanged Git-verified configuration and the original one-byte
lock. No old ledger/array/media was altered. C01's three denied staging folders
remain inventoried and untouched; no deletion retry occurred.

## Renderer repair and automated approval trace

The first bundle passed all 32 exact native sample checks and all 25 HTTP media
checks, but Chrome found a real seek-handler failure. Formatting had inserted a
raw newline inside a single-quoted JavaScript error message. The renderer fix
`8a68686` adds a regression for multiline script literals, byte-identical report
copying, preserved native proofs and rejection of numerical-consumer changes.
Rendered-script syntax passed Node and the full 315-test suite passed afterward.

The separate [repair declaration](../manifests/refinement/report-repair.json),
committed as `2105a37`, pins only CLI routing, command routing and renderer changes.
All numerical modules are byte-identical; original report-build and exact native
verifier ASTs are unchanged. A second C03-owned legacy audit binds this report
consumer. The numerical execution, its original receipt/reuse/features, first
bundle/native proof and failed browser JSON/screenshot are preserved. Verified
media copies are charged to the same ledger and a second native proof is published;
no inference is repeated and no stale-consumer guard is weakened.

Automatic approval review rejected the combined hidden-background-listener and
browser-QA command with **"blocked by policy"**, without a more specific reason;
that command executed nothing. A directly tracked foreground repository listener
and separate HTTP/Chrome QA commands were accepted. The foreground listener is
stopped with Ctrl+C; no hidden-helper launch retry or process-kill cleanup is used.
C01's separately denied staging deletion remains untouched.

## Exercised Windows commands

Run from the repository root. Exact command summaries/logs are under
`reports/local/c03`; private media/checkpoint/query inputs are required. Public
metadata is not proof of availability in a fresh clone.

```powershell
$c03Python = '.\.venv\Scripts\python.exe'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& $c03Python -m pip install --no-index --no-deps --no-build-isolation -e .
& $c03Python -m pip check
& $c03Python -m unittest discover -s tests
& .\.venv\Scripts\ruff.exe check src tests scripts/verify-refinement-preservation.py
& .\.venv\Scripts\ruff.exe format --check src tests scripts/verify-refinement-preservation.py
& $c03Python -m similar_sound_search --root reports/local/c03/starter-smoke --tier starter smoke
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/preflight-command.json refinement preflight
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/known-answer-command.json refinement known-answer
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/geometry-command.json refinement geometry
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/pilot1-command.json refinement compare --pilot
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/pilot2-command.json refinement compare --pilot
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/comparison-command.json refinement compare
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/compatibility-command.json refinement compatibility
$c03Receipt = (Get-Content reports/local/c03/compatibility-command.json -Raw | ConvertFrom-Json).receipt
$c03Input = 'data/runs/retrieval/executions/a1390a76b77c76aa53c3c97d6adfd5dc5ed38b5f0e9ad9ad2bf890f7a0554d67.json'
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/refinement-pilot-command.json refinement refine --execution $c03Input --arm event-multi --receipt $c03Receipt --pilot
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/refinement-command.json refinement refine --execution $c03Input --arm event-multi --receipt $c03Receipt
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/reuse-command.json refinement verify --execution $c03Input --arm event-multi --receipt $c03Receipt
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/report-command.json refinement report
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/native-command.json refinement verify-native
# After the renderer-only fix; original command summaries were archived first.
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/compatibility-repair-command.json refinement compatibility
$c03ReportReceipt = (Get-Content reports/local/c03/compatibility-repair-command.json -Raw | ConvertFrom-Json).receipt
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/report-command.json refinement repair-report --receipt $c03ReportReceipt
& $c03Python -m similar_sound_search --tier starter --report reports/local/c03/native-command.json refinement verify-repaired-native
& $c03Python scripts/verify-refinement-preservation.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/listen-refinement.ps1
```

The isolated smoke's missing-reference diagnostic says nothing about this delivery.
The supplied Loulou MP3 is technically available. Its exact immutable revision is
`c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3`,
materialization `0ebb77012137c086e4cb1f72298e16446b33d96da2de28d7c9ccc5d663a03036`.
The full selected mixture is 218..240s, native frames 9,613,800..10,584,000 at
44.1 kHz stereo; context is 217..241s, frames 9,569,700..10,628,100. Recording/version
alignment, master offset, rights, intended layer and complete event boundaries
remain unverified. It adds no discovery recording.

## C04 handoff

Read the pinned C03 `execution` reference from `data/runs/refinement/execution.json`.
The `c03-c04-refinement-1` export references all twenty immutable
`c03-c04-group-1` results separately from ten displayed songs. Every group carries
its input rank/state, complete original C02 input, selected anchors/objectives,
original control/retained alternates, all local rows and actual scored/context
native maps. New feature bundles reference separate producing-code receipts.
The execution binds the exact query, input arm, snapshot/banks, fresh current
consumer proof, policy and protocol.

The dependency graph records ledger/work/timing/progress/reuse ownership and atomic
boundaries: feature producer/bundle, immutable group, progress pointer, final
execution. An interrupted command resumes the same pending inputs; conflicts fail
without resetting charges. The one required reuse validates original sources,
historical/native membership and all local feature bytes/scores without embedding.
Changes to source/query/native bounds/objective/representation require declared
new work; labels do not change semantic features. C04 must provide its own allowance
and consumer. Automatic invalidation, general scheduling, source refresh and cache
cleanup remain unimplemented.


## Final delivery, costs and playback

The completed numerical execution is
`339fa84d523c457ab10c099be4feeb13b220d29fec995c31eed12fae4a23d98d`.
All twenty input groups are complete with no processing failures and unchanged
song ranks. Fifteen groups have at least one changed placement: nineteen of forty
anchors moved and twenty-one retained their exact original interval. The required
reuse validated all twenty groups with zero new features. Original controls and
all unprocessed third representatives remain inspectable.

[Sanitized machine-readable evidence](C03_REFINEMENT_EVIDENCE.json) contains every
case/paired metric, group/native row, immutable dependency, producer/consumer proof,
QA outcome and accounting record. Selected/control indices address each anchor's
row list, and the retained-original alias addresses its input; this avoids repeated
large objects while preserving the shared 1 MiB reader limit.

| Counter | Used / fixed ceiling |
| --- | --- |
| Aggregate worker seconds | 1,789.733 / 3,600 |
| Workers | 123 / 256 |
| Full-source read seconds, including repeat hash audits/decodes | 47,900.946 / 90,000 |
| New local feature windows | 704 / 4,096 (480 development, 224 real) |
| Feature-audio seconds | 2,361.6 / 20,000 |
| Reserved feature bytes | 3,499,520 / 33,554,432 |
| Query/refinement jobs | 28 / 64 |
| Clips, including retained byte-identical repair copies | 50 / 64 |
| Clip bytes | 49,226,100 / 134,217,728 |
| Counted metadata bytes | 29,200,890 / 100,663,296 |
| Query preparation / other processing audio bytes | 0 / 67,108,864; 0 / 134,217,728 |
| Managed reserved bytes, including 96 MiB metadata envelope | 153,388,916 / 536,870,912 |
| Development batches / case-policy evaluations | 1 / 1; 24 / 48 |
| Separator inputs / input seconds / real processed regions | 0 / 32; 0 / 240; 0 / 4 |

There are zero HTTP acquisition attempts/downloads, new discovery rows or copied
legacy feature arrays, and no pending worker/read reservations. Maximum measured
worker working memory is 440,315,904 bytes, below 1 GiB. Initial Windows available
commit was 44,257,341,440 bytes and physical availability 4,694,183,936 bytes;
the conservative allocation estimate was 1,028,906,808 bytes. These are distinct
measurements. Action timing/peaks and actual namespace/array sizes are in the JSON.
Setup, isolated tests, preservation and non-inference HTTP/browser QA are separate
from the processing ledger. Both audits, the first report and repair copies remain
charged; no fund was reset or enlarged.

The final playable report is
`reports/local/c03/refinement-6f80c1786000d30144d0a3bf3da4dc777059f6cd391c13393e2dd3f712a6c405/index.html`,
bundle `b7c1bae8c55f488883a599d4486b85d382b6d66eecabc6bbf028871e4ae48aee`.
It has 32 players / 25 unique WAVs: full query/context plus before, after and
original context for ten songs. All 32 passed fresh exact native PCM16/sample/gain/
frame/rate/channel checks. All 25 media hashes/MIME/length and HTTP prefix/suffix
range, invalid/multipart range and outside-path checks passed (7.25s).

Chrome 155.0.8059.85 with bundled Playwright 1.62.1 passed all 32 load/play/advancing
clock, pause and seek checks in one 12.287s run, using 128 trusted keyboard events,
with no media or page errors. Two request-intercepted harness attempts had media
load failures, while ordinary Chrome diagnostics loaded every player. The final
complete control check used normal network requests and a fresh isolated profile,
with the same controls/assertions/timeouts. All failed attempts, profiles and
network diagnostics remain. No further application/server/media change was needed
for that harness correction. The owned browser context and foreground loopback
listener are closed; other listeners and sessions were untouched. No deployment.

Start playback from the root with
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/listen-refinement.ps1`,
then open `http://127.0.0.1:8772/`. The startup script was exercised as a foreground
session. HTTP/browser QA helpers and rendered-JavaScript syntax checks are retained
under `reports/local/c03`; the code and final 315-test run precede the repair audit.

The final preservation check verified 12,119 historical files: 12,118 byte-identical
and only the documented exact config README navigation addition allowed. There
are no missing, unexpected or otherwise changed historical files. The public
configuration, old ledgers/arrays/proofs, root MP3 and denied C01 staging folders
are preserved. New ignored reports, sources/features, both report versions and QA
artifacts remain in this delivery checkout.

The C04 handoff additionally distinguishes the original numerical consumer from
`manifests/refinement/report-repair.json` and its later fresh report receipt.
`data/runs/refinement/report.json` locates final playback;
`report-repair-native-qa.json` owns its new native proof. Producer/execution versions
are preserved rather than relabelled. C04 has not started.

![Verified C03 playback](local/c03/browser-qa.png)
