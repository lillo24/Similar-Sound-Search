# A04 — Benchmarks and controlled test generation

Implement **A04 only** in https://github.com/lillo24/Similar-Sound-Search. Deliver and exercise a reproducible evaluation suite: published human-rating data where usable, deterministic sound/mixture fixtures, verified scorers, and a frozen protocol for A05 development and the A06 held-out check. Complete the repository's branch/PR/merge workflow. This is an implementation task, not a request for another plan.

## Starting point and scope

Reviewed on 12 October 2026: A03 is merged through PR #5 at `40a8284a4a18fd1f777b66c146e066156e877f4f`. Its acquisition/ingestion implementation is delivered; the real catalogue remains **partial**. Versioned evidence records 72 distinct blocSonic recordings from 35 artists: 70 provider full tracks, two excerpts, 11,152.101 seconds of original audio, and 2,160 seconds of prepared analysis. Selection contains 106 entries for 120 requested; 34 selected entries remain not ready. The 2,400-second acquisition allowance is exhausted.

The authoring review independently passed all 58 offline tests, Ruff lint/format, pinned setup/dependency checks, and starter offline smoke on Linux. All 183 public catalogue JSON files passed size/self-hash checks, and their ready-record counts agree with the report. The downloaded audio and private registration were not present in that review checkout; its 72-asset audio validation remains the delivery-machine evidence documented in `reports/A03_CATALOGUE.md`.

Reinspect current `main`, local changes and `AGENTS.md` before editing. Read the project brief, evaluation/record contracts, decisions, status, runtime/catalogue documentation, A03 report, source/config maps, and actual source. Inspect `config/resource_limits.json`, `config/catalogue.json`, `inputs.py`, `preparation.py`, `records.py`, `resources.py`, `storage.py`, `cli.py`, and the catalogue subsystem before selecting interfaces.

Keep timbre first, approximate pitch second, and phrase rhythm deferred. A04 establishes trustworthy tests and evaluation inputs. A05 owns acoustic/pretrained matcher implementation and comparison; A06 owns the first search and final baseline check. Do not train/download models, select a winner, build a production retrieval index, add separation, or implement the user interface in A04. A small model-independent prediction contract and known-answer scoring fixtures are in scope.

## External context, local assets and resource boundaries

- All required design context is in the repository. No Google Doc, new user labels, similar-song suggestions, or listening review is required. The first required listening review remains D04.
- Published perceptual evaluation needs actual accessible audio **and** its original human judgments, source/version mapping and usable rights information. Select and inspect suitable sources yourself; record access failures precisely and complete independent work. Generated examples must never be relabelled human-rated.
- Check the implementation machine's explicit project inputs for the existing 72 originals, prepared bundles and private records. Public `state: ready` metadata alone does not establish local availability in a new checkout. Verify the assets used by A04 within bounded local operations; missing/changed files must remain visible.
- Do not rerun the exhausted `starter` acquisition as a prerequisite, erase/replenish its ledger, increase its caps, or create a replacement catalogue job to evade the stop. Its `catalogue verify` also consumes that exhausted job allowance. Reuse existing low-level validation through an appropriate bounded, read-only A04 consumer; any necessary small shared helper belongs with its current owner. A04 processing existing files is distinct from acquiring more catalogue tracks.
- The catalogue's derivatives cover only a centred thirty-second region at 16 kHz per recording. Full originals remain available on the delivery machine. Declare which available intervals are used; never imply that the derivatives cover entire tracks. Keep original audio unchanged and preserve mappings to sequentially decoded source-file time. External-master offsets remain unknown even for provider-labelled full tracks.
- The marked-version **daoud — Loulou & the loulous** audio is still missing: full track or existing approximately **3:38–4:00** excerpt, with available version/provenance and offset evidence. Keep its manifest unverified. Missing audio does not block A04; do not crop a short excerpt at second 218 or claim a substitute validates Loulou.
- Use the actual available machine, retaining Python 3.12 and the pinned CPU-capable stack unless a justified small change is necessary. Keep existing per-worker/input/memory ceilings, concurrency one, 4 GiB managed storage and 4 GiB free-space headroom. Define conservative finite A04 download, generation, attempt and run-time allowances, with durable accounting and measured costs separate from A03. No paid services, private-audio upload or public deployment.
- Use `--tier starter smoke` on the populated delivery checkout: its existing managed footprint exceeds the default smoke tier's 256 MiB disk cap. The diagnostic remains offline. Keep network-dependent benchmark acquisition separate from ordinary offline tests.

## 1. Import and validate published human timbre judgments

Start with [Timbre Dissimilarity Metrics](https://github.com/ben-hayes/timbre-dissimilarity-metrics) and its cited [original musical-timbre-studies data](https://github.com/EtienneTho/musical-timbre-studies). Inspect original study documentation and source code/data rather than assuming package names establish metric semantics. Select a small useful set whose audio/rating alignment and usage conditions can be established. Record the original study, immutable source revision, file hashes, acquisition route, actual availability, attribution and any unresolved restrictions. Public repository access is not a blanket licence for every included recording or code file.

Concrete integration facts found during prompt review:

- The metrics repository at `262ca43c2105483eac03c775cd1adba6273a9e6b` includes AIFF stimuli and dissimilarity matrices. For example, its Grey1977 matrix stores observations in the upper triangle, with zeros below it. Those storage zeros must not become extra human judgments.
- Its loader orders AIFF filenames lexicographically; establish and retain the explicit study stimulus-to-row mapping instead of assuming any directory listing is sufficient evidence. Related studies/conditions reuse stimuli, so dataset names alone are not independent groups.
- A03 supports WAV/FLAC/MP3; it still rejects AIFF. Add the smallest bounded, tested AIFF decoding/import path needed for selected stimuli, preserving original bytes and explicit derivative lineage. Do not rename an AIFF extension or bypass shared input/resource validation. Prefer the already-pinned decoder where it supports the required encoding.
- The upstream package uses TorchMetrics and older loading helpers. Installing its full stack is not necessary merely to read matrices/audio or compute rank correlation with the existing NumPy/SciPy environment. Validate any reused algorithm independently, including tied ranks; an ordering permutation is not itself a vector of per-observation ranks.

Inspect each dataset's rating direction/scale, triangle or full-matrix convention, diagonal, ties, genuine zeros, missing observations, duplicate pairs, number of listeners when available, audio order, pitch/level/duration controls, and whether the task measures overall timbre or a narrower attribute such as brightness. Preserve raw ratings and explicit valid-pair masks. Do not fill unknown ratings with zero, average incompatible triangles silently, combine duplicate observations as independent evidence, or label a brightness-only task general timbre similarity.

Implement a small versioned adapter with stable stimulus IDs, verified audio-to-rating mapping, source-family relationships, native sample metadata, and reproducible preprocessing references. Give published stimuli an explicit human-rated evaluation role: catalogue import currently permits discovery or engineering, so extend the appropriate record boundary deliberately or use an evaluation adapter sharing the underlying audio tooling. Keep originals at native quality; do not automatically apply A03's 16 kHz thirty-second catalogue crop to perceptual stimuli. Model-specific preparation belongs to A05 and must retain lineage.

Download and validate selected usable assets in a real bounded run. Prefer individual pinned files to a large repository/history/archive download. The existing acquisition transport restricts hosts to Archive: extend or share transport responsibilities deliberately with explicit trusted source rules, without weakening the catalogue's existing checks or duplicating an incompatible downloader. Preserve verified TLS, transfer caps, checksums, atomic publication and resumption. If alignment, access or permitted use cannot be established after reasonable source investigation, mark that dataset unavailable for scoring, explain why, and continue the controlled suite. Do not request fresh annotations from Leonardo.

## 2. Generate deterministic, varied sound fixtures

Use an available lightweight synthesizer with reproducible presets, or a sufficiently varied procedural renderer fitting the existing NumPy/SciPy stack. Avoid a heavy plugin host or sound-bank download when a procedural route suffices. Cover several distinct mechanisms/textures, such as harmonic sustained tones, plucked/percussive envelopes, FM/inharmonic spectra and filtered noise; a collection of differently pitched sine waves is inadequate.

Represent engine, preset/parameter identity, related-preset family, performance/phrase, pitch, random seed and transformation lineage separately. Produce multiple performances/phrases and nearby pitches for each selected identity. Balance pitch and phrase conditions across identities so a method cannot solve the suite through note sequence, register, duration, level or a file-name convention alone. Include contrasting timbres playing the same notes and a separately reported exact-waveform diagnostic.

Preserve full event attacks, decays and relevant tails. Retain event sample intervals from construction, a declared amplitude/level policy, sample rate/channels, renderer/config versions, parameters/seeds, byte/PCM hashes and valid time mappings. Check finite/non-silent samples and clipping. Choose counts and durations from a small measured pilot, with enough independent families for meaningful development/held-out partitions; report actual diversity and limitations rather than generating a large factorial explosion.

Same preset across different performances is **known source identity**, a controlled proxy rather than human proof of equal perceived timbre. EQ, noise, effects, dynamics and pitch changes can alter timbre. Record their conditions without automatically declaring all transformed sounds perceptually identical positives. This stage tests source consistency and sound character under declared conditions, not melody or rhythm matching.

Make unchanged regeneration deterministic in the declared environment. Reuse only after validating recipe/tool/input identity and output integrity; changed recipes must invalidate affected fixtures. Reuse the project's deterministic audio-writing and atomic-storage patterns. Keep generated audio in ignored engineering/evaluation locations, never in the real discovery population.

## 3. Construct mixture tests with independent ground truth

Create target-present mixtures with known event sample positions, varied placement, multiple accompaniments and several declared target-to-background levels. Include acoustically challenging distractors and target-absent cases. Available validated catalogue excerpts may supply accompaniment, alongside generated backgrounds; record a missing-real-background limitation if only procedural material is local.

Distinguish two tasks:

1. **Exact-instance recovery:** the query waveform is inserted into a mixture. This is a useful identity/localisation diagnostic.
2. **Source-consistency retrieval:** the query and inserted target are separate performances of the same preset/source, with phrase/pitch conditions recorded. This is harder and remains a source-identity proxy.

Absent-target means the designated source/event is absent by construction; it does not prove that no other sound could be perceived as similar. Do not count known unrelated preset IDs as human dissimilarity judgments.

Define how target-to-background ratio is measured over the active target interval, not over unrelated silence in a long file. Save target/background gains, requested and achieved levels, mixing parameters and any final common scaling. Preserve the intended ratio while preventing clipping. Ground truth must come from generation/insertion parameters, never from the matcher being evaluated.

Record all target intervals, asset/source IDs, transformations, accompaniment parents and offsets in an inspectable manifest. Cover crops, resampling, boundaries, multiple events where supported, and known/unknown original offsets. Map through the existing file/excerpt coordinate contracts; arbitrary MP3 random seek remains unverified, so use full sequential decoding and source-file slicing when consuming MP3 backgrounds. Verify the emitted audio and event bounds independently of the manifest writer.

## 4. Freeze family-aware splits before model comparisons

Assign source families to development or held-out **before** constructing mixtures and transformations. Keep every crop, re-encoding, onset/remainder variant, related preset, rendered performance and known duplicate of a source in the same partition. No target or accompaniment source family may cross partitions through another role. Use A03 groups plus relevant source/artist/recording evidence; disclose its known limits for unknown lossy copies. Do not split rendered files randomly and then call their parents independent.

For human judgments, keep comparisons only when both endpoints satisfy the split policy. Retain counts of dropped cross-split pairs and the resulting sound/family/pair coverage. Check reused stimuli across datasets and conditions. Prefer suitable official splits when available; a random pair split sharing the same stimuli is insufficient. Tiny remaining groups may require a narrower or explicitly descriptive evaluation rather than invented statistical power.

Freeze a versioned, hashed protocol under `manifests/evaluation/` containing dataset revisions, selected IDs, family links, split assignments/seed, generator recipes, pitch/mix conditions, metrics and direction, shortlist K values, candidate/interval matching rules, tie handling, aggregation, uncertainty procedure, preprocessing constraints, resource limits and the development-only selection rule A05 must use. Base technical tolerances on sample rounding/decoder behavior and choices such as K on the intended shortlist and budget. Do not invent a universal timbre-accuracy threshold.

Reserve final held-out **model scores** for the agreed A06 check after A05 choices are frozen. A04 may validate held-out asset integrity, construction truth and split membership; that is not permission to run and tune candidate matchers on it. Make split selection explicit in commands and default development runs appropriately. If later tuning uses held-out results, record the contamination instead of preserving a false final-test claim. Unknown overlap with future pretrained training data remains unknown.

## 5. Implement scorers and their model-independent input contract

Define the smallest structured prediction format A05 can emit: protocol/run/method/config identity, query and candidate asset IDs, scored intervals with coordinate basis, score direction, deterministic order/tie behavior, stage (candidate or refined), split and measured cost. Validate IDs, finite scores, bounds and completeness. Missing queries/predictions remain visible in denominators; stale, mismatched or malformed results must fail explicitly.

| Question | Required reporting behavior |
| --- | --- |
| Agreement with human dissimilarity | Signed rank correlation on valid unique non-diagonal pairs within each dataset/condition, with correct score direction and ties; sound/source-group-aware uncertainty where supportable |
| Controlled source consistency | Query-to-known-source ranks and retrieval at frozen K values, separately by exact-instance, performance, pitch and contrast condition |
| Known targets in mixtures | Candidate hit/target coverage at K before refinement, with explicit query/target denominators and the frozen asset-plus-temporal matching rule |
| Localisation | Boundary errors and overlap in source-file coordinates, with missed-target counts alongside conditional errors for successful matches |
| Absent-target behavior | Separate score/rank distributions and false accepts only under a declared development-fitted rejection rule; a forced top-K list does not establish presence |
| Cost | Measured wall time, processed audio/durations, storage and available memory evidence, separating estimates from measurements and setup from scoring |

Distinguish a single-target query hit rate from recall of multiple target events. Do not count several overlapping hits as several recovered targets, or permit one broad interval to satisfy every event. Define how duplicate candidates and K larger than the available list are handled. Candidate and refined metrics must consume their respective lists; a reranker cannot recover an omitted candidate.

Do not pool incompatible human-rating scales or all dataset pairs into one unqualified score. Report each dataset first, then only a predeclared justified aggregate. Pairwise ratings sharing sounds are dependent: uncertainty/permutation methods must respect source grouping rather than treating every matrix cell as an independent sample. Report undefined correlation for constant/insufficient data with a reason and denominator, not a numeric pass. Any optional calibrated distance/error score must fit calibration on development data only.

Verify scorers with tiny independent known answers: perfect and reversed rankings give signed correlations +1 and -1; tied ranks behave as specified; diagonal/triangle placeholders and missing judgments do not enter denominators; all-equal scores are handled explicitly. Include ranks where an `argsort` permutation differs from per-item ranks, rather than testing only already-sorted vectors. Test candidate-prefix omissions, duplicate/overlapping hits, wrong-asset predictions, interval boundary/offset errors, absent targets, missing outputs and invalid numerical values.

Exercise the end-to-end scoring contract using clearly labelled hand-constructed, oracle and deliberately incorrect predictions as appropriate. Those runs verify the harness. They are not matcher performance, perceptual validation or measured Loulou retrieval. A05 will provide genuine model predictions.

## 6. Run, document and deliver the suite

Provide clear commands to acquire/validate benchmark data, generate or resume fixtures, validate manifests/splits, and score a prediction file. Fit them into the existing CLI and module responsibilities. Respect the 1 MiB JSON reader contract through bounded/sharded records where necessary. Track finite A04 work and completed artifacts across interruptions, include new evaluation files in managed disk accounting, and fail with actionable recovery information when a limit is reached.

Execute actual generation, independent audio/interval checks, deterministic regeneration/reuse, deliberate corruption/change invalidation, split-leakage checks, and the known-answer scoring command. Exercise the selected published dataset adapter against real downloaded audio/ratings when usable; record an explicit partial state otherwise. Check that acquisition state and immutable catalogue originals are unaffected by A04 consumption.

Run project setup if needed, `pip check`, Ruff lint/format, change-complete tests, starter offline smoke and delivered evaluation commands. Shared decoding/resource/record/CLI changes require the existing 58 tests as well. Keep routine tests offline and small; network downloads, full benchmark runs and future model comparisons must be explicit. No hosted CI currently exists, and no CI pass should be claimed.

Update relevant source/config maps, contracts, decisions and status. Add a sanitized `reports/A04_BENCHMARKS.md` or equivalent with exact commands, protocol/version/hash, actual human datasets/sounds/usable pairs, generated families/performances/mixtures, split coverage/exclusions, checks executed, measured costs, blocked evidence and limits. Separate **harness correctness**, **published human judgments available**, **controlled ground truth**, and **model quality not yet measured**. Keep audio, environments, caches, private paths and raw machine reports ignored; preserve attribution and reproducibility metadata appropriately.

Follow `AGENTS.md`: use one isolated A04 branch/worktree, inspect the intended diff, commit task files, push, open a PR into `main`, verify current base/head and checks/mergeability, merge unless a consequential unresolved issue requires review, and complete branch/worktree cleanup. Preserve archived prompts and unrelated work. Do not leave delivery local-only or relabel A03's partial catalogue complete.

Finish with the PR/merge reference, exact validation results, asset/fixture/split counts, a runnable evaluation smoke command, and complete/partial/blocked status by evidence category. State precise missing external access if any. Leave the repository ready for **A05 — Candidate matchers and comparison harness**, without implementing it or requesting a listening review.
