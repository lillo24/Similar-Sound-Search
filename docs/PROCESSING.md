# C04 dependency contract (version 1)

One processing owner manages explicit immutable input revisions, plans, jobs and
atomic results. Original audio, legacy mean retrieval and pitch off remain defaults.
The existing decoder, frozen EfficientAT representation, native grid, cosine scoring,
exclusions, C02 complete-population fusion and C03 geometry retain their owners.

This table is declared before implementation and inference. Execution/attempt IDs,
producer code and consumer proofs are separate from semantic sample identities.

| Output | Semantic dependencies | Invalidation and reuse |
| --- | --- | --- |
| Source validation | bytes + canonical PCM + rate/channels/frames + exact decoder | Changed bytes at the same path fail the old revision; explicit replacement creates a new one. Every run audits actual sources. |
| Preparation | source + channel/resample/crop/transform/cue/native map | Only validated B03 recipes for saved derivatives; unsupported transforms fail explicitly. |
| Native feature row | all sample dependencies, exact bounds, frozen checkpoint/preprocessing/dimension | Row lookup independent of bank, label, packing, job and ancestry. No cross-file or cross-decoder equivalence. |
| Bank membership/snapshot | exact ordered native rows, policy, population/group/provenance/exclusions | New population publishes new membership; removal is a tombstone, never deletion. Packing changes references only. |
| Query materialization/features | explicit recipe/revision/materialization and actual audio/cue/map | Query change invalidates query/score descendants, preserving candidate features. |
| Per-source scores | candidate row bytes, query feature bytes, cosine implementation | Population/group/label changes retain compatible distances; eligibility is applied again. |
| Group ranks/shortlist | every eligible group in every complete bank, events/objective/fusion/ties | Recompute complete population, never only prior shortlist. |
| Optional refinement | exact C02 population/query/selection and C03 policy/local row evidence | Import the exact completed historical chain; changed dependencies require new explicit refinement work. |
| Playback/report | exact result, native scored/context bounds, labels/layout/media | Rebuild metadata/proofs without inference; verified historical media may be referenced intact. |

Each compact row reference retains original array identity/hash, native membership,
row number and producer evidence. Conflicting bytes for one semantic key fail.
Historical package-wide code guards remain enforced. C04 declares an exact consumer
and a classified source map; unclassified drift blocks. A new declaration is required
after an implementation change. Numerical compatibility is established separately
from coordinator/renderer identity, never by replacing old hashes.

Fixed roots: `data/runs/processing`, `data/features/processing`,
`data/indexes/processing`, `data/audio/processing`, `manifests/processing`,
`reports/local/c04`. `config/processing.json` fixes one stage pool shared by every
job/retry/revision/clean comparison. No rename/reset/cache clear replenishes it.
The 128 MiB metadata envelope is reserved inside the 512 MiB new-output limit;
metadata rewrites, pool/attempt records, temporaries and failed writes are charged.
CPU/offline/concurrency one, starter storage/headroom/memory limits and 120-second
worker deadlines remain. Setup/regression and non-inference preservation/HTTP/browser
QA are measured separately. No acquisition, dependency change, separation or GC.

## Commands and D01 API

Use `.venv/Scripts/python.exe -m similar_sound_search --tier starter processing`:

| Operation | Explicit input | Result |
| --- | --- | --- |
| `import` | `c04-local-import-1` JSON, 1..8 path/id/group/title/rights values | Charged source revisions and PCM/native metadata outside frozen discovery |
| `plan` | `c04-input-1` JSON; optional `--previous PLAN` | Immutable plan, dependencies, tombstones, metadata reuse estimates and blockers |
| `run` | immutable plan path, `--job NAME`; optional `--pilot` | Job, at most four graph units per bounded worker |
| `status` | immutable job path | Read-only current state/error/result, last complete, remaining units/allowance |
| `resume` | same job path; optional `--pilot` | Revalidate committed feature/query outputs; remaining work under same pool |
| `cancel` | job path | Cooperative stop; active bounded unit finishes; no new admission |
| `result` | immutable result path | Complete result and snapshot; incomplete requests fail explicitly |
| `inventory` | none | Bounded read-only owner/reference/byte inventory; no deletion |
| `derive-query` | `--revision EXACT_B03_REVISION` | C04-owned derivative through B03 recipe and lineage validators |
| `serve` | completed job path, `--port 8773` | Verify result/media and serve preserved C03 playback |
| `preflight`, `known-answer` | none | Charged checkpoint/resource and independent scalar/native checks |

Python callers use `processing.api`: `import_sources`, `plan`, `run`, `status`,
`resume`, `cancel`, `result`, `playback`, `events`, `inventory`. The execution methods
take the standard `cli.execute` bounded dispatcher. References are opaque
`{path, record_hash}` objects; persist/pass them unchanged. `reference(owner, path,
kind)` resolves CLI locators once. `playback(job)` returns immutable HTML/bundle
identity and exact scored/context native maps. Results without media say so.

`manifests/processing/d01-interface.json` exports the field/state contracts. Input
sources are full registration values or exact historical sources. Banks are ordered
`{label, grid}` values; query is `native` with exact source/bounds/exclusions/lineage,
or `saved`/`saved-derived` with immutable B03 revision/materialization. Policy contains
`arm` and optional native-witness association; packing is 1..128; refinement is `off`
or `historical`. Historical mode requires the pinned C01/C02/C03 chain. New refinement
for changed dependencies needs a later explicitly declared policy. Unsupported
schemas/transforms/lineage fail. Every eligible group is ranked in complete banks;
the selected experimental arm never changes legacy-mean/original/pitch-off defaults.

## Transactions and recovery

The deterministic graph orders native source features, query, per-source scores,
complete aggregation, optional historical refinement and final publication. Each
job owns progress; semantic rows are shared. States are pending/running/in_progress/
complete/failed/blocked/cancelled; attempts preserve committed and failed evidence.
There is no automatic retry loop. OS locks span claims, reservations and publication;
lock-file bytes are not live owners. Earlier orphan workers still block numerical
concurrency. A separate control lock allows cancellation during work. Explicit resume
archives its cancellation request without erasing it.

Reserve before work and persist the producer proof before encoding. Publish flushed
array bundle, immutable native membership/result, unit commit, progress, complete
result, then last-complete locator. Reopen hashes/native membership before adopting
orphans. Corrupt/missing arrays block explicitly and are never overwritten in place.
Partial temporaries and all failed attempts remain retained and charged. Source
removal creates tombstones and new membership, never file deletion.

Worker settlement uses an immutable journal and replayable post-settlement pool;
reconciliation applies once. Unobservable crash time retains the full reservation
as separately reported uncertainty. Computation can repeat before publication;
verified publication is unique. Metadata rewrites and transaction overhead are
reserved prospectively. Windows sharing/replace failures preserve recoverable commits.
Last-complete is separate from a newer failed/incomplete request.

Historical metadata is planning evidence only. Execution decodes each original,
checks actual PCM/bytes, audits both arrays/native grids and publishes fresh C04
consumer evidence. Arrays remain in their original namespaces. C03 numerical,
report and C04 consumers stay distinct. Imported browser/native proof is historical;
the current media route verifies bytes without copying or re-embedding them.

The finite delivery sequence is `scripts/exercise-processing.py scenarios`, then
`scripts/exercise-processing-recovery.py` (one tracked real termination/restart),
then `scripts/exercise-processing.py historical` / `warm`. Independent clean encodes
share the same pool. There is no reset/force/cache-clear option. Fresh clones lack
private audio, checkpoint and saved artifacts; offline checks remain possible and
historical adoption reports exact missing prerequisites.

Start a completed historical job through `scripts/listen-processing.ps1`, foreground
loopback 8773, Ctrl+C to stop. Its default locator is
`reports/local/c04/historical-warm.json`; an explicit job path is accepted. Earlier
reports/listeners and denied C01 staging folders remain intact. D01 UI and D04
listening review are outside this delivery.

The declared C04 correctness repair retains the first consumer in `consumers/`
and its source proof in `consumer-repair.json`. Encoding, semantic row keys,
source decoding and distance functions are unchanged; native parent exclusions
and event witnesses are stricter. Dispatcher errors retain their domain unit.
Windows workers bypass the venv launcher using the same resolved virtualenv paths
and prefix, so the deadline targets the actual worker PID. No dependency changes.
Old plans keep their exact consumer binding; new work uses an explicit new plan.
Earlier successful evidence and the first clean timeout remain retained/charged.

The later `metadata-compatibility.json` declaration authorizes only an exact
coordinator/metadata upgrade: future attempts reference the immutable consumer,
native row references intern bundle/source keys, and scores bind the digest/count
of the complete ordered candidate key/byte transcript. Arrays, feature identities,
scoring computation, numerical calls and allowance functions are unchanged, with
source/AST proofs checked at consumption. Old records and charges remain intact.
The same paused plan resumes after revalidating committed outputs; unknown drift
still blocks. `api.membership(root, ref)` reads both full and compact memberships,
so D01 does not need private packing details.

The final metadata revision publishes the numerical claim once in the attempt,
shares immutable consumer proofs across non-feature units, and references saved
source scores rather than copying their payload into progress. It publishes the
complete legacy and event-multi group lists; event-legacy is additionally published
when requested. C02's original three arms remain intact. Scoring/aggregation AST
proofs separate these publication choices from unchanged numerical computation.
One exact query matrix may be shared in memory within a worker after its first
successful source/array validation; it never survives a worker or masks a failed
load. Up to eight read-only resume validations share a worker; executable units
remain capped at four. Cancellation during validation stops further admission,
and status shows in-progress while resume validation runs.
