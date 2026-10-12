# A04 — Benchmarks and controlled test generation

Delivery evidence, 12 October 2026, implementing [A04 from PR #6](https://github.com/lillo24/Similar-Sound-Search/pull/6). Base: `0e8cc1a2812edb2e93fd33c11f14182995839939`; implementation branch: `codex/a04-evaluation`. The implementation PR and merge commit provide the final code revision. Package metadata remains `0.3.0`; the independent evaluation implementation version is `a04-suite-1`.

| Evidence category | State | Delivered evidence and limit |
| --- | --- | --- |
| Harness correctness | Complete | Independent known answers, interval/rank validation, native AIFF decoding, durable limits, deterministic regeneration, corruption/change tests, all 88 offline tests passing. |
| Published human judgments available | Partial; unavailable for scoring | Actual Grey1977 files inspected: 16 native stimuli and 120 supplied matrix observations. Zero eligible pairs because reuse permission and original study-to-row/scale provenance remain unresolved. |
| Controlled ground truth | Complete | 96 procedural renders, 112 mixtures, 160 queries; independently checked audio, insertion truth, source mappings and family splits. |
| Acoustic model quality | Not measured; belongs to A05/A06 | Development oracle/wrong/missing runs exercise the contract. No acoustic matcher, model download, training, winner or held-out model comparison. |
| Real catalogue/reference | Existing limitations retained | A03 remains 72 ready recordings from 35 artists, with its acquisition allowance exhausted. Loulou audio remains missing and its manifest unverified. |

## Reproduction and identity

Use the repository root in PowerShell with Python 3.12. The delivered environment is Windows 11 AMD64, Python 3.12.14, four logical CPUs, 17,118,912,512 bytes total RAM, approximately 8.2 GB available during the final smoke, and an unused GTX 1660 SUPER with 6 GiB VRAM. All processing was CPU-only, with one operation and one numerical thread. The pinned NumPy 2.2.6, SciPy 1.15.3, SoundFile 0.13.1/libsndfile 1.2.2 and truststore 0.10.4 stack is unchanged. Neither FFmpeg nor a GPU framework is required or used.

The frozen [protocol](../manifests/evaluation/protocol.json), schema `a04-protocol-1`, version `2026-10-12.2`, seed `42104`, has self-hash:

```text
b5fd2d1e87040e8a9b929a65a4b3a2d92ae69e99dfab88e3e0c87c28aa70093d
```

The [suite](../manifests/evaluation/suite.json) has self-hash:

```text
59b781f3fbf75a7bad52f49c051e02142528f402cbde1c74041927ef4f081a2a
```

Suite records bind every asset ID to its asset-record hash. Prediction files must bind both hashes. The pre-model pilot/construction protocols are retained in [protocol-history](../manifests/evaluation/protocol-history/); the final revision makes the development selection rule explicit. No acoustic scores informed any revision. Reuse after the final revision verified all 208 unchanged assets.

The following commands were executed successfully. Setup used the actual bundled Python path expressed relative to the user's home; other installations should supply their own Python 3.12 executable.

```powershell
.\scripts\setup.ps1 -PythonExecutable "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-offline-smoke.json smoke
git diff --check
```

Evaluation commands executed on the delivery inputs:

```powershell
# Offline pilot and full construction, followed by unchanged regeneration.
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-pilot.json evaluation generate --pilot
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-generated.json evaluation generate
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-reused.json evaluation generate
# Explicit bounded network acquisition, then verified local reuse.
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-published.json evaluation acquire
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-published-reused.json evaluation acquire
# Final protocol and independent integrity/coordinate checks, including held-out assets.
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-final-regeneration.json evaluation generate
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-final-validate.json evaluation validate --split all
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-maps.json evaluation maps
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-maps-reused.json evaluation maps
# Development-only harness checks, then the ordinary prediction-file scorer.
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-final-known.json evaluation known-answer
.\.venv\Scripts\sound-search.exe --tier starter --report reports/local/a04-final-score.json evaluation score data/runs/evaluation/predictions-development-oracle.json
```

These are exact invocations, grouped by purpose rather than execution order. Raw machine reports, audio, matrices, private registration, environments and caches remain ignored. All 214 public evaluation JSON records passed size/self-hash checks: maximum 189,229 bytes, total 984,423 bytes, each below the 1 MiB reader limit. Public records carry relative paths, source URLs, recipes, hashes and attribution rather than personal paths or raw ratings.

A fresh checkout must restore the four frozen A03 source files, their prepared bundles and matching private ready registrations before using this suite. Public `ready` records alone are insufficient. Missing/changed inputs fail visibly; do not restart the exhausted A03 acquisition job. An independently documented procedural-only protocol would be a separate pre-comparison choice, not a silent substitute for these backgrounds.

## Published human data investigation

The inspected primary sources are [Timbre Dissimilarity Metrics at `262ca43`](https://github.com/ben-hayes/timbre-dissimilarity-metrics/tree/262ca43c2105483eac03c775cd1adba6273a9e6b), its [lexicographic audio loader](https://github.com/ben-hayes/timbre-dissimilarity-metrics/blob/262ca43c2105483eac03c775cd1adba6273a9e6b/timbremetrics/audio.py), and [original musical-timbre-studies at `0a34e76`](https://github.com/EtienneTho/musical-timbre-studies/tree/0a34e76101a192ad0e5945f22193ef9d60c8065a). Git-tree inspection found identical Git blob identities for the selected 16 AIFF files and matrix in both repositories. [The original Grey paper](https://sites.music.columbia.edu/cmc/courses/g6610/fall2019/week3/Grey_1977_Multidimensional_perceptual_scaling_of_musical_timbres.pdf), DOI `10.1121/1.381428`, supplies study context, not a blanket asset licence.

Grey's first experiment concerns overall timbre, with sixteen synthesised versions of instrumental tones near E-flat 4, controlled perceived pitch, loudness and duration. Twenty listeners participated, fifteen repeated, yielding 35 response sets. The original similarity scale was 1–30, with higher values more similar. Those original trials are not established as the supplied matrix: the downloaded file is labelled dissimilarity and contains differently scaled aggregate-looking values. Its precise transformation, participant-level observations and original row key remain unverified.

The adapter's explicit upstream order is:

```text
BN C1 C2 EH FH FL O1 O2 S1 S2 S3 TM TP X1 X2 X3
```

This reproduces the inspected loader contract; it does not independently authenticate the study's original row labels. A directory walk is not accepted as additional mapping evidence. The native files are mono 44.1 kHz PCM16 AIFF, 4.317074829931973 seconds in total. Originals are preserved; no A03 16 kHz/30-second crop is applied. Model-specific preprocessing is deferred to A05 with lineage required.

The 16×16 matrix has 120 observed upper-triangle pairs, 120 distinct nonzero values in `0.163710272727273..0.865176272727273`, no observed ties or genuine zeros, and 136 diagonal/lower-triangle storage zeros. An explicit boolean observation mask excludes those placeholders. Raw supplied values and the mask are preserved privately without filling missing values. Tests separately establish that a genuine observed zero is retained, masked missing values are ignored, conflicting full triangles fail, and duplicate pairs never inflate denominators.

The provisional conservative first-letter source grouping gives eight families: two development families/three sounds and six held-out families/thirteen sounds, with 3 development pairs, 78 held-out pairs and 39 dropped cross-split pairs. Related stimuli reused across studies/conditions are not counted as independent; only Grey1977 is imported. These tiny dependent groups support descriptive reporting, not an independent-cell confidence interval. **All 120 observed pairs are excluded from actual model scoring.**

Both inspected repository trees lacked an asset licence establishing permitted reuse; a code copyright notice in the original project reserves rights rather than granting audio/data permission. The [OSF project](https://osf.io/qu7vc/) did not expose usable file/rights evidence through the available page/API retrieval. The GitHub audio itself was accessible: acquisition succeeded. The unresolved items are permission for audio/data use and the original study-to-row/scale provenance, not a fabricated download failure. The adapter remains quarantined and refuses human predictions. No raw benchmark audio or ratings are published by this change. Enabling this evidence needs source permission/mapping evidence and a deliberate protocol revision before comparisons; A04 does not request new labels from Leonardo.

The upstream [metric implementation](https://github.com/ben-hayes/timbre-dissimilarity-metrics/blob/262ca43c2105483eac03c775cd1adba6273a9e6b/timbremetrics/metrics.py) was inspected rather than installed. Our scorer independently uses average per-observation ranks, with score direction explicit; an `argsort` ordering permutation is not used as ranks. No Torch/TorchMetrics stack was added.

## Controlled inputs and split coverage

Four mechanisms cover harmonic sustained tones, plucked envelopes, FM/inharmonic spectra and filtered noise. Each mechanism has two related-preset families and two variants per family: eight families and sixteen presets. Every preset has the same three phrase orders and two nearby pitch conditions (0/+2 semitones), giving six performances per preset and 96 renders. Seed, engine, parameters, family, preset, phrase and pitch identities are separate. The shared 24 kHz mono, 2.4-second duration and whole-render RMS 0.08 policy avoid simple register/phrase/level cues between identities. Attacks and declared 1.1-second event releases are retained.

| Population | Development | Held-out | Total |
| --- | ---: | ---: | ---: |
| Procedural families | 4 | 4 | 8 |
| Presets | 8 | 8 | 16 |
| Rendered performances | 48 | 48 | 96 |
| Mixtures, 8 seconds each | 56 | 56 | 112 |
| Generated audio assets | 104 | 104 | 208 |
| Queries | 80 | 80 | 160 |
| Target-present queries | 72 | 72 | 144 |
| Target-absent queries | 8 | 8 | 16 |
| Target intervals, including multiple-event cases | 88 | 88 | 176 |
| Used real accompaniment families | 2 | 2 | 4 |

Each preset has three controlled-render queries (exact waveform, different performance, nearby pitch) and seven mixture queries (exact insertion/source consistency at -12/0/+12 dB, plus one absent case). Same-preset truth is a source-identity proxy; altered pitch/performance and contrasting preset IDs are not human similarity/dissimilarity judgments.

There are 80 mixtures with catalogue accompaniment and 32 with procedural accompaniment. A03's established duplicate groups and provider-artist links union its 72 ready entries into 35 families before deterministic split assignment. Each procedural mechanism contributes one family to each split, and all performances/crops/accompaniments retain their parents' partition. Checks found no used family, known byte identity or canonical PCM identity crossing roles/partitions. This tests new preset families within known engines, not unseen synthesis engines. Unknown lossy edits and future pretraining overlap remain unknown.

Four real sources were fully sequentially decoded, checked against public/private byte/PCM/native metadata and prepared hashes, then consumed read-only. The mixture excerpt is seconds 2..10 of each centred 30-second A03 derivative, arithmetic channel mean, polyphase resampled 16→24 kHz. The corresponding original decoded-file intervals are:

| Split | Artist — track | Original file seconds | Rights evidence |
| --- | --- | --- | --- |
| Development | Deadly Combo — Burns (Featuring Cable) | 65..73 | [BSMX0152](https://archive.org/metadata/BSMX0152) |
| Development | C-Doc — Vintage featuring The Honorable Sleaze | 76..84 | [BSOG0054](https://archive.org/metadata/BSOG0054) |
| Held-out | Donnie Ozone — Christmas Shopping at the Dollar Store | 29..37 | [BS450034](https://archive.org/metadata/BS450034) |
| Held-out | Jeannine Lyons — Autopsy (While Doin' Dishes) | 38..46 | [BSOG0044](https://archive.org/metadata/BSOG0044) |

All four carry the existing [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/) evidence, source attribution and local noncommercial research restriction. Full attributions/URLs and original hashes remain in the linked catalogue records and each generated mixture's ancestry. This change does not publish their audio. These intervals refer to the decoded available files; external-master offsets remain null. A thirty-second derivative is not represented as full-track coverage.

Exact-instance mixtures insert the query itself; source-consistency mixtures insert a different phrase at the nearby pitch. Ratios use target/background RMS over the union of full active target-render intervals, including releases. Positions include 0 and 5.6 seconds in two-event cases, 0.75 seconds, and 3 seconds; targets touch both mixture boundaries. Saved gains and a common peak-limiting scale preserve achieved ratios while keeping peak <=0.9. Designated-target absence means absence by construction, not absence of every perceptually similar sound.

Independent validation reconstructs target/background stems and gains without calling the mixture renderer, compares exact emitted float32 samples, checks achieved ratio within `1e-5` dB, and validates target bounds/ancestry. Real-source boundaries use sequential decoding, never arbitrary MP3 seeks. Actual composed 24→16→24 kHz A02 crops map final derivative second 0.2 to available-file second 0.6000000000000001; verified full-file offset zero gives the same recording time, a known excerpt offset 10 gives 10.6, and unknown excerpt offset stays null. The three mapping cases reused their six completed bundles on repeat.

## Scoring and observed harness answers

The [prediction contract](../docs/RECORDS.md#a04-evaluation-records) records protocol/suite/run/method/config identity, split, score direction, decoded-file integer intervals, separate candidate/refined stages and measured model cost with an explicitly labelled working-memory estimate. IDs, bounds, finite numbers, hashes, complete stage fields and duplicates are validated. Missing query outputs remain misses in the full expected denominator.

K is frozen at 1/5/10; score ties use asset/start/end order. Identical intervals with equal scores collapse before K; conflicting duplicates fail; K beyond the list uses all unique entries. Exact asset plus IoU >=0.5 is the temporal matching convention. Maximum-cardinality, then IoU, one-to-one matching prevents a broad/overlapping prediction from recovering multiple targets. Candidate/refined metrics use their own lists, and refined intervals must lie inside a supplied candidate. Query hit rate and multi-event target coverage are separate. Localisation errors/IoU are conditional on successful matches and retain missed-target counts. These are designated-file interval shortlists, not demonstrated retrieval across an arbitrary song catalogue.

Signed rank checks returned perfect `+1`, reversed `-1`, average-rank ties `+1`, and constant-score correlation `null` with a reason and three-pair denominator. Tests include an independent tied-rank `0.5` answer and nontrivial permutations where argsort differs from per-item ranks. Human scoring remains unavailable; there is no pooled perceptual metric or fitted calibration.

| Development harness prediction | Expected queries | Provided queries | Target intervals recovered at K=10 |
| --- | ---: | ---: | ---: |
| Oracle | 80 | 80 | 88 / 88 |
| Deliberately wrong predictions | 80 | 80 | 0 / 88 |
| Missing output | 80 | 0 | 0 / 88 |

The ordinary file-scoring command also accepted the final oracle under the final suite/protocol hashes. Absent cases report score/rank distributions; no development-fitted rejection rule exists, so false accepts are undefined. These results establish harness correctness only. No acoustic method's ranking, perceptual quality or Loulou retrieval was measured.

The frozen A05 selection rule requires technical/resource compliance and all query outputs for at most three candidates, then maximises macro candidate query hit@10 across the three source-consistency mixture levels; the secondary criterion is macro controlled performance/pitch hit@5. Ties use measured model wall time, then lexical method/config hash. Exact-instance diagnostics do not choose a winner; no eligible run means no selection. No universal accuracy threshold is invented. Held-out matcher scoring requires an explicit A06 final-choice file matching the development-selected protocol/method/config. A04 validates held-out construction/integrity only. Later tuning from held-out results must disclose contamination.

## Measured cost, limits and checks

| Operation | Outer command wall seconds | Additional evidence |
| --- | ---: | --- |
| Pilot | 13.046 | 5.813 construction seconds; 12 assets, 6 queries; 28.8 audio seconds; 2,765,496 WAV bytes. |
| Published acquisition | 10.843 | 17 individual GET attempts, 384,189 received/charged bytes; sixteen stimuli plus matrix. |
| Full suite construction | 62.125 | 59.968 construction seconds; 208 assets, 160 queries; reused the 12 pilot assets. |
| Unchanged regeneration | 7.282 | 4.953 construction seconds; all 208 reused; no additional construction allocation or HTTP. |
| Final protocol regeneration | 7.484 | 5.125 construction seconds; all 208 reused. |
| Final independent validation, both splits | 8.984 | 104 assets per split, six used families per split, plus sixteen native published files checked. |
| Mapping checks / repeat | 3.766 / 3.750 | All three coordinate cases pass; repeat reuses bundles. |
| Final known-answer command | 2.593 | Development-only oracle, wrong and missing-output answers. |
| Ordinary oracle file scoring | 3.281 | 80 of 80 expected query outputs. |
| Published acquisition repeat | 2.375 | Verified local assets; zero additional GET attempts/bytes. |
| Starter offline smoke | 3.359 | Existing engineering diagnostic passes; no network/model work. |

The 208 final WAV files total **108,146,464 bytes** and **1,126.4 audio seconds**. At the final audit, managed storage was **700,397,491 bytes**, with **358,526,898,176 free bytes**. The largest real-source inspection working estimate was **286,817,792 bytes**; the generator's largest fixed working reservation was **45,842,432 bytes** (`192000*64 + 32 MiB`). These are allocation estimates, not measured OS peak RSS. Setup/build time and dependency downloads are separate from evaluation. Model-cost fields in hand/oracle predictions do not represent a measured acoustic model.

The existing starter per-input/worker ceilings remain unchanged: 256 MiB input/decoded, 900 seconds/input, 8 channels, 192 kHz, 1 GiB estimated working allocation, 120-second hard worker deadline, concurrency one, 4 GiB managed storage and 4 GiB free headroom. [A04 policy](../config/evaluation.json) additionally bounds its fixed separate lifetime job to 16 MiB download payload, 64 HTTP attempts, 2,400 charged worker seconds, 128 MiB conservative generated bytes, 1,600 audio seconds and 512 construction attempts. Retries/redirects/timeouts remain finite; shared TLS verification is preserved and only the exact pinned raw-GitHub path is added. Catalogue defaults remain Archive-only.

Final A04 accounting was **17 attempts, 384,189 received/charged bytes, 128.687 charged worker seconds**, no pending reservations. Construction accounting was **112,132,096 reserved bytes, 1,142.4 audio seconds and 210 attempts**: 208 assets plus two conservatively charged mapping-command attempts, each reserving six bundles/8 seconds even on reuse. Actual WAV size is reported separately from those pre-write reservations. Reuse never resets lifetime limits; crashes retain uncertain charges. Repeat the same command to resume completed artifacts; missing/corrupt or orphaned owned files fail visibly and require explicit inspection/removal of that artifact, not ledger deletion or increased caps.

Setup/editable packaging and dependency consistency passed. The final complete unittest run passed **88 tests in 54.384 seconds**, including all 58 existing A02/A03 tests and 30 new evaluation tests. Ruff lint/format and whitespace checks passed. New tests include hand-built AIFF sample answers, encoding/container refusals, mask/rank edge cases, changed recipes/tool identities/corruption, durable limit/recovery behavior, independent mixture reconstruction, role/split leakage, candidate omissions/duplicates/overlap/boundaries, absent/missing outputs, and a full procedural suite in an isolated temporary root. Routine tests are offline; real network acquisition and delivered benchmark runs are explicit commands. No hosted CI workflow exists and no hosted CI pass is claimed.

A before/after SHA-256, size and nanosecond-mtime comparison passed for **146 preserved files**: all 72 A03 originals, their 72 prepared audio files, the exhausted A03 ledger and the Loulou manifest. Their total 574,244,501 bytes were unchanged. No catalogue job was restarted/replaced, no caps increased and no reference substitute introduced. The read-only consumer additionally validates the four consumed sources and matching private registration. Public A03 manifests, archived prompts, resource caps and dependency pins are unchanged in Git.

## Handoff

A05 can implement and compare genuine candidate matchers against the development prediction contract and frozen selection rule. Restore the frozen inputs before reuse, retain all existing allowances, and measure model cost separately from scorer cost. Reserve held-out model results for A06 after development choices are frozen. Published perceptual agreement remains blocked on permission/original mapping evidence; Loulou-specific validation remains blocked on the actual marked-version audio and provenance/offset evidence. These external gaps do not block the delivered controlled harness. D04 remains the first required listening review.
