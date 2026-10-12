# Project status

Updated 12 October 2026. **A04 harness and controlled suite implemented and exercised; ready for A05 — Candidate matchers and comparison harness.** Published human evidence remains partial/unavailable for scoring; A03 remains partial at 72/120 recordings, 35 artists. No acoustic matcher/perceptual/Loulou result is claimed. Follow [AGENTS.md](../AGENTS.md) for branch/PR/merge/cleanup delivery.

## Foundation and current delivery

- A01 merged through [PR #1](https://github.com/lillo24/Similar-Sound-Search/pull/1), merge `c6e0068692460f3ff64fba8711e2fc9e9589a1cb`: adopted brief/evaluation/records, unverified Loulou reference and private-artifact exclusions.
- A02 merged through [PR #3](https://github.com/lillo24/Similar-Sound-Search/pull/3), merge `2a14cb0c0065d53149269296b84f0c39acdaf1de`: pinned Python CPU runtime, WAV/FLAC inspection/preparation, resource tiers and 32 tests. Its [historical report](../reports/A02_RUNTIME.md) remains unchanged.
- A03 pulled current main `3c1f469` and uses isolated branch `codex/a03-starter-catalogue`; the resulting GitHub PR/merge is the durable delivery record. No extra worktree was created.
- Explicit project input locations contained no supplied local music or Loulou audio. Generated fixtures remain engineering material; the unchanged reference is still missing/unverified.

## Delivered in A03

| Area | Evidence |
| --- | --- |
| Real selectively downloaded discovery music | [Measured quantities/costs/shortfall](../reports/A03_CATALOGUE.md), [frozen selection](../manifests/catalogue/starter/selection.json), [current local-run summary](../manifests/catalogue/starter/summary.json) |
| One source and explicit local import through shared A02 preparation | Internet Archive/blocSonic; explicit permitted-use context, no personal-library scan; [commands/recovery](CATALOGUE.md) |
| Small tested decoder extension | MP3 Layer III through pinned SoundFile/libsndfile, sequential decode, preserved original bytes and channels, explicit timing uncertainty |
| Reproducible provenance and duplicate grouping | Additive [0.3 catalogue records](RECORDS.md#a03-catalogue-records-version-03), original SHA-256 and canonical PCM identity, source snapshots/rights/aliases, [group mapping](../manifests/catalogue/starter/groups.json) |
| Durable bounded acquisition/resumption | Existing numeric tier ceilings unchanged; cumulative payload/retry/partial/crash accounting, finite 2,400-second worker-time/600-attempt job, bounded cursor and worker locks |
| Actual pilot and repeat evidence | 12 real recordings/11 artists in the expanded pilot; subsequent acquisition/resumption and local-ready verification quantified in the report |
| Change-complete offline validation | 58 tests (32 A02 + 26 catalogue), Ruff, setup/dependency/package checks, offline starter smoke and delivered CLI checks; [test map](../tests/README.md) |

The frozen 80-release sample contains 370 eligible provider recordings/35 artists and selects 106 for 120 requested under file/duration/artist-coverage filters. Fourteen requested places are unavailable under that frozen selection; acquisition's additional limit/failure shortfall is measured separately. Public ready records are delivery-machine evidence, not proof of local audio in a fresh checkout. Verify local assets/private registration before consumption. No catalogue audio, raw provider snapshots, private paths, caches, environment or ledgers are committed.

## Environment and verification

Windows 11 x64, Python 3.12.14, four CPU threads, approximately 16 GiB RAM; CPU processing with NumPy 2.2.6, SciPy 1.15.3, SoundFile 0.13.1/libsndfile 1.2.2. Native TLS uses pinned truststore 0.10.4 after verified default-context certificate-chain failure. A detected 6 GiB GPU is unused; no FFmpeg/GPU framework is required. [Runtime](RUNTIME.md) retains setup, A02 commands and numeric limits; [catalogue documentation](CATALOGUE.md) owns acquisition-specific behavior.

Full local validation includes independent PCM answers; accepted WAV/FLAC encodings and MP3 timing/truncation; channel/crop/resample/composed maps; original/derivative immutability and corruption; controlled HTTP failures/limits/retries; lifecycle/recovery/cumulative budgets; deterministic selection/grouping and actual CLI batch/lock behavior. The offline diagnostic remains reference-independent and network-free. Use `--tier starter smoke` when the real workspace exceeds the unchanged smoke tier's 256 MiB managed cap.

No GitHub Actions workflow/required CI check exists in the inspected repository; no CI pass is claimed and none was added. Before merge, check latest main/head, mergeability/reviews/status/check runs and intended diff. The evidence report records actual local check outcomes and limits. Preserve `AGENTS.md`, archived A01/A02/A03 prompts and `manifests/references/loulou.json`.

## Capability and stage status

| Item | State |
| --- | --- |
| A01 durable foundation | Complete; PR #1 |
| A02 Python/input/resource runtime | Complete; bounded CPU WAV/FLAC foundation |
| A03 acquisition/ingestion | Implemented and exercised; real local discovery subset, explicitly partial against 120 requested |
| Actual Loulou input | Missing; manifest unverified; reference experiment not run |
| A04 controlled construction and evaluation harness | Complete engineering delivery: 208 assets, 160 queries; 88 tests; [evidence](../reports/A04_BENCHMARKS.md) |
| A04 published human evidence | Partial: 16 AIFF stimuli + 120 observations downloaded/validated; zero eligible scoring pairs due to unresolved rights/original mapping |
| A05 matcher comparison / A06 search and playable results | Not implemented or run |
| B–D event selection, separation, indexing/refinement, interface/package | Future; first required listening review D04 |
| Perceptual quality, mixture recovery, Loulou relevance | Unmeasured |
| Linux live acquisition/GPU compute/arbitrary compressed seek | Unverified; sequential MP3 fixture behavior only |

## A05 handoff

Reinspect current instructions/main, [brief](PROJECT_BRIEF.md), [records](RECORDS.md), [evaluation commands](EVALUATION.md#a04-delivered-commands-and-protocol), [A04 evidence](../reports/A04_BENCHMARKS.md), source/config maps and the actual implementation. Use a separate A05 branch/PR. The frozen protocol/suite use 104 assets and 80 queries per partition, four procedural families and two real-background families per split. Development choice uses source-consistency candidate coverage then controlled performance/pitch coverage and cost; exact-instance diagnostics do not select the winner. Preserve the explicit published-data exclusion and reserve held-out model scores for A06. No A04 model, checkpoint, acoustic baseline, retrieval index, separation or UI was implemented.

The A04 read-only consumer verifies the four music backgrounds under its separate finite budget, without touching exhausted A03 accounting. Backgrounds use seconds 2..10 of the centred 30-second derivatives; sequential-original intervals and unknown master offsets are recorded. The generated suite has 96 renders, 112 mixtures, three performances/two pitch conditions, -12/0/+12 dB levels and absent/multiple-event cases. Full original bytes and reference remain unchanged. The model-candidate cap of three remains an A05 contract. [A04 commands](EVALUATION.md#a04-delivered-commands-and-protocol) cover local restoration, generation/reuse, independent validation and scoring recovery.

Still needed for a reference-specific experiment: the actual **daoud — Loulou & the loulous** file from the marked version (full recording or existing approximately 3:38–4:00 excerpt), with any version/provenance and verified excerpt-start evidence. Unknowns stay unknown; never crop an already-short excerpt at second 218. Exact target-event selection remains B01. Missing audio does not block independent A04 work, and no labels/listening review are requested now.
