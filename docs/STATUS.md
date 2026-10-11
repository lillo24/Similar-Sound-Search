# Project status

Updated 11 October 2026. **A02 complete; ready for A03 — Automated starter catalogue.** Working audio plumbing is established; no retrieval/perceptual result is claimed. Delivery follows the branch/PR/merge/cleanup workflow in [AGENTS.md](../AGENTS.md).

## Foundation and current delivery

- A01 merged through [PR #1](https://github.com/lillo24/Similar-Sound-Search/pull/1), merge `c6e0068692460f3ff64fba8711e2fc9e9589a1cb`. It established the brief, evaluation/record contracts, unverified Loulou reference, and private-artifact exclusions. Its archived prompt and user-owned `AGENTS.md` are preserved.
- A02 pulled current `main` at `6bce07d` (the A02 handoff, PR #2), inspected the actual repository/machine, and uses the dedicated `codex/a02-runtime-inputs` branch with a PR into `main`. The GitHub PR/merge history is the durable delivery record.
- No supplied audio/task attachment was present; explicit project audio locations initially contained only directory markers. The created local audio is labelled deterministic engineering material.

## Delivered in A02

| Area | Evidence |
| --- | --- |
| Reproducible project-local Python 3.12 environment | [pyproject.toml](../pyproject.toml), [complete pins](../requirements.lock), [executed PowerShell setup](../scripts/setup.ps1) |
| Offline diagnostic and actual CPU/decoder route | `sound-search smoke`; [runtime instructions](RUNTIME.md), [sanitized measured evidence](../reports/A02_RUNTIME.md) |
| Explicit file/bounded project inventory | Candidate records with hashes, samples/duration/channels, known provenance and explicit identity unknowns |
| Immutable channel/crop/resample preparation | Atomic bundles, validated reuse, source/derivative hashes, sample counts, tools/parameters and composed maps |
| Conservative numeric tiers and enforced preparation boundaries | [resource profile](../config/resource_limits.json), [enforcement and future-only contracts](RUNTIME.md#resource-policy) |
| Additive input/prepared contract | [0.2 record fields](RECORDS.md#a02-input-and-prepared-records-version-02), [unverified excerpt example](../config/input_context.example.json); original 0.1 Loulou manifest unchanged |
| Meaningful offline correctness validation | [test map](../tests/README.md), Ruff formatting/static checks, packaging/dependency checks and delivered CLI execution |

## Verification and actual environment

Setup created/reused `.venv`, installed the pinned binary resolution, built the editable package, and passed `pip check`. Python 3.12.14, NumPy 2.2.6, SciPy 1.15.3, SoundFile 0.13.1/libsndfile 1.2.2 were executed. Windows 11 x64 exposed four CPU threads and ~16 GiB RAM; a GTX 1660 SUPER with 6144 MiB was detected via `nvidia-smi` without installing a GPU framework. The runtime uses CPU. No working PATH Python beyond Store aliases, FFmpeg, ffprobe, uv, or py launcher was found; bundled Python supplied the project environment.

The complete local checks are in [RUNTIME.md](RUNTIME.md#validation). They cover independent known PCM/hash/RMS answers; 21 accepted encoding/container combinations; corrupt/unsupported/silent/non-finite input; explicit channels and resampler event/count rounding; full-track/known-excerpt/unknown-excerpt maps; composition/offset-once/padding; invalid context/bounds; immutable source, reuse/corruption/change invalidation; disk/memory/output refusals and recovery; atomic write containment, concurrency, hard worker timeout; and missing-Loulou offline smoke. The [evidence report](../reports/A02_RUNTIME.md) records exact results and measured pilot costs.

No GitHub Actions workflow or required CI check exists in the inspected repository; no CI pass is claimed. A02 adds no hosted workflow. Before merge, check current main/head, PR mergeability/reviews/status/check runs and intended diff. Keep local machine/input reports, generated audio, environment, caches and run output ignored. Confirm the archived A01/A02 prompts, `AGENTS.md`, and reference manifest are unchanged.

Repeatable foundation checks still apply: `git diff --check` and staged equivalent; resolve local Markdown links; parse the reference JSON; inspect the intended staged files. Exclusion checks can use `git -c core.ignorecase=false check-ignore --no-index -- data/audio/private.WAV .env manifests/private/source.json` (all should print). Versionable metadata/markers such as `manifests/references/loulou.json`, `reports/A02_RUNTIME.md`, and `data/audio/.gitkeep` must not print when checked separately; exit 1 then means none is ignored.

## Capability and stage status

| Item | State |
| --- | --- |
| A01 durable foundation | Complete; PR #1 |
| A02 Python/input/resource runtime | Complete; Windows CPU WAV/FLAC engineering path exercised |
| Actual Loulou input | Missing; manifest unverified; reference experiment not run |
| A03 catalogue / A04 retrieval benchmarks | Not implemented or run |
| A05 matcher comparison / A06 search and playable results | Not implemented or run |
| B–D event selection, separation, indexing/refinement, interface/package | Future work; first required listening review D04 |
| Perceptual quality, mixture recovery, Loulou relevance | Unmeasured |
| Linux execution, GPU compute, lossy decoding and compressed seek | Unverified/unsupported as described in runtime docs |

## A03 handoff

Reinspect instructions, current main, the [brief](PROJECT_BRIEF.md), [records](RECORDS.md), [evaluation contract](EVALUATION.md), [decisions](DECISIONS.md), source/config maps, and runtime commands. Use a separate A03 branch/PR. Catalogue acquisition must establish real analysable audio and permitted use, enforce the starter download/disk/time/concurrency caps, and keep discovery audio separate from engineering/human-rated evaluation data. A02's download and future model-shortlist limits are configuration contracts awaiting their actual consumers, not implemented download/model controls.

Still needed for a reference-specific experiment: the actual **daoud — Loulou & the loulous** file from the marked version (full recording or existing excerpt around 3:38–4:00), with any available version/provenance and verified excerpt-start evidence. Unknown facts must stay unknown; never crop a short excerpt at 218 seconds from the approximate request. `inspect`/`prepare` can register a candidate without verifying its association; exact target-event selection remains B01. Missing audio does not block independent A03 work, and no similar/dissimilar examples or listening review are requested now.
