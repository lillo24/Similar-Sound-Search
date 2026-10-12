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
