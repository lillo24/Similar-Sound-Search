# Decisions and assumptions

Adopted on 11 October 2026 for A01. These are foundation decisions, not validated audio capabilities. Changes should record their reason and affected evidence.

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-001 | Use the canonical `lillo24/Similar-Sound-Search` checkout; preserve the archived A01 prompt. | Keeps future work attached to existing Git history. The initial A01 inspection used `ae9da07b75a37137004fe7a62510c7faca3a22c5`; delivery starts from `bc9fc94dcb503d59266d154117f57b3faad23587`, which adds the governing `AGENTS.md`. |
| DEC-002 | Prefer a Python audio-processing core; defer dependency/runtime setup to A02. | There is no existing application stack to preserve. Python is the requested default; no specific Python version, package manager, GPU stack, or audio library is selected yet. |
| DEC-003 | Rank sound character first, approximate pitch second, and defer phrase rhythm. | Matches the product direction; preserve individual event evolution and keep any pitch contribution inspectable. |
| DEC-004 | Start from original audio and compare an acoustic baseline with pretrained representations. | Provides a simpler comparison and avoids assuming custom training is necessary. Model/checkpoint selection and optional separation require later measured evidence. |
| DEC-005 | Use a documented draft JSON record contract and an explicitly unverified Loulou manifest. | Preserves the request without inventing a file, hash, source version, instrument, or verified event. No database, validator, or retrieval abstraction is needed for A01. |
| DEC-006 | Map processing time to the original available file, then apply a verified recording offset once. | Prevents double cropping/offsets and keeps unknown-offset excerpts honestly excerpt-relative. Original mixture playback is required even for separated features. |
| DEC-007 | Keep published perceptual evidence, generated diagnostics, and real-song discovery distinct. | Source identity/location is not a human relevance label. Query copies are diagnostic, not discoveries. |
| DEC-008 | Group related examples before development/held-out splitting; freeze criteria before comparison. | Limits recording/preset leakage and retrospective target setting. No arbitrary timbre-quality percentage is justified in A01. |
| DEC-009 | Reserve local data directories and exclude audio, weights, caches, and secrets from Git. | Keeps private/large artifacts local while allowing sanitized manifests and evidence summaries to be versioned. Exclusions do not protect already tracked content. |
| DEC-010 | Keep A06 internal and the first required listening review at D04; default to local resources and no paid services. | Automates catalogue/test/model work without upfront labels or routine approval gates. The present handoff stops at A01 because later prompts define later scope. |

## A02 runtime decisions

A02 additions, 11 October 2026:

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-011 | Python 3.12 local environment with a complete pinned binary NumPy/SciPy/SoundFile resolution; CPU path only. | Actual Windows session had a working bundled 3.12.14 but no usable PATH interpreter/FFmpeg. Wheel libsndfile provides tested WAV/FLAC without global/driver changes. A 6 GiB NVIDIA GPU was detected without installing a framework; GPU computation is untested. |
| DEC-012 | Explicit file or bounded project audio inventory, optional evidence context, additive 0.2 candidate/prepared records. | Technical decoding cannot verify recording/version/event/offset. The 0.1 Loulou manifest remains unchanged and missing. No A02 reference experiment is claimed. |
| DEC-013 | Required channels/rate, validated optional file-relative crop, zero-phase polyphase resampling, composed original-file mapping. | Prevents implicit target-dropping, changed playback speed, double excerpt offsets, and invented recording time. Fractional output padding has no claimed original source span. |
| DEC-014 | Hash/version-keyed atomic derivative bundles with verified reuse; fail on corruption. | Keeps originals immutable and changed source/context/parameters from resolving to stale derivatives. This is bounded preparation reuse, not C04. |
| DEC-015 | Numeric smoke/starter tiers, single locked worker, hard deadline, memory/disk/output preflight. | Limits fit observed ~16 GiB RAM/four CPU threads and a short offline pilot. Future download/shortlist caps are contracts awaiting A03/A05 enforcement; no paid service/upload/deployment is authorized. See [runtime limits](RUNTIME.md#resource-policy). |
| DEC-016 | Small local Ruff/unittest/CLI validation; no hosted CI workflow added. | The repository had no CI/required checks. Complete manual commands validate every changed area without recurring runner cost, model downloads, or unrelated suites. |

## Remaining assumptions after A02

| Unknown | Consequence and next step | Blocks A02? |
| --- | --- | --- |
| Loulou file, recording version, full-track/excerpt status, original offset, and exact event | No actual file was supplied/present in A02's project inputs. Inspect a supplied file with evidence context before any verified Loulou crop/search claim. | No |
| Instrument identity and useful pitch tolerance | Keep description unverified; compare query/pitch choices in later experiments. | No |
| Larger workloads, Linux/GPU compute, and lossy decoder/seek behavior | Windows CPU runtime and conservative limits are now exercised; measure new routes before expanding their claims or resource budgets. | No |
| Permitted starter catalogue and benchmark audio access | A03/A04 establish actual audio access, provenance, versions, and permitted use; provider metadata is insufficient. | No |
| Pretrained model/checkpoint availability, suitability, and training overlap | A05 documents available candidates and measured results; overlap may remain unknown. | No |
| Separation benefit, generalisation, and real-song relevance | Unrun hypotheses; compare separation later, reserve held-out checks, and obtain the first relevance review at D04. | No |

The linked design context was readable during A01 and agrees with the archived task. Its older Tom's Diner example remains optional future context; the explicit Loulou reference and v2 roadmap govern this foundation. No external audio/dataset/model download was needed for A01.

## A03 catalogue decisions

A03 additions, 12 October 2026; [commands/contracts](CATALOGUE.md) and [measured evidence](../reports/A03_CATALOGUE.md) supersede the historical A02 catalogue/MP3 unknowns above.

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-017 | One selectively downloadable Internet Archive/blocSonic adapter with explicit audio-licence evidence and deterministic artist/genre coverage. | FMA/MTG-Jamendo bulk audio exceeds the starter transfer policy. Retain actual local music, exact source snapshot/ordering/exclusions and honest label/genre bias; explicit provider snippet qualifiers remain unknown-offset excerpts. No metadata-based similarity claim. Pilot expands 60 to 80 releases under the same durable allowance. |
| DEC-018 | Add sequential MP3 Layer III through pinned SoundFile/libsndfile; native verified TLS through pinned truststore 0.10.4. | Existing decoder can handle the selected source without FFmpeg/GPU. Native Windows trust resolves the observed certificate-chain failure without disabling verification. Known MP3 fixtures measure this route; arbitrary seek/master alignment remains unknown. |
| DEC-019 | Immutable original bytes, versioned canonical float32 PCM identity and a centred 30s preserved-channel 16 kHz analysis derivative. | Original full-track mixtures remain available. Explicit limited analysis coverage fits disk/output/memory policy and maps back through A02; decoded MP3 derivatives are not described as lossless originals. |
| DEC-020 | Durable per-job payload/attempt/worker-time ledger, finite invocations, locked owned-write disk accounting and asset cursor. | Metadata/retries/partials/resumption/crashes cannot replenish download/time allowance. Worker/disk caps remain unchanged. Pilot measurements justify reducing per-read fsync/inventory overhead with a 1 MiB conservative reservation; every worker scans actual disk and refreshes around preparation. |
| DEC-021 | Add catalogue schema 0.3 with per-entry public descriptors, private local registration, explicit lifecycle and established duplicate-family edges. | Manifests stay within 1 MiB, fresh checkout reconstruction uses frozen descriptors, metadata alone cannot count as local readiness, and aliases retain provenance. No title-only/fuzzy grouping or A04 splits. |
| DEC-022 | Keep live acquisition separate from fully offline HTTP/decoder tests and the unchanged missing-reference diagnostic. | Report actual quantities/access/costs, not mocked network success. A03 does not claim retrieval relevance or request a listening review; A04 is next. |

## A04 evaluation decisions

12 October 2026; [commands/protocol](EVALUATION.md#a04-delivered-commands-and-protocol) and [measured evidence](../reports/A04_BENCHMARKS.md) define the delivery.

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-023 | Inspect pinned individual Grey1977 AIFF/matrix files; quarantine all human-scoring pairs. | Download/decoder checks establish availability, not reuse permission or an independent original row mapping. Preserve supplied raw matrix/mask and explicit loader order; do not copy/install the upstream Torch stack or treat its argsort permutation as ranks. |
| DEC-024 | Add PCM/float AIFF through the pinned shared decoder; share transport via an explicit pinned GitHub policy with unchanged Archive default. | No new dependency or catalogue permission broadening. Native human audio is never automatically cropped to A03's 16 kHz/30s policy. |
| DEC-025 | Eight procedural families/four mechanisms, balanced phrases/pitches/levels, known insertion truth and independently audited mixtures. | Lightweight CPU generation fits measured limits. Preset identity is a source proxy; transformed sounds and different presets are not human similarity/dissimilarity labels. |
| DEC-026 | Freeze related-preset and A03 duplicate/artist families before construction, including background roles. | Prevents crop/performance/encoding/role leakage. Unknown lossy copies and future pretraining overlap remain unknown; tiny human groups receive descriptive reporting without cellwise uncertainty. |
| DEC-027 | Separate durable A04 transfer/time/construction ledgers and read-only catalogue consumer. | Exhausted A03 allowance and immutable originals remain unchanged. Existing worker/memory/disk ceilings are retained; crash work remains conservatively charged. |
| DEC-028 | Explicit candidate/refined prediction contract, signed average ranks, one-to-one event assignment and missing denominators. | Candidate omissions cannot be hidden by refined output, overlapping hits cannot inflate target recall, constants remain undefined, and forced rankings cannot assert presence. Oracle checks prove harness behavior only. |
| DEC-029 | Development-only lexicographic selection rule frozen before A05; held-out matcher scoring requires an A06 choice declaration. | Exact-instance diagnostics do not choose the winner. Human evidence stays unavailable unless a reviewed protocol revision establishes permission/alignment. Later held-out tuning must disclose contamination; D04 remains the first listening review. |

## A05 development comparison decisions

13 October 2026; [protocol/commands](MATCHERS.md) and [measured evidence](../reports/A05_MATCHERS.md).

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-030 | Prospectively replace saturated primary hit@10 with source-consistency candidate query hit@1, preserving secondary/ties, pools, truth, K and IoU. | Actual constant chronological hit@10 is 100%; analytical random expectation 99.2028238%. Freeze query-length/.25s/tail grid before rankings and atomically bind revised protocol/suite; retain originals in history without audio regeneration. |
| DEC-031 | Freeze one fixed-scale spectral/cepstral/envelope baseline and one MIT EfficientAT MN04 checkpoint. | Four-megabyte pretrained model fits CPU limits; CIR lacks established terms, standard CLAP exceeds transfer cap. No second checkpoint, hyperparameter sweep, learned fit or hidden pitch term. |
| DEC-032 | Optional hash-pinned Windows CPU Torch setup; reproduce native evaluation mel equations without TorchAudio extension. | TorchAudio DLL loading failed; all 65,664 coefficients match pinned native source exactly. Root renderer versions remain unchanged. Strict local weights/eval mode and network refusal prevent hidden downloads. |
| DEC-033 | Waveform/rate-only representation boundary, truth-independent grid, source-bound feature cache and prediction publication before scoring. | Labels/filenames/truth cannot reach features; finite shape/hash checks and explicit missing/error states prevent fabricated embeddings or success-shaped failures. |
| DEC-034 | Separate finite A05 ledger and exact locked owned-array disk accounting. | Original audio and A03/A04 accounting remain intact; crash reservations persist. Replacing repeated disk scans changes publication overhead only, while model cost separately measures loads, unique extraction and ranking and survives cache reuse. |
| DEC-035 | Provisional EfficientAT default by the frozen rule; reserve held-out/cross-song/human conclusions. | Development source-consistency hit@1 is 24/24 versus baseline 17/24, constant 16/24 and seeded random 9/24. Query hits do not mean perfect localisation/multiple-event recall. Choice remains A05; A06 must explicitly initiate final checks. |

## A06 local search decisions

14 October 2026; [commands/contracts](SEARCH.md) and [measured evidence](../reports/A06_SEARCH.md).

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-036 | Preserve the selected A05 descriptor/checkpoint; freeze separate A06 search policy and a pre-inference declaration for exactly one final check. | All eighty held-out queries retain their denominators. Source-consistency hit@1 is 21/24, event recovery at ten is 32/32; weak results do not select another model. Pitch and refinement remain absent from that check. |
| DEC-037 | Index every local ready original over its full available-file duration with 2.4s/.25s/unique-tail windows and compact 512-vector shards. | The development cost pilot retained this grid; 72 recordings yield 44,025 windows and 3.098 unique hours. Exact bounded ranking fits this scale without a new dependency/service. Sequential original validation preserves high-frequency input and known coordinate uncertainty. |
| DEC-038 | Explicit complete-content queries, identical-PCM deduplication and mean per-example distances; one best scored passage per distinct recording/known duplicate group. | Query order and repeated copies cannot change weights. All parents are excluded while another recording by the same artist remains eligible. No title/artist/truth similarity terms or calibrated presence claim are introduced. |
| DEC-039 | Original native-channel/rate playback clips with declared PCM16 conversion/gain, separately scored/context bounds and a verified loopback allowlist. | Numeric checks establish crop conversion and mapping; browser checks establish load/play/pause/seek and visible missing-media failure. External MP3/master seeking and human relevance remain unverified. |
| DEC-040 | Separate fixed finite A06 accounting, atomic progress and immutable feature reuse; retain all interruption charges. | No old acquisition/model allowance is reset. Native exit, worker deadline and file-publication failures are explicit and recover under unchanged identities. Reuse consumes read/worker cost; an idle listener performs no indexing. |
| DEC-041 | After final-score inspection, split catalogue ranking into four-recording serial workers without changing distances, selection, exclusions, intervals or features. | The original all-catalogue worker exceeded 120 seconds. The committed execution-repair proof binds old/current code and validates unchanged critical syntax against exact frozen originals, preserving the declaration, index and results. No second held-out experiment follows. |

Loulou remains missing/unverified. The predetermined development-side catalogue crop
and separate generated known-target fixture are labelled engineering demos. A06 ends
this batch; automatic event/layer selection, separation and a listening judgment remain
later-stage work, with the first required review at D04.

## B01 event-selection decisions

19 October 2026; [contracts](EVENTS.md) and [measured evidence](../reports/B01_EVENTS.md).

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-042 | Explicit B01 accounting and audited read-only A06 compatibility, with separate consumer and historical feature identities. | Keep closed A06 final/ledger guards and frozen adapters/math; validate sources/groups/grid/checkpoint/shards. Necessary consumer receipts never re-embed catalogue features. |
| DEC-043 | One deterministic channel-safe envelope/flux setting, independent explicit selection and native A02 crops; preserve overlap/censoring. | Onset-to-next-onset cuts cannot establish complete releases. Manual intervals remain reliable; fixed mean unique-PCM distances, all-parent exclusion and pitch off remain unchanged. |
| DEC-044 | Keep automatic proposals experimental and explicit/coarse default after the fixed development batch. | Corrected precision 13.76% / recall 46.875%; single matched coarse 5/8 hit@1, multiple fell to 4/8. No settings tuning or replacement inference after the forty-query cap. |
| DEC-045 | Correct saved note truth using actual reference insertions and count invalid oracle outputs as misses. | Two selected phrases are truncated and one target lies outside the region. Preserve original predictions/summary and all denominators; +12dB present-reference/oracle coverage remains partial. No new held-out check. |
| DEC-046 | Preserve failed-operation charges and exact native selections during accounting/report repairs. | Add omitted parent hash-read cost once; stale selection metadata is refused and regenerated with identical bounds/audio/features. Copy WAV conversion receipts for resumable playback; final browser/HTTP checks pass. |

## B02 optional-processing decisions

19 October 2026; [contracts](SEPARATION.md) and [evidence](../reports/B02_SEPARATION.md).

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-047 | Offline HPSS plus genuinely audio-conditioned fixed-template activation masks; no learned separator admitted. | Preserve the pinned matcher environment, bounded CPU/temporary memory and zero acquisition; DSP components are not instrument identities. |
| DEC-048 | Independently verify actual saved insertions/support/cues/TBR, then freeze a distinct B02 development protocol. | Twelve complete positives and four separate controls; inspected families are not a fresh holdout, and no B01 oracle repair is performed. |
| DEC-049 | Original audio remains default after the fixed comparison. | Guided top-1 improves 2/12 to 5/12 but loses one baseline success and fails attack/tail preservation. Broad processing also misses retrieval/preservation gates. |
| DEC-050 | Preserve refusals/charges and declare bounded context/report corrections. | A 12s real stereo context fails the fixed 128 MiB allocation guard; 8s keeps the same event/cue with lead/tail context. Report-only repairs preserve producing code/predictions and require a fresh B02-owned read-only index receipt. |

## B03 query/revision decisions

20 October 2026; [contracts and migration](QUERIES.md), [prospective records](../manifests/queries/README.md)
and [delivery evidence](../reports/B03_QUERIES.md).

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-051 | Separate display heads, immutable portable recipes, validated materializations and exact search executions. | Labels and pitch-only revisions reuse unchanged PCM/features; every contributing parent/cue exclusion survives deduplication. Explicit bindings support relocation without rewriting historical receipts. |
| DEC-052 | Retain the unchanged conservative pitch estimator; use an explicit .03 / twelve-semitone absolute-register mean penalty with all-query reliability gate. | Timbre selects one passage per group; pitch only reranks the complete eligible winner set. Missing/ambiguous pitch contributes zero with reasons. Original audio/pitch off remain defaults irrespective of controlled outcomes. |
| DEC-053 | Give B03 fixed offline accounting and read-only B02/A06 adapters; declare shared hooks before processing. | No historical ledger is reopened, no catalogue feature is rebuilt, and frozen model/pitch/math/guard contracts remain enforced. |
| DEC-054 | Register the newly supplied MP3 separately from historical missing-reference evidence, preserving its full 218..240s original mixture. | Technical support does not verify identity, marked-version alignment, rights, master offset or intended layer. Use the existing Donnie guided event/cue to demonstrate processing reuse without a new separation experiment. |
| DEC-055 | Freeze independent insertion/support checks and one eight-case/sixteen-arm development batch before comparison. | Familiar deterministic families are inspected development, not a fresh holdout or human timbre truth. Keep all failures and denominators; no sweep or replacement reference after rankings. |
| DEC-056 | Declare a two-module execution-only repair before any predictions; share one unchanged adapter per worker and checkpoint pending units. | PyTorch's interop setting is process-wide. Preserve the original failed attempt, cached features, pending case/arm reservation and every retry charge; recover an immutable prediction before repeating inference. Windows memory failures likewise retain progress and charges. |

## C01 bank decisions

20 October 2026; [contracts](INDEXING.md), [prospective protocol](../manifests/indexing/protocol.json)
and [evidence](../reports/C01_INDEX.md).

| ID | Decision | Reason / consequence |
| --- | --- | --- |
| DEC-057 | Separate versioned bank policies, immutable plans/snapshots, mutable progress and exact per-bank executions. | Reference original A06 shards through a fresh C01-owned audited consumer; keep all banks separately addressable and original/pitch-off defaults unchanged. C02 owns combination/calibration/aggregation. |
| DEC-058 | Compare 1.2/2.4/4.8s with a common development hop, then admit at most one production policy by predeclared support/quality/cost. | Both new durations lose one of six baseline source-consistency successes. The experimental 4.8s/1s policy provides full-event support and fits measured budgets; containment is not a localization or relevance win. |
| DEC-059 | Keep the closed batch and independently verify its strict full-2.4s support denominator. | The raw tally included the .3s short-file control. Geometry-only verification gives 0/10, 5/10 and 10/10, retains every case/ranking/failure and proves the same admission. No replacement inference or result-dependent case deletion is allowed. |
| DEC-060 | Restrict component indexing to validated query-independent HPSS regions; reject actual guided outputs as generic stems. | Exercise two components on one controlled mixture and one real 8s region, preserving all cue/parent ancestry, native maps and output checks. No catalogue-wide separation or instrument claim is justified. |
| DEC-061 | Preserve producing feature versions separately from later consumer/metadata verification. | Feature identities, samples, model/math and native grids stay fixed. Compact hashed references keep snapshots below the existing 1 MiB JSON limit; saved-query representation and frozen-function audits remain explicit. A completed-bank rerun validates sources/arrays under the same finite ledger; new encoding still requires its declared producer. |
