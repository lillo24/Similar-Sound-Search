# A03 — Automated starter catalogue

Implement **A03 only** in https://github.com/lillo24/Similar-Sound-Search. Build and run bounded catalogue acquisition and ingestion, retain real analysable audio locally, and complete the repository's branch/PR/merge workflow. This is an implementation task, not a request for another plan or a downloader that has never been exercised.

## Starting point and scope

Reviewed on 11 October 2026: A02 is merged through PR #3 at `2a14cb0c0065d53149269296b84f0c39acdaf1de`. It provides Python 3.12, a pinned NumPy/SciPy/SoundFile CPU runtime, WAV/FLAC inspection, immutable crop/channel/resample preparation, composed timestamp maps, validated derivative reuse, and numeric resource tiers. Its 32 tests, formatting/static checks, dependency checks, and offline smoke were also rerun successfully in a separate Linux review environment. That review does not replace the documented Windows evidence or establish catalogue/search quality.

Reinspect current `main`, local changes, and applicable instructions before editing. Read `AGENTS.md`, `README.md`, `docs/PROJECT_BRIEF.md`, `docs/RECORDS.md`, `docs/EVALUATION.md`, `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/RUNTIME.md`, `reports/A02_RUNTIME.md`, the source/config maps, and `config/resource_limits.json`. Inspect actual implementations in `cli.py`, `inputs.py`, `preparation.py`, `records.py`, `resources.py`, and `storage.py` before choosing interfaces.

Preserve the adopted direction: selected-event timbre first, approximate pitch second, phrase rhythm deferred. A04 owns retrieval benchmarks and controlled mixtures; A05 owns candidate matchers; A06 owns first search/playable results; C04 owns broader incremental processing. A03 produces a reproducible discovery catalogue ready for those consumers. It does not train models, build a vector index, compare matchers, or claim perceptual relevance.

## External context and inputs

- All required design context is in the repository. Google Doc access is optional. This prompt is archived in `history-implementations/Similar_Sound_Search_A03.md`; preserve the earlier prompts.
- A real acquisition run needs network access to a documented, permitted audio source, or explicitly supplied/authorised local music. Select and collect candidates yourself. Do not ask Leonardo to find similar songs, label examples, or perform a listening review; the first required review remains D04.
- Use the actual machine available to this session. A02 exercised Windows 11, Python 3.12.14, four CPU threads, approximately 16 GiB RAM, and CPU processing. A detected 6 GiB GPU is not evidence of a working GPU pipeline. Keep the CPU route and project-local setup.
- The marked-version **daoud — Loulou & the loulous** audio is still missing: either the full track or the existing approximately **3:38–4:00** excerpt, with any available version/provenance and excerpt-offset evidence. Check supplied attachments and explicit project input locations only. ChatGPT files are not automatically present in a Codex checkout.
- Missing Loulou audio must not block A03. Keep its reference unverified; never infer identity or a verified offset from a title, duration, or filename. An already-short excerpt must not be cropped again at second 218. No Loulou retrieval experiment is expected in A03.

## 1. Select a feasible source and exercise a small pilot

Choose a documented source of actual audio within the existing permissions and budget. Include authorised local audio through the same ingestion path when available. Prefer full recordings or excerpts with documented original offsets, and include a small full-track ingestion exercise where accessible. Unknown-offset excerpts are acceptable when honestly labelled; metadata, provider previews without analysable files, or precomputed embeddings do not constitute an acquired audio catalogue.

Investigate FMA as one candidate, not a mandatory dependency. Its [official repository](https://github.com/mdeff/fma) documents a 342 MiB metadata archive and a 7.2 GiB small audio archive containing 8,000 thirty-second MP3 excerpts. The whole small archive exceeds this project's 512 MiB starter download cap. Dataset metadata and audio have different licence conditions, including track-level audio licences. Do not launch a whole-archive download by default or install its historical example environment.

For another comparison, the [official MTG-Jamendo repository](https://github.com/MTG/mtg-jamendo-dataset) documents MP3 collections distributed in large archives and its permitted-use conditions. Its ordinary bulk downloader is not automatically a fit either. These are research starting points checked while authoring the prompt, not claims that selective audio access works on the implementation machine. Recheck current official source documentation, access, licence evidence, and expected transfer size. Choose a smaller or selectively downloadable alternative if necessary; do not build adapters for several sources merely to generalise the architecture.

If using selective archive access, first prove the server honours the requested range and bound both transferred and extracted bytes. A `200` whole-object response to a range request must not trigger an oversized download. Validate member integrity and record the extent of verification; member CRC/local SHA-256 is not verification of an undownloaded archive's published hash. Direct individual-file access is preferable when it avoids unnecessary complexity.

Run a small pilot, roughly 10–20 distinct recordings or fewer if needed to establish cost. Then target roughly **100–300 distinct real recordings** where access and the existing limits allow. Preserve a varied mix, including electronic/instrumental material, rather than filling the catalogue with one convenient artist or sound family. Use metadata only for deterministic coverage selection, not as timbre labels or a similarity score. Record the source snapshot/version, selection rule, stable ordering/seed, requested count, exclusions, and actual eligible population.

If the target cannot fit, deliver the largest useful validated subset within the limits and state the shortfall and cause. Generated fixtures and duplicate encodings never count toward the real-recording target. If permitted network acquisition is unavailable, finish the tested acquisition path, ingest any authorised local music, and mark the real catalogue portion partial/blocked with exact access evidence. Do not call an empty or synthetic-only catalogue a completed real acquisition.

## 2. Integrate acquisition with the existing bounded runtime

Add one clear catalogue/ingestion responsibility that fits the current package. Share input validation, identity, resource, storage, and preparation behavior where appropriate; avoid a second incompatible audio pipeline. Provide a reproducible CLI command for initial acquisition and resumption, plus explicit local import. A local import must accept only the user's explicit path or project input locations, not scan unrelated personal directories.

The current A02 format allowlist accepts WAV/FLAC and deliberately refuses MP3, OGG, and other lossy formats even if libsndfile advertises them. Resolve this integration boundary explicitly. Either select a genuinely compatible source or add the smallest tested decoder extension needed by the chosen catalogue. Inspect the already-pinned SoundFile/libsndfile capabilities before adding dependencies. Do not silently relabel files, bypass the allowlist, or describe a WAV decoded from MP3 as a lossless original.

When extending decoding, retain original downloaded bytes and their identity. Record decoder/version, source format, decoded sample rate/count/channels, derivative identity, and processing lineage. Preserve original-mixture channels unless a documented explicit derivative policy says otherwise. Establish sample counts and timing behavior on known fixtures, including any priming/padding/delay; do not assume sample-exact compressed seek. A full sequential decode with a cached playback/analysis derivative can be a bounded route, provided its relation to the original available source and any remaining timing uncertainty are explicit. Do not invent full-recording offsets for provider excerpts.

Keep original assets immutable. Validate temporary downloads before atomic publication; quarantine or explicitly reject corrupt, silent, truncated, unsupported, and over-limit files. Use bounded streaming, request/read timeouts, retries/backoff, redirects, and total attempts. Recover completed entries after interruption. Changed remote content, failed validation, and exhausted limits must be visible states, not success-shaped empty manifests.

Reuse must verify local content and relevant metadata/configuration identity. Repeating an unchanged import must not redownload valid originals, duplicate entries, or needlessly regenerate valid derivatives. A changed URL payload, local byte hash, decoder/preparation version, or required provenance must not silently inherit a stale ready state. Keep this focused on acquisition/ingestion; do not introduce a general workflow engine.

## 3. Preserve provenance, identity, and honest timestamps

Extend the current record contracts deliberately and document any schema change with affected consumers/examples updated together. Catalogue identity must distinguish the recording, a particular available asset, and its derivatives. Retain at least:

| Area | Required information |
| --- | --- |
| Identity | Stable catalogue/source recording ID; title, artist, album/version and source IDs when known; explicit unknowns and evidence for associations |
| Acquisition | Provider/source URL, dataset revision or metadata snapshot, acquisition date, permitted-use/licence evidence and any attribution requirements; distinguish audio rights from metadata/code licences |
| Available audio | Original file-byte SHA-256, format, size, duration, decoded rate/channels/sample count, and a versioned canonical decoded-PCM hash with its exact normalization definition |
| Time coordinates | Full-track/excerpt/unknown kind, original-recording offset or null, offset evidence, and mapping through decoding/preparation; unknown-offset results remain available-file/excerpt-relative |
| Lifecycle | Discovered/downloaded/validated/ready or equivalent explicit states, exclusions/quarantine/failures with reasons, and derivative/config/tool identities needed for reuse |
| Data role | Real-recording discovery catalogue, separate from engineering fixtures and future published human-rated evaluation data |
| Duplicate grouping | Canonical recording/family group, related assets and match evidence/confidence; preserve provenance for all retained aliases |

Deduplicate byte-identical copies, equal canonical decoded audio, repeated provider IDs, and other known alternate copies with justified evidence. A decoded-PCM hash can identify matching decoded samples; it does not guarantee detection of lossy re-encodings, edits, or near-duplicates. Keep suspected relationships distinguishable from established identity and report actual duplicate-detection coverage. Do not merge unrelated tracks solely because titles or artists match. Retain groups usable later for query-copy exclusion and leakage control, without inventing A04 splits or A06 discovery results.

Use stable relative asset references in reproducible records and ignored local manifests for private paths/access details. Keep sanitized catalogue metadata under `manifests/catalogue/` and original/derived audio in the existing ignored data locations. Never commit audio, temporary downloads, caches, environments, credentials, signed URLs, or machine-specific personal paths. A manifest may be versioned even when its audio may not be redistributed.

## 4. Enforce the resource policy across the acquisition job

The existing starter profile sets **512 MiB download bytes, 4 GiB managed storage, 4 GiB free-space headroom, concurrency one, and a 120-second worker deadline**. Its per-input, decoded-memory, working-memory, output, duration, and channel/rate caps also apply. The smoke tier has zero download allowance and must remain offline.

Implement the previously configuration-only download limit at the real network boundary. Count metadata, audio/archive payloads, retries, and partial transfers toward a durable cumulative budget for the catalogue acquisition, including resumption. Define the accounting unit explicitly, such as received HTTP payload bytes rather than unmeasurable transport overhead. Check advertised sizes when available and enforce streaming limits when they are absent or wrong. Do not reset the entire allowance per track, per retry, or each time the same job resumes. A post-crash unknown transfer reservation must not silently become free budget again.

Include originals, prepared copies, extracted members, manifests/reports, and abandoned partials in the applicable disk accounting. Check expansion/output estimates and remaining free space before writing. Respect the current per-worker deadline and choose an explicit conservative run-wide time/attempt bound from the pilot; a sequence of workers must not become an unlimited job. If external decoder processes are added, ensure timeout/cancellation terminates them too.

The current directory inventory limit is 64 starter files and its worker deadline is not a 300-track batch guarantee. Process a larger selected catalogue through bounded batches or per-asset operations with durable overall accounting. Likewise, the existing JSON reader caps a document at 1 MiB: use an appropriate bounded manifest layout/parser rather than writing an unreadable aggregate. Preserve lock semantics and completed work across batches without permitting concurrent budget races or nested-lock failures.

Do not raise the existing resource ceilings merely to reach the target count. Smaller validated catalogues and resumable limit stops are valid outcomes. Any necessary contract addition must be documented, finite, and exercised. Defaults remain no paid services, no private-audio uploads, and no public deployment. Measure actual costs rather than assuming the Windows resource report describes this session.

## 5. Verify behavior and run real acquisition

Use small offline fixtures and a deterministic local HTTP test server or equivalent controlled transport for meaningful failure coverage. Tests should assert independent outcomes, not merely compare a manifest with another output from the same function. Cover:

- Deterministic source selection and one shared ingestion path for local and downloaded audio.
- Valid acquisition through decoding/registration; unsupported, corrupt, silent, and interrupted/truncated downloads; explicit status and recovery.
- Missing/misleading length headers, bounded retries/timeouts, cumulative byte and disk limits, and interruption/resumption without resetting the budget. Test range/redirect behavior if used.
- Atomic publication and concurrent-run refusal; incomplete files never accepted as ready; unchanged repeat runs avoid duplicate entries/downloads and detect changed or corrupt cached inputs.
- Original byte identity, canonical PCM identity across suitable alternate encodings, stable duplicate grouping, and retention of source/licence evidence.
- Full-track, known-offset excerpt, and unknown-offset excerpt mapping; preservation of the original source and declared timing behavior for every newly supported format.
- Compatibility with A02 inspection/preparation, unchanged offline smoke, and an unverified/missing Loulou reference.

Run the actual source acquisition/import, not only mocks. Exercise resumption or an unchanged second run against the acquired catalogue, and demonstrate that ready entries resolve to valid local analysable audio and trustworthy metadata. Keep slow/live-provider tests separate from routine offline validation. Retain explicit evidence if a provider or environment prevents the live run; do not fabricate counts or report network success from fixture tests.

Run project-local setup where needed, `pip check`, Ruff checks/format verification, the tests affected by the change, the offline smoke, the delivered catalogue commands, and `git diff --check`. Shared runtime changes require the existing A02 tests as well. No CI currently exists; do not claim a CI pass or add a hosted workflow without a concrete need consistent with `AGENTS.md`.

## Delivery and handoff

Update the nearest source/config maps and relevant runtime/record/decision/status documentation. Provide a sanitized `reports/A03_CATALOGUE.md` or equivalently clear evidence report with exact setup/acquire/import/resume commands for the detected platform, source/access decisions, selection identity, requested versus acquired/ready counts, distinct recordings/artists, total usable duration, full-track/excerpt/unknown-offset coverage, duplicates/quarantines/failures, and measured transfer/storage/time costs. Separate estimates, fixture results, and live-provider results. Include the supported decoder route and limitations.

Follow `AGENTS.md`: one isolated A03 branch/worktree, inspect the intended diff, commit only task files, push, open a PR into `main`, and merge after applicable checks and clean mergeability unless a consequential unresolved issue requires review. Complete prescribed branch/worktree cleanup. Preserve archived prompts, unrelated work, and the unverified Loulou reference unless actual supplied evidence justifies a documented update.

Finish with the PR/merge reference, actual validation results, catalogue counts/source coverage and limits, one runnable catalogue/resume command, and an explicit **complete, partial, or blocked** assessment. Explain any count shortfall and precise missing access/input rather than assigning routine source research to Leonardo. Working ingestion is not measured retrieval quality.

Leave the repository ready for **A04 — Benchmarks and controlled test generation**. Do not implement A04 or request a listening review in this task.
