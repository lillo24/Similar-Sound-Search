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
