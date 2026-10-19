# Project status

Updated 14 October 2026. **A06 local exact passage search and original playback delivered.** All 72 local A03 recordings are indexed over full available durations, with single/multiple-example demos and one unchanged EfficientAT held-out check. Human agreement and Loulou relevance remain unavailable; A03 remains partial against its acquisition target. Follow [AGENTS.md](../AGENTS.md) for branch/PR/merge/cleanup delivery.

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
| A06 search, playable results and held-out model check | Implementation/index/demos/final check complete: 72/72 local recordings, 44,025 passages, original stereo clips; 21/24 source-consistency held-out query hits at K=1 and 32/32 events at K=10. Extra whole-index repeat partial at the fixed cap; later catalogue browser controls unavailable. [Evidence](../reports/A06_SEARCH.md) |
| B01 event selection | Implemented with native/manual crops, experimental proposals, two catalogue searches and verified playback. Bounded development evaluation partial; explicit/coarse default. [Evidence](../reports/B01_EVENTS.md) |
| B02–D separation, indexing/refinement, interface/package | Future; first required listening review D04 |
| Perceptual quality and Loulou relevance | Unmeasured; real-catalogue candidates are not confirmed matches; controlled A05/A06 metrics remain separate |
| Linux live acquisition/GPU compute/arbitrary compressed seek | Unverified; sequential MP3 fixture behavior only |

## A06 delivery and handoff

The [A06 evidence](../reports/A06_SEARCH.md), [search commands](SEARCH.md) and [public records](../manifests/search/README.md) own current search behavior. A05's choice stays stage A05. A06 declared its immutable final run before inference, then ran all eighty held-out queries using that exact configuration/checkpoint/protocol/suite, preprocessing/grid, cosine distance, pitch zero and empty refinement. Its 21/24 source-consistency query hit@1 compares with development 24/24; no retuning or second model was selected.

A06 has its own fixed finite indexing/query/final-check ledger; old A03/A04/A05 ledgers and all prior inputs/evidence remain unchanged. The 72-file index contains 123 compact shards, 67,638,144 vector-file bytes and 3.098 unique source hours. Parent recordings/known duplicates are excluded; each demo returns ten distinct recording candidates. Original native-channel/rate crops are verified sample by sample and exported as PCM16 WAV. Unknown master offsets remain visibly available-file/excerpt-relative.

Run `.\scripts\listen-search.ps1` from the repository root and visit `http://127.0.0.1:8766/`; Ctrl+C stops the owned loopback listener. The completed index/query/report remain ignored in this delivery checkout after merge. A fresh checkout needs its matching private inputs/checkpoint/registrations; it cannot infer availability from public manifests. Reuse still consumes finite read/worker allowance. The post-inspection repair only splits catalogue ranking into four-recording serial workers and validates unchanged math/extraction/scoring against frozen source proofs.

The fixed A06 worker-time allowance is consumed; further compute refuses without
resetting/increasing anything. All 123 immutable arrays remained unchanged, both complete
catalogue ranks reused eligible shards, and single-query preparation returned reuse.
An extra full-index repeat refreshed 57/72 receipts before its final bounded worker
was terminated. Later Chrome control required an extension update; catalogue play/pause/
seek is not claimed, while earlier engineering playback checks passed on identical code.
The listener remains independent of the exhausted compute job. [Resource record](../manifests/search/resources.json)
retains all costs and gaps.

The controlled suite retains 104 assets/80 queries per split, unchanged audio/truth/recipes, four procedural families and two real-background families per split. Backgrounds still use seconds 2..10 of the centred A03 derivatives with decoded-original intervals and unknown master offsets. A06 preservation audits cover 7,121 earlier files. Grey1977 remains quarantined, CIR lacks established terms, and standard CLAP exceeds the download cap.

The actual marked-version daoud — Loulou & the loulous audio and provenance/offset evidence remain unavailable for a verified reference experiment. Never crop a short excerpt at second 218. D04 remains the first required listening review; no new labels are requested for independent A06 engineering.

## B01 delivery and B02 handoff

[B01 evidence](../reports/B01_EVENTS.md), [event commands/contracts](EVENTS.md) and
[sanitized records](../manifests/events/README.md) own the current event-selection
workflow. The audited B01 consumer validates the completed A06 index read-only, with
new accounting and current-code identity separated from historical feature identity.
Old ledgers, originals, manifests, predictions/reports and all feature arrays remain
unchanged: 7,944 protected files passed byte/size/mtime preservation checks.

Automatic selection did not meet its prospective gates. Corrected note precision is
13.76%, recall 46.875%; coarse/single hit@1 is 5/8 and multiple 4/8, with 8/9 render
targets recovered at ten in each mode. The fixed regions truncate two accompanied
phrases and omit one target, so the +12dB present-reference and oracle comparison are
partial. Three invalid oracle outputs count as misses; no new model queries replaced
them after the forty-query cap. Explicit/manual native crops remain the default.

The named substitute's three distinct real spans are heavily overlapping and
duration-censored, with no isolated-layer or verified-note claim. Both catalogue
searches score 43,690 eligible passages, exclude the reference/duplicate parent and
return ten distinct candidates. Query order/duplicate reuse preserves identity and
three unique examples. CPU work used 1,231.445/3,600 worker seconds, with all retries
and an explicit missed-root-read correction retained. No catalogue feature was rebuilt.

Run `.\scripts\listen-events.ps1`, then visit `http://127.0.0.1:8767/` for the event,
context and single/multiple search pages. Chrome load/play/pause/seek and HTTP media,
hash/range/containment checks passed. A fresh tab recovered one earlier inspection
timeout; no browser extension/driver changed. A06's saved listener still works on 8766.
Private artifacts remain in the delivery checkout; a new clone needs matching inputs.

B02 should prospectively compare optional isolation with native/no-isolation crops,
validate actual source/region geometry before inference, retain absent/censored cases,
and use its own finite accounting. Preserve the inspected development/final evidence;
do not turn it into a fresh holdout. Loulou/version/offset and human relevance remain
unmeasured, with first required listening review D04. B02 was not started automatically.
