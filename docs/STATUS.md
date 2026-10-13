# Project status

Updated 13 October 2026. **A05 acoustic/pretrained development comparison delivered; provisional EfficientAT MN04 default ready for A06.** The corrected hit@1 protocol was frozen before rankings. Human agreement remains unavailable and A03 remains partial. No held-out model, cross-song or Loulou success is claimed. Follow [AGENTS.md](../AGENTS.md) for branch/PR/merge/cleanup delivery.

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
| A05 matcher comparison | Complete controlled development comparison: two genuine methods, 80 queries each, provisional EfficientAT MN04; [evidence](../reports/A05_MATCHERS.md) |
| A06 search, playable results and held-out model check | Next; not implemented or run |
| B–D event selection, separation, indexing/refinement, interface/package | Future; first required listening review D04 |
| Perceptual quality, cross-song recovery, Loulou relevance | Unmeasured; controlled mixture/source metrics are separate A05 evidence |
| Linux live acquisition/GPU compute/arbitrary compressed seek | Unverified; sequential MP3 fixture behavior only |

## A06 handoff

Reinspect current main/instructions, [matcher setup/commands](MATCHERS.md), [A05 measured evidence](../reports/A05_MATCHERS.md), [choice](../manifests/matchers/choice.json), source maps and actual implementation. Use a separate A06 branch/PR. The provisional EfficientAT MN04 choice achieved 24/24 source-consistency development query hits at K=1, versus acoustic 17/24, constant 16/24 and seeded random 9/24. This is a small four-family controlled-source result, not human timbre accuracy. The selected configuration/checkpoint, protocol/suite, preprocessing and distance are frozen; no tuning sweep or held-out model run occurred.

A06 must explicitly initiate its final check with the exact choice; A05's choice remains `stage: A05` and cannot bypass the held-out guard. A05 has four run operations and twelve smoke attempts already charged; A06 must define its own finite work for its distinct stage, without resetting A03/A04/A05 ledgers or using a replacement job to repeat development tuning. Feature reuse retains original model cost and validates source/checkpoint/config identity. Refinement, a real-catalogue index/search and playable-result delivery remain A06/later work.

The controlled suite retains 104 assets/80 queries per split, unchanged audio/truth/recipes, four procedural families and two real-background families per split. The atomic comparison pair changes only the pre-ranking grid/selection policy. Backgrounds still use seconds 2..10 of the centred A03 derivatives with decoded-original intervals and unknown master offsets. All 396 preserved audio/reference/accounting files retained exact hashes, sizes and modification times. Grey1977 remains quarantined, CIR lacks established terms, and standard CLAP exceeds the download cap.

The actual marked-version daoud — Loulou & the loulous audio and provenance/offset evidence remain unavailable for a verified reference experiment. Never crop a short excerpt at second 218. D04 remains the first required listening review; no new labels are requested for independent A06 engineering.
