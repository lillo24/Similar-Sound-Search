# A05 — Candidate matchers and development comparison

Delivery evidence, 13 October 2026, implementing [the archived A05 prompt](../history-implementations/Similar_Sound_Search_A05.md) from base `383b737` on `codex/a05-matchers`. The implementation PR/merge identifies the final source revision. Package/renderer identity remains `0.3.0` / `a04-suite-1`; the new representation boundary is `a05-representation-1`.

**Provisional default: EfficientAT MN04**, selected strictly by the prospectively corrected rule. Both genuine methods supplied all 80 development outputs. Source-consistency candidate query hit@1 is 24/24 for EfficientAT and 17/24 for acoustic, versus constant 16/24 and seeded random 9/24. This is controlled-source evidence from four procedural families, not human timbre accuracy, cross-song retrieval, a held-out check or Loulou relevance.

| Evidence category | State |
| --- | --- |
| Prospective comparison correction | Complete: original real-scorer geometry audit, versioned grid/primary correction, atomic paired records and preserved history before rankings. |
| Acoustic baseline | Installed/exercised/complete: 56-dimensional fixed-scale spectral/cepstral/envelope representation, actual audio and all 80 queries. |
| Genuine pretrained comparison | Installed/exercised/complete: official MN04 weights, strict CPU load, native evaluation frontend, all 80 queries. Two scored methods; no sweep or second checkpoint. |
| CIR / standard CLAP | Unavailable / excluded at preflight: unresolved CIR terms; CLAP exceeds transfer cap. Neither weights file downloaded or counted as an executed comparison. |
| Human judgments / reference | Unavailable for scoring: Grey1977 remains quarantined with zero eligible pairs; Loulou remains unverified/missing. A03 remains partial at 72 recordings/35 artists. |
| A06 held-out/cross-song/playback | Not run or implemented by A05. Choice stage remains A05. |

## Frozen comparison and sources

Original A04 protocol `b5fd2d1e87040e8a9b929a65a4b3a2d92ae69e99dfab88e3e0c87c28aa70093d` and suite `59b781f3fbf75a7bad52f49c051e02142528f402cbde1c74041927ef4f081a2a` are preserved in [protocol-history](../manifests/evaluation/protocol-history/) and [suite-history](../manifests/evaluation/suite-history/). Before candidate rankings, the original scorer reproduced 24 mixture windows and 8/7/7 matching-window counts at -12/0/+12 dB. Constant chronological hit@10 is 100% and macro hit@1 is 66.6667%. The analytical uniform-random expectations are **99.2028238% at K=10** and **30.555556% at K=1**, calculated from `1-C(N-m,K)/C(N,K)`. Seed 42105 supplies one separately reported random-order diagnostic, whose observed hit@1 is 37.5%; that is not the analytical expectation.

Protocol `2026-10-13.1` prospectively freezes complete controlled renders and query-length mixture windows every .25 seconds with a unique end-aligned tail, then selects by macro source-consistency candidate **query hit@1**, controlled performance/pitch hit@5, measured model time and lexical method/config identity. K=1/5/10, candidate pools, IoU>=.5, one-to-one event matching, family splits, audio/truth/recipes and A04 construction accounting are unchanged. No accuracy threshold is invented. The [atomic comparison pair](../manifests/evaluation/comparison.json) publishes both revised self-hashed records; canonical protocol/suite files are recoverable mirrors. Fresh construction uses the same revised defaults, and reuse verifies the authoritative suite identity.

| Identity | SHA256 |
| --- | --- |
| Revised protocol | `07af66b37db00d6a6dd4bea87c9636b06aa9dbd43c75e8164be4568bd94b0048` |
| Revised suite | `d4c59416e5d4bb4aeddfbefa933a3a0f18691a25957e3623f1743d2951806441` |
| Acoustic config | `2f1e8c103ada9bc9c819fa0b9b3e0217c2f307994cfc9443c51e2bd0b0e2d8f7` |
| EfficientAT config | `5a487b946d748d48ec2945dae97e51f07bd0e8b106fa6c49c98df9e84a4035e9` |
| Provisional choice | `95dce46b16760b002358b1aec3db8adb9b5df1c1f2033ee70b0b5121c2dea051` |

The [frozen shortlist](../manifests/matchers/shortlist.json) records exact source hashes, feature layer, pooling, channel/resampling/padding, scales, distance, precision/device and tool versions. Features receive samples/rate only. Source names, preset/family labels, conditions and insertion truth never enter computation/ranking; predictions are persisted before the existing scorer joins ground truth. No learned fit or hidden pitch term is used. Refined lists stay empty consistently.

Post-merge checkout verification exposed Git's default newline conversion on one source file. A small follow-up adds `.gitattributes` rules preserving all three captured source byte identities across checkout, with an offline regression against the frozen hashes. This restores usable reuse without changing method/config hashes, predictions, feature arrays, costs or choice; no new inference or allowance reset is involved. Fresh-index checkout reproduces all three frozen hashes, all 31 matcher tests pass in 2.052 seconds, and post-checkout comparison accepts the unchanged choice.

The acoustic baseline combines thirteen cepstral means/stds, five spectral descriptor means/stds, sixteen relative RMS bins and four level/envelope descriptors, with fixed scales and Euclidean distance. EfficientAT uses a 384-dimensional mean of the final convolution before the classifier, cosine distance, 32 kHz native evaluation mel preprocessing, eval/inference mode and one CPU thread. Complete selected content is retained; padding short inputs does not extend source intervals. [MATCHERS.md](../docs/MATCHERS.md) gives exact conventions and recovery behavior.

Primary source evidence: [EfficientAT source at `a425fdc`](https://github.com/fschmid56/EfficientAT/tree/a425fdce92572e602a1d5634799bd9f1f2efa806), [official release v0.0.1](https://github.com/fschmid56/EfficientAT/releases/tag/v0.0.1), [MIT licence](https://github.com/fschmid56/EfficientAT/blob/a425fdce92572e602a1d5634799bd9f1f2efa806/LICENSE), and [native frontend](https://github.com/fschmid56/EfficientAT/blob/a425fdce92572e602a1d5634799bd9f1f2efa806/models/preprocess.py). The official project releases these pretrained models with its repository MIT terms; no alternate per-asset terms were advertised in the inspected release. Copyright/licence are retained with the narrow architecture adaptation. MN04 was selected for its small CPU footprint before scoring; its published AudioSet tagging result is not this project's accuracy. The 4,066,513-byte asset ID 84971629 has captured/pinned checksum `899a8c6217063f6941793102a2780b3dd788ab11fce468d9cf5f0577c453321c`. The release supplies no independent digest; subsequent acquisition/load requires the committed checksum.

[CIR's pinned source](https://github.com/gwendal-lv/CIR/tree/ca551b8df4234e40e3acc84202f8b921854be89c) tree/README lacked an established licence, while `AST.py` also loads a pretrained AST and feature extractor. Its mixture domain is percussion/bass/synth-lead NSynth/Surge; terms and additional loading requirements were not silently assumed. [The official CLAP checkpoint page](https://huggingface.co/lukewys/laion_clap/blob/main/630k-audioset-best.pt) lists 1.86 GB and SHA256 `8053c9775516af2f4902e1e8281e356cc1bf7a85e8b761908170767b77c3f037`, exceeding the 512 MiB project ceiling. No CIR/CLAP weights, training datasets or credentials were fetched.

## Commands actually exercised

From the repository root in PowerShell; commands below are grouped by purpose, not execution order. Ordinary setup remains independent of models. Optional setup uses Windows AMD64/Python 3.12 hash-pinned CPU wheels; all root numerical/decoder versions remain unchanged.

```powershell
.\scripts\setup.ps1 -PythonExecutable "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
.\scripts\setup-models.ps1
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_matchers.py -v
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-freeze.json matchers freeze
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-validate.json matchers validate
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-acquire.json matchers acquire
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-acoustic-smoke.json matchers smoke --method acoustic
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-efficientat-smoke-final.json matchers smoke --method efficientat
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-acoustic-run.json matchers run --method acoustic
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-efficientat-run.json matchers run --method efficientat
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-comparison.json matchers compare
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-acoustic-reuse.json matchers run --method acoustic
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-efficientat-reuse.json matchers run --method efficientat
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-acquire-reuse.json matchers acquire
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-acoustic-score.json matchers score data/runs/matchers/acoustic-predictions.json
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-efficientat-score.json matchers score data/runs/matchers/efficientat-predictions.json
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-known.json matchers known-answer
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a05-offline-smoke.json smoke
git diff --check
```

A fresh checkout needs the corresponding local audio/private A03 registration; public ready metadata is insufficient. All 208 suite assets and their ancestry/truth were independently validated, including held-out integrity without model scores. Actual inference uses 80 development queries, 24 controlled renders and 56 mixtures: **1,368 unique windows and 3,283.2 processed audio seconds per method**. Candidate features are shared across queries. Each unchanged reuse validated all 1,368 features and source audio without new inference, retaining the cold model cost. Complete prediction-file scoring and revised known-answer checks pass. No A03/A04 ledger was opened by these A05 operations.

## Compatibility, measured cost and checks

Windows 11 AMD64/Python 3.12.14, four logical CPU threads, approximately 16 GiB host RAM; GPU unused. NumPy 2.2.6, SciPy 1.15.3, SoundFile 0.13.1/libsndfile 1.2.2 and truststore 0.10.4 are unchanged. Optional Torch is 2.6.0+cpu. No GPU framework, global runtime install or hidden model download is needed.

The first optional wheel resolution exposed that the CPU index does not supply the pinned root setuptools. The bounded repair uses the complete explicit hash-pinned missing dependency closure with `--no-deps`, the ordinary root setup and `pip check`; it does not relax versions. TorchAudio then failed Windows DLL loading before any pretrained ranking. It was removed after a repo-wide usage check; direct evaluation-only Kaldi equations reproduce all **65,664 coefficients exactly**, maximum error zero, from the installed pinned source without importing the extension. Strict official-state load and short/silent/stereo CPU smoke then passed with networking disabled. These are logged compatibility repairs, not score-driven configurations. The initial failed three-case smoke remains charged; twelve total smoke-window attempts are consumed.

| Cost component | Acoustic | EfficientAT |
| --- | ---: | ---: |
| Summed adapter load seconds, 15 bounded workers | 0.000021 | 28.958 |
| Unique cold feature extraction seconds | 13.200 | 21.586 |
| Ranking seconds | 0.016 | 0.043 |
| Selection model wall seconds (sum above) | 13.216 | 50.587 |
| Measured peak worker working set bytes | 170,487,808 | 339,828,736 |
| Conservative array/model reservation bytes | 67,108,864 | 805,306,368 |
| Actual feature array bytes | 481,536 | 2,276,352 |
| Reuse outer wall seconds | 8.766 | 8.797 |

Both methods use the same cold feature state, batches, device and thread policy. Model timing uses high-resolution `perf_counter`; shared startup, validation, publication and orchestration are separate. The acoustic outer run took 365.438 seconds; its early workers repeatedly inventoried unchanged disk files. A narrow switch to the existing locked owned-file accounting reduced subsequent publication overhead, without changing features/methods/rankings or model-cost timing. EfficientAT's outer run time is recorded below. Reuse never turns model cost into zero. Memory numbers are measured peak working-set evidence checked after operations, with separate allocation reservations; they are not a new OS memory sandbox.

Checkpoint acquisition used **two HTTP attempts and 4,066,513 charged/received bytes**, including the GitHub redirect; reuse added zero attempts/bytes. Optional dependency wheels occupy 218,227,265 bytes, including the retained 2.4 MB wheel from the failed TorchAudio attempt; installed environment/cache cost is separate from model transport and included in free-headroom evidence. Runtime imports no TorchAudio. Source/metadata research and dependency installation are separately identified, not presented as metered checkpoint bytes.

Final required checks: ordinary and optional setup/dependency consistency, Ruff lint/format, all **118 regression tests in 54.374 seconds**, and starter offline smoke passed. The suite includes thirty new matcher tests, including the final path/accounting and interrupted-run eligibility guards; the existing 88 tests are unchanged. Tests exercise independent geometry/ranks, deterministic grids/tails, waveform timing, truth isolation, fixed scaling, invalid values/shapes/distances, cache corruption/dependency invalidation, explicit inference failure charges, managed-byte accounting, coordinator failure/recovery, selection ordering, held-out/network refusal and a real small acoustic pipeline. Ordinary tests are offline and require no pretrained import/download. No hosted CI pass is claimed; no hosted CI currently exists.

The [A05 lifetime policy](../config/matchers.json) retains existing 120-second workers, 1 GiB configured working ceiling, concurrency one, 4 GiB managed storage and 4 GiB free headroom. Separate fixed allowances are 8 MiB checkpoint payload, sixteen HTTP attempts, 2,400 worker seconds, four model-run operations, 8,000 processed windows, 64 MiB conservative feature publication allocation and twelve smoke-window attempts. Charges persist before inference/writes; complete reuse counts as a run, and no alternate job name replenishes limits. Non-acquisition A05 workers refuse socket connections. All weights/audio/features/private paths/machine reports remain ignored, with self-hashed public JSON bounded to 1 MiB.

The final preservation audit passed for **396 files / 692,720,678 bytes**: all snapshotted original/prepared/generated/published audio, Loulou manifest and A03/A04 acquisition/construction/raw-published records retain identical SHA256, size and nanosecond mtime. Archived prompts, A03 manifests, A04 asset records, root resource caps, dependency lock and historical reports remain unchanged in Git.

## Development results

The [compact public comparison](../manifests/matchers/comparison.json) retains each condition's counts, all K metrics, ranks, missing targets, conditional boundary error, absent scores, costs and descriptive family counts. Full predictions/scores are private and reproducible through the commands above. Every method supplies 80/80 query outputs, with 72 present queries, eight absent queries and 88 target events. The tables below report successful-query counts separately from recovered events; one top-1 interval cannot recover both events in a two-event query.

### acoustic

| Condition | Queries / targets | Hit queries at 1 / 5 / 10 | Recovered events at 1 / 5 / 10 | First-rank median (missing) | Boundary MAE at 1; matched / missed |
| --- | ---: | --- | --- | --- | --- |
| absent:0 | 8 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | undefined (0) | undefined; 0 / 0 |
| exact_instance:-12 | 8 / 16 | 6 / 6 / 7 | 6 / 7 / 11 | 1.0 (0) | 0.200000s; 6 / 10 |
| exact_instance:0 | 8 / 8 | 4 / 4 / 6 | 4 / 4 / 6 | 5.5 (0) | 0.062500s; 4 / 4 |
| exact_instance:12 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 (0) | 0.000000s; 8 / 0 |
| exact_waveform | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 (0) | 0.000000s; 8 / 0 |
| performance | 8 / 8 | 7 / 8 / 8 | 7 / 8 / 8 | 1.0 (0) | 0.000000s; 7 / 1 |
| pitch | 8 / 8 | 5 / 8 / 8 | 5 / 8 / 8 | 1.0 (0) | 0.000000s; 5 / 3 |
| source_consistency:-12 | 8 / 16 | 5 / 6 / 7 | 5 / 7 / 11 | 1.0 (0) | 0.120000s; 5 / 11 |
| source_consistency:0 | 8 / 8 | 4 / 4 / 5 | 4 / 4 / 5 | 5.5 (0) | 0.125000s; 4 / 4 |
| source_consistency:12 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 (0) | 0.000000s; 8 / 0 |

Conditional mixture localisation at K=1 (signed errors are prediction minus truth):

| Condition | Matched events | Mean start / end error seconds | Mean IoU |
| --- | ---: | --- | ---: |
| exact_instance:-12 | 6 | -0.200000 / -0.200000 | 0.866667 |
| exact_instance:0 | 4 | -0.062500 / -0.062500 | 0.952830 |
| exact_instance:12 | 8 | 0.000000 / 0.000000 | 1.000000 |
| source_consistency:-12 | 5 | -0.120000 / -0.120000 | 0.920000 |
| source_consistency:0 | 4 | -0.125000 / -0.125000 | 0.905660 |
| source_consistency:12 | 8 | 0.000000 / 0.000000 | 1.000000 |

Eight absent-case top distances: `5.096879, 4.626571, 5.071733, 4.688155, 5.422842, 4.629538, 1.907214, 1.890474`. No rejection rule is fitted; false accepts remain undefined. Raw distances across methods are not calibrated probabilities.


### efficientat

| Condition | Queries / targets | Hit queries at 1 / 5 / 10 | Recovered events at 1 / 5 / 10 | First-rank median (missing) | Boundary MAE at 1; matched / missed |
| --- | ---: | --- | --- | --- | --- |
| absent:0 | 8 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | undefined (0) | undefined; 0 / 0 |
| exact_instance:-12 | 8 / 16 | 7 / 8 / 8 | 7 / 13 / 15 | 1.0 (0) | 0.371429s; 7 / 9 |
| exact_instance:0 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 (0) | 0.187500s; 8 / 0 |
| exact_instance:12 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 (0) | 0.375000s; 8 / 0 |
| exact_waveform | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 (0) | 0.000000s; 8 / 0 |
| performance | 8 / 8 | 5 / 8 / 8 | 5 / 8 / 8 | 1.0 (0) | 0.000000s; 5 / 3 |
| pitch | 8 / 8 | 7 / 8 / 8 | 7 / 8 / 8 | 1.0 (0) | 0.000000s; 7 / 1 |
| source_consistency:-12 | 8 / 16 | 8 / 8 / 8 | 8 / 12 / 14 | 1.0 (0) | 0.137500s; 8 / 8 |
| source_consistency:0 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 (0) | 0.250000s; 8 / 0 |
| source_consistency:12 | 8 / 8 | 8 / 8 / 8 | 8 / 8 / 8 | 1.0 (0) | 0.312500s; 8 / 0 |

Conditional mixture localisation at K=1 (signed errors are prediction minus truth):

| Condition | Matched events | Mean start / end error seconds | Mean IoU |
| --- | ---: | --- | ---: |
| exact_instance:-12 | 7 | -0.371429 / -0.371429 | 0.748571 |
| exact_instance:0 | 8 | -0.187500 / -0.187500 | 0.880952 |
| exact_instance:12 | 8 | -0.375000 / -0.375000 | 0.754740 |
| source_consistency:-12 | 8 | -0.137500 / -0.137500 | 0.900000 |
| source_consistency:0 | 8 | -0.250000 / -0.250000 | 0.833783 |
| source_consistency:12 | 8 | -0.312500 / -0.312500 | 0.786613 |

Eight absent-case top distances: `0.657209, 0.635325, 0.750599, 0.682412, 0.689446, 0.707115, 0.616464, 0.557518`. No rejection rule is fitted; false accepts remain undefined. Raw distances across methods are not calibrated probabilities.


### Dependent family coverage

Each used procedural family has six source-consistency queries and eight target events; variants, levels and reused backgrounds are dependent. No independent-window confidence interval/significance claim is made.

| Procedural family | Acoustic hit@1 | EfficientAT hit@1 |
| --- | ---: | ---: |
| procedural:harmonic:0 | 3/6 | 6/6 |
| procedural:pluck:0 | 3/6 | 6/6 |
| procedural:fm:0 | 5/6 | 6/6 |
| procedural:noise:0 | 6/6 | 6/6 |

EfficientAT's outer inference run took 185.562 seconds. At the final audit, managed storage was **936,732,073 bytes**, free disk **355,680,051,200 bytes**, the optional environment **1,549,163,236 bytes**, pip cache **219,390,264 bytes**, and feature arrays plus metadata **10,458,099 bytes**. All **222 public evaluation/matcher JSON records** passed self-hash/size checks; largest **229,967 bytes**.

A05 final accounting: **592.520 worker seconds**, two HTTP attempts, 4,066,513 bytes, no pending reservations; **4/4 run operations, 2,748/8,000 processed windows, 47,234,304/67,108,864 reserved feature bytes, and 12/12 smoke attempts**. The charged windows include twelve smoke attempts, including the failed three-case compatibility attempt; successful feature extraction is 2×1,368. Reuse added no features/inference. Lifetime limits remain consumed; do not reset them to repeat development experiments.


## A06 handoff

[choice.json](../manifests/matchers/choice.json) binds EfficientAT, its exact configuration/checkpoint, both revised input hashes, the shortlist, development results/costs, exclusions and limits. Source-consistency top-1 query hits are 100%, but top-1 recovers only 24/32 events, and top-10 30/32: query hit is not complete multiple-event recall. Successful mixture boundaries can differ by hundreds of milliseconds; no refinement was implemented. Exact-instance and isolated-performance weaknesses remain visible above. The former top-10 selection metric is 83.3333% for acoustic and 100% for EfficientAT and constant controls, illustrating its saturation. Secondary performance/pitch hit@5 is 100% for both methods.

A06 should consume the frozen usable adapter/choice for its distinct finite search/final-check work. It must explicitly initiate the held-out check and preserve all existing ledgers; A05 does not mark its choice A06 or claim final validation. No learned scaling, separation, production index, user interface, new human labels, listening review, paid compute, deployment or private-audio upload was introduced. Unknown pretrained-data overlap, absent-case calibration, human agreement and real-catalogue/Loulou relevance remain unresolved. D04 remains the first required listening review.
