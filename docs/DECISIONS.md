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

## Unresolved assumptions

| Unknown | Consequence and next step | Blocks A01? |
| --- | --- | --- |
| Loulou file, recording version, full-track/excerpt status, original offset, and exact event | A02 first locates and inspects available inputs. Until then, no verified Loulou crop/search claim is possible. | No |
| Instrument identity and useful pitch tolerance | Keep description unverified; compare query/pitch choices in later experiments. | No |
| Runtime, hardware, disk, dependency compatibility, and run budget | Inspect and record limits in A02 before choosing/installing a stack or running expensive jobs. | No |
| Permitted starter catalogue and benchmark audio access | A03/A04 establish actual audio access, provenance, versions, and permitted use; provider metadata is insufficient. | No |
| Pretrained model/checkpoint availability, suitability, and training overlap | A05 documents available candidates and measured results; overlap may remain unknown. | No |
| Separation benefit, generalisation, and real-song relevance | Unrun hypotheses; compare separation later, reserve held-out checks, and obtain the first relevance review at D04. | No |

The linked design context was readable during A01 and agrees with the archived task. Its older Tom's Diner example remains optional future context; the explicit Loulou reference and v2 roadmap govern this foundation. No external audio/dataset/model download was needed for A01.
