# A06 — First complete local search baseline

Implement **A06 only** in https://github.com/lillo24/Similar-Sound-Search. Connect the existing catalogue and selected representation into bounded exact passage search, query handling, truthful original-audio playback and a minimal local listening report. Run the agreed held-out check once with the frozen A05 choice. Deliver and exercise real commands, then complete the repository's branch/PR/merge workflow. This is an implementation task, not another planning exercise.

## Starting point and evidence

Reviewed on 13 October 2026: A05 merged through PR #9, `5a0af5c228a809a4d947f9c5cbb82d6cdb2475f9`; PR #10, `0a461ddeedb6abc03c8e358083972740efa17910`, preserves its source-byte identities across checkout. Current `main` at authoring includes both. Reinspect current instructions, changes and implementation before editing.

EfficientAT MN04 is the provisional default: **24/24 source-consistency query hits at rank one**, acoustic 17/24, constant control 16/24, seeded random 9/24. Both genuine methods completed all 80 development queries. EfficientAT recovered **24/32 target events at rank one**, and 30/32 at rank ten; successful boundaries can differ by hundreds of milliseconds. These results establish controlled-source behavior, not human timbre agreement, cross-song retrieval or accurate isolation of every event. Refinement remains unimplemented.

The authoring review independently passed all **119 current offline tests**, Ruff lint/format, pinned core setup/dependency consistency, starter offline smoke and matcher known answers on Linux/Python 3.12.14. All 222 public evaluation/matcher JSON records passed self-hash checks; the current source/configuration exactly matches the frozen choice. The review lacked local catalogue/evaluation audio and model weights, so it did not repeat pretrained inference. Windows inference and native-frontend evidence remain in `reports/A05_MATCHERS.md`.

Read `AGENTS.md`, the project brief, decisions/status, runtime/catalogue/evaluation/record/matcher contracts, A03–A05 reports, source/config maps, resource policies and actual source. Keep timbre first, approximate pitch separately inspectable, and phrase order/rhythm deferred. A06 is a small working baseline. Advanced event selection/separation and reusable query design belong to Set B; sophisticated retrieval/refinement/incremental indexing to Set C; the full interface/package/listening review to Set D. Do not train, expand the model shortlist or implement those later stages here.

## External inputs, preservation and accounting

- Design context is already in the repository. No external design document, new labels, similar-song suggestions or user listening approval is required. D04 remains the first required listening review.
- Reuse the delivery machine's actual 72 ready recordings, matching private registrations, A04 suite, selected checkpoint and optional CPU environment. Validate availability and identity; public `ready` metadata alone is insufficient. A fresh checkout does not contain ignored runtime assets. Use explicit project input locations and supported restoration paths, preserving originals and records.
- A03 remains partial: 70 provider full tracks and two excerpts, 35 artists, 11,152.101 seconds of available original audio. Existing A02 analysis derivatives cover only thirty seconds per recording at 16 kHz: 2,160 seconds total. Searching those derivatives alone is **partial time coverage**, not full-track search. Master-recording offsets remain unknown unless supported by evidence, including for provider-labelled full tracks.
- Loulou remains missing/unverified: **daoud — Loulou & the loulous**, the marked-version full track or existing approximately **3:38–4:00** excerpt, with available provenance/version and offset evidence. Missing audio does not block A06's other work. Never crop a short excerpt at second 218 or claim a substitute validates that reference.
- Preserve A03/A04/A05 ledgers, checkpoints, original audio, frozen reports and manifests. A05 has consumed **4/4 run operations and 12/12 smoke attempts**. Do not call `matchers run`/`smoke` as a prerequisite, reset those counters, increase prior allowances or move old development experiments into a new job. A06's distinct indexing, query and final-check work needs its own finite accounting.
- Keep CPU/Python 3.12 and the captured numerical/decoder/Torch versions. Preserve `.gitattributes` and the frozen bytes of `acoustic.py`, `efficientat.py`, and `efficientat_model.py`. An unrelated package-version/EOL change can invalidate A04/A05 identities; avoid it. Optional model setup is currently exercised on Windows AMD64; do not claim Linux pretrained compatibility from core tests.
- Retain existing starter ceilings: concurrency/numerical threads one, 120-second compute workers, 1 GiB configured working ceiling, 256 MiB input/decoded/output ceilings, 4 GiB managed storage and 4 GiB free-space headroom. Preflight combined decoded audio, model, arrays and temporary output, and measure worker memory. Reuse local weights without network. If restoration genuinely requires acquisition, scope it to the same pinned artifact through explicit bounded transport; no hidden downloads, new catalogue collection, paid compute, uploads or deployment.
- Before long work, choose and commit conservative numeric A06 aggregate caps for worker time, indexed windows/audio, query jobs, final-check attempts, generated clips/features and any transfer. Reserve budget for the held-out run and playable demonstration. Include new managed paths in disk accounting. Retries/resumption must retain charges; job names cannot mint new allowances. Separate installation, inference, indexing, validation and report costs.

## 1. Integrate through the existing boundaries

Use A02 input/preparation/mapping, A03 read-only consumer validation, A05 adapters and A04 scoring. Introduce a small search owner with a source map; make only necessary shared refactors at the current owner. Do not duplicate decoders/scorers or weaken acquisition and held-out guards globally.

Concrete integration constraints found in review:

- `matchers.windows.routes`, `runner.run_batch` and the A05 job are development-specific. The runner also loads every evaluation asset into memory; copying that approach to three hours of music would violate memory limits. Process catalogue assets/bounded shards serially and reuse one adapter per worker.
- `matchers.cache.put` calls the A05 charge function directly. Reuse suitable identity/validation primitives, but give new A06 work an explicit accounting owner; do not redirect or reset the A05 ledger invisibly.
- `catalogue.ingestion.validate_local_ready` validates the original but returns the thirty-second derivative. Extend/share the appropriate read-only boundary for validated original samples when needed; do not mistake its return value for the full recording.
- A05's shared representation descriptor includes its frozen evaluation grid. Keep A06 search durations/hops, query aggregation, pitch preferences and display policy in separately versioned search configuration. Never mutate the chosen representation/config hash to disguise a search-policy change.
- Evaluation's 128-scored-interval-per-query limit belongs to that bounded prediction contract. It is not a 128-window limit on searching the catalogue. Use a separate search-result/index contract and bounded ranking; retain the existing evaluation limit for its frozen pools.

Validate the saved choice, shortlist, checkpoint and descriptors rather than trusting a method name. Keep the acoustic method available as an explicitly chosen alternative for diagnostics/development; no silent fallback under the EfficientAT identity. Missing weights or unsupported input must produce an actionable failure.

## 2. Prepare explicit queries and one honest substitute demo

Support one selected event or a bounded unordered collection of examples of the same intended sound, supplied through explicit local files/crops. Retain source hashes, parent recording/asset IDs, native bounds, preparation lineage and any known offset evidence. Preserve complete selected content, including attack/decay; make padding and duration limits explicit. The current adapter accepts up to thirty seconds. Never silently truncate an overlong query or infer the desired source layer from a filename.

For multiple examples, use a simple documented order-invariant rule, such as the mean of per-example cosine distances to each candidate. Retain per-example distances and the final aggregate. Deduplicate identical example identities by default so repeated copies cannot silently change weights. Record any query/candidate duration mismatch; a long mixed excerpt can emphasize accompaniment. More elaborate event selection, separation and learned fusion remain deferred.

If marked-version Loulou audio is present, inspect it and its evidence before making a recording-time crop. Preserve the full marked excerpt and record any shorter proposed variants as engineering selections, not confirmation of Leonardo's intended layer. Unknown-offset excerpts retain excerpt-relative coordinates. Run the real query when usable; otherwise retain a precise ready-to-run input/crop command and an explicit unrun status.

If Loulou is absent, deterministically choose a permitted, locally validated **development-side catalogue** source and a recorded non-silent short crop before inspecting rankings, for a labelled alternative engineering demo. Do not search for a query that makes results look good. Exclude its parent recording and known duplicates from discoveries. Independently use known-target fixtures for correctness; generated diagnostic positives must never appear as real-catalogue discoveries or substitute perceptual ground truth.

## 3. Build a bounded exact passage index over actual recordings

Target all locally validated ready recordings over their **full available-file durations**, using sequentially decoded original mixtures at the selected adapter's normal preprocessing boundary. Do not discard high-frequency content by silently indexing only the old 16 kHz centre crops. Keep originals immutable. Decode/validate once per bounded processing unit, rather than once per sliding window; record any reusable analysis derivative deliberately.

Start with the development-tested **2.4-second windows / 0.25-second hop**, including one unique end-aligned tail. On the public 72-record catalogue metadata, this yields approximately **44,025 windows** and **67,622,400 bytes** of float32 MN04 vectors before metadata. These are sizing calculations, not a measured index. The old per-window reservation scheme would reserve about 789 MB and approach the 100,000-managed-file guard when combined with existing features. Prefer compact immutable per-recording/batch shards with shared identity metadata; respect the 1 MiB JSON reader limit. Do not remove guards to accommodate inefficient storage.

Use a small deterministic development-side cost pilot to settle batch size and any necessary search-hop adjustment before the final configuration is frozen. Keep any second duration narrowly justified by query needs and budget; no large multi-scale sweep. The held-out evaluation must still use its exact frozen A05 grid regardless of catalogue-search settings. Use integer frame boundaries and deterministic rounding across native rates; shorter-than-window files and final tails need explicit behavior.

Store stable recording/asset identity, original byte/PCM hashes, feature/checkpoint/preprocessing identity, window bounds, coordinate maps, source/provenance links and coverage in the index manifest. Query reusable shards with exact cosine distance in bounded blocks; a vector database or approximate-nearest-neighbour service is unnecessary at this scale.

Commit progress atomically so interruption can resume missing work. Validate source and shard identities on reuse; a changed/deleted recording, checkpoint or recipe must invalidate/refuse affected results. Repeating a completed operation should verify/reuse work, not create a new allowance or silently re-embed everything. Keep finite cumulative read/validation costs visible too.

Report both recording coverage and **union of source intervals indexed**, not the sum of overlapping window durations. Distinguish original audio hours, indexed unique hours and processed window-seconds. If resources or unavailable assets prevent completion, retain explicit exclusions and searchable coverage, fail/mark the requested full run partial, and provide a truthful resume command. Do not call a thirty-second-per-track index complete or rerun exhausted catalogue acquisition.

## 4. Rank distinct recordings and return original passages

Default ranking uses the frozen EfficientAT timbre distance. Metadata such as title, artist, genre, family labels or known target times must not contribute to similarity. Return stable recording IDs, title/artist when known, actual source URL, score/direction, selected model/config, matched native interval and mapping to the available source. Do not turn cosine distance into a match probability.

Keep approximate pitch preference explicit and **off by default**. A small bounded classical estimate with declared reliability rules is sufficient for this baseline; use development/known-note fixtures to establish its behavior. If enabled, expose its contribution and parameter separately and keep it subordinate to timbre. Unpitched, silent or ambiguous/polyphonic estimates must abstain rather than invent a note or reject otherwise valid timbre candidates. Do not add pitch/fusion settings to the frozen held-out model check or imply Set B's pitch work is complete.

Exclude all query-parent recordings and their established source-ID/byte/PCM duplicate groups by default, including re-encodings recognized by A03. Multi-example queries exclude every known parent. Do not exclude an entire artist merely because the evaluation split groups artists; recording duplicates and evaluation families serve different purposes. Unknown edited copies remain a disclosed limit. A separate explicit self-match diagnostic may include the source without counting it as discovery.

Use deterministic score/ID/time tie handling. Suppress redundant overlapping hits and normally return one best passage per distinct recording/known duplicate group. Keep the scored interval distinct from an expanded playback-context interval. Do not transitively merge dense overlapping windows into a whole-song match or assign a window's score to an unscored union. Return fewer than ten eligible candidates honestly when necessary; without a calibrated rejection rule, top results are ranked candidates, not confirmed matches.

## 5. Produce and exercise a minimal local listening report

Generate a small local HTML report or equivalent local page with the query and about ten distinct-recording candidates, title/artist, source links, readable timestamps and direct audio controls. Label the substitute demo when used. Keep model hashes, resource ledgers and technical detail in companion machine-readable evidence rather than cluttering the listening view. No login, cloud hosting, telemetry or user-rating gate is needed.

Playback must use the **original available mixture**, not a mono/model-rate analysis window, separated stem or generated target. Because arbitrary compressed MP3 seeking remains unverified, derive bounded playback clips from the verified sequential decode and carry exact source-frame offsets. Preserve channels and time; declare the browser-compatible encoding, sample precision and any playback gain/conversion. Verify exported samples against the corresponding original crop under the declared conversion. Never silently clip or normalize away evidence.

Show the matched source interval and playback context separately. Clip time zero must map to the recorded original-file start. Use recording-time labels only when original offset/version evidence supports them; visibly mark excerpt-relative times. A provider's full-track label does not establish a verified external master timeline.

Use working relative local media paths or a narrowly scoped loopback-only report server. If serving is needed, expose only the owned report/media bundle through contained allowlisted paths, with explicit start/stop commands. Do not serve the repository root or arbitrary requested files. Report generation, opening and reuse must remain offline; an idle listening page is not an excuse for unbounded indexing workers.

Exercise the delivered page in an available browser: audio loads, duration is correct, play/pause and seeking within exported clips work, and stale/missing media fails visibly. Combine browser checks with independent numeric timing/sample checks. A successful WAV decode alone is not browser-playback evidence. If a browser capability is unavailable, finish independent tests and identify that exact verification gap without claiming it passed or asking Leonardo to perform the D04 review early.

## 6. Run one final held-out check with the unchanged choice

Complete development-side integration tests and freeze the A06 implementation/configuration before inspecting held-out matcher scores. Perform the final check before catalogue exploration is used to make any further algorithm choices. The authoritative protocol/suite is the atomic pair in `manifests/evaluation/comparison.json`, not an assumed canonical mirror.

| Frozen item | SHA256 |
| --- | --- |
| A05 choice | `95dce46b16760b002358b1aec3db8adb9b5df1c1f2033ee70b0b5121c2dea051` |
| Protocol | `07af66b37db00d6a6dd4bea87c9636b06aa9dbd43c75e8164be4568bd94b0048` |
| Suite | `d4c59416e5d4bb4aeddfbefa933a3a0f18691a25957e3623f1743d2951806441` |
| EfficientAT configuration | `5a487b946d748d48ec2945dae97e51f07bd0e8b106fa6c49c98df9e84a4035e9` |

Create a separate self-hashed A06 final-check declaration **before inference**, binding the unchanged A05 choice/shortlist, protocol/suite, method/config/checkpoint, exact split/grid, code/environment and finite run identity. Keep the original `choice.json` at stage A05. The new explicit A06 declaration supplies the scorer's final-choice guard; validate its provenance/bindings rather than accepting an arbitrary object with `stage: A06`.

Implement the necessary held-out coordinator at the appropriate inference/evaluation boundary, with A06 accounting. Do not relabel held-out examples as development, disable A05's refusal, run the old selection function on the test set or silently change the saved choice. Reuse the same feature extraction, 2.4-second/.25-second/tail interval rules, cosine scoring, preprocessing, no-pitch setting and empty refinement stage. All **80 held-out queries** must retain their denominators. Run only the selected **EfficientAT configuration** for the final model check; fixed constant/random controls may accompany it as diagnostics without choosing another model.

Persist predictions before scoring, retain per-condition/per-family hit@1/5/10, event coverage, misses, conditional boundary errors, absent-score distributions and measured costs. Clearly distinguish query hits from multiple-event recall. Grey1977 human agreement remains unavailable; do not change its eligibility. Small families, placement bias, reused backgrounds and unknown pretraining overlap remain limitations; no new accuracy threshold or independent-window significance claim.

One final evaluation may resume after a technical interruption under the same immutable configuration/run and retained charges. Re-scoring saved predictions is not a new independent experiment. Log whether any held-out results were inspected before a fix; preserve earlier results and describe later runs as post-inspection when applicable. Do not tune on failures and repeatedly call the same test untouched. A weak held-out result is a result to report, not grounds to select another default from that set.

## 7. Verify the whole path and leave a usable handoff

Add focused tests for the new boundaries: native-rate/tail intervals, query order invariance and duplicate examples, exact ranking, metadata/truth isolation, duplicate-parent exclusion versus diagnostic inclusion, timestamp/crop composition, pitch abstention/off behavior, source/index/clip corruption, partial coverage and resumable bounded work, and the A06 declaration/held-out guard. Verify sharded ranking against a small independent brute-force answer. Test path containment and safe rendering of source titles in the local report.

Demonstrate ingestion/validation → features/index → query → original playback with a known-target engineering fixture and independent expected source bounds, including crop/resample and excerpt cases. Known-target recovery may have algorithmic error; distinguish exact mapping correctness from measured localisation and report both. Run the real-catalogue substitute or Loulou query separately, plus a multiple-example query. Verify completed index/query reuse and that default discovery excludes reference parents/known duplicates.

Run ordinary/optional setup as applicable, dependency checks, Ruff/format, all affected tests and the inexpensive full regression suite, starter offline smoke, known answers through an appropriate accounting route, actual held-out inference/scoring, actual catalogue indexing/query/reuse and browser playback checks. Ordinary offline tests must not download models or consume the final held-out run. Record what was exercised on which platform; no CI pass claim when no hosted CI exists.

Update source maps, nearest setup/search/record/evaluation documentation, decisions and status. Write `reports/A06_SEARCH.md` with exact exercised commands for input/query preparation, bounded indexing, query/report creation and opening, final-check declaration/run/scoring, reuse and recovery. Provide one practical resume/demo command from the delivery repository root. Record coverage, model/query/index/run identities, resource consumption, omissions and external input gaps; sanitize versioned evidence and keep private audio, weights and generated reports local.

Before cleanup, ensure ignored runtime artifacts remain usable from the delivery checkout after merge; Git does not transfer them from a temporary worktree. Preserve/move only owned new artifacts through verified paths without overwriting existing originals, ledgers or user work. Do not delete the only usable index/report during worktree cleanup.

Finish through `AGENTS.md`: inspect the intended diff, commit/push, open a PR into current `main`, verify applicable checks/reviews/mergeability, merge when eligible, and remove task checkout/branches when no longer needed. Preserve earlier prompts and evidence. Summarize A01–A06 as complete, partial or blocked with evidence, separating **pipeline operation**, **held-out controlled results**, and **unmeasured human/Loulou relevance**. End with the playable report path, tested commands, merge evidence and remaining limitations. This batch ends at A06; do not automatically start Set B or ask for listening judgments.
