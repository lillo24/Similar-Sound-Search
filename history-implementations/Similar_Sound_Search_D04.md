# D04 — First listening review of the delivered prototype

Implement **D04 only** in https://github.com/lillo24/Similar-Sound-Search. Prepare and technically verify a simple listening review of the installed product's saved Loulou search: the original reference, the actual first ten distinct-song candidates, exact timestamps, direct original/context playback and optional feedback. Deliver the finished review before asking Leonardo to listen. Do not run another search merely to reproduce results already available.

Follow `AGENTS.md` and `docs/PROJECT_BRIEF.md`. The goal is similarity of a selected sound's **timbre**, not matching song genre, mood, melody or recording identity. This is the first stage that asks Leonardo to listen. It is not a requirement that he find positives, identify an instrument, label a dataset or approve routine engineering. Keep **original mixture / legacy mean / pitch off**. Do not automatically start E01, retune the model or promote an experimental policy.

## Starting point and scope

D03 merged in [PR #32](https://github.com/lillo24/Similar-Sound-Search/pull/32), `4040f0a524bf62f1c905e5bcb44d8376cd0b70de`. Read current instructions, `reports/D03_PACKAGE.md` and `.json`, `docs/PACKAGE.md`, the brief and the relevant result/media readers before editing. The JSON's `handoff` section supplies the ordered cards and native identities; verify them against the actual saved publication when private assets are available.

The delivered archive is `dist/similar-sound-search-d03-1.0.0.zip`, **292,441,732 bytes**, SHA256 **`062f97ac056f75f664440c0bfc45caaea3ed7e52023d6568704098dda7808901`**. It contains a non-editable core 0.3.0 wheel, web assets/notices and an offline dependency closure. Its supported target is Windows AMD64 / exact Python 3.12.14 / Torch 2.6.0+cpu. Private assets remain separate. Optional complete C03/D02 views are omitted from this installed package, with their historical originals preserved.

D03 completed the Loulou and new two-example searches, each **98/98 units**, with zero catalogue encodes. All 40 scored/context clips passed native checks and all 40 browser controls passed technical playback. The Loulou search used the preceding installed artifact; the final artifact added scoped port-binding/UI repairs, reopened it and verified full numerical agreement. The new-query run and final playback used the final wheel. Preserve this distinction rather than claiming every search was rerun with the final artifact.

The prompt-authoring review independently passed **417 tests in 47.179s**, Ruff lint/format over 241 Python files, JavaScript syntax, pinned core setup/dependency checks, starter smoke and four-scalar/eleven-native known answers on Linux/Python 3.12.14. A fresh wheel included all web assets/notices and preserved matcher raw bytes. The ten public handoff rows have distinct groups/recordings and consistent frame-to-second coordinates. This review did not repeat private inference, Windows installation or actual listening. No hosted CI is configured.

D02's event-multi candidate failed its coverage gate in both splits despite better event recall. Its controlled evidence, the inspected A06 holdout and unit tests do not establish human or Loulou relevance. D03's muted browser checks likewise establish operation, not perceptual quality. D04 must keep engineering delivery, presentation of the review and actual human response as separate states.

## 1. Freeze the exact review input and candidate list

Use the existing completed D03 publication:

- Job: `06a4ee15a6956b3b55c8bf9a018b65ecc32f3bb81f4d902d14ee1b7a6a19dd1e`.
- Result: `2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374`.
- Reference revision: `c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3`.
- Materialization: `0ebb77012137c086e4cb1f72298e16446b33d96da2de28d7c9ccc5d663a03036`.
- Original available-file selection: **218..240s**, native **[9,613,800, 10,584,000)** at 44.1 kHz; context **217..241s**.

The available MP3's SHA256 is `2fc1256b1ac35134cfaef177aaf032277a0e375c676e50d391a1e3b22046ae30`. Its presence does not establish the marked version/master alignment, intended layer, rights or relevance. Keep the full 22-second original mixture. Do not silently replace it with a cleaner excerpt, guessed instrument stem or a differently timed master.

Assign stable review IDs to the saved ranks:

| ID | Candidate | Scored available-file interval |
| --- | --- | --- |
| D04-01 | Shivering Shadows (Featuring Viktor Van River) — Cutside | 03:11.000–03:13.400 |
| D04-02 | Body, soul — Viktor Van River | 02:00.000–02:02.400 |
| D04-03 | Amaterasu — Cutside | 01:37.000–01:39.400 |
| D04-04 | Essence 118 — mGee | 02:43.750–02:46.150 |
| D04-05 | Subway Cameo — Pete Lund | 03:14.500–03:16.900 |
| D04-06 | When I Lay Down — Gary Wood | 02:18.000–02:20.400 |
| D04-07 | Absurdius Rex — Jovian Year | 00:07.750–00:10.150 |
| D04-08 | Something To See (De Vries Instrumental) — Donnie Ozone | 03:08.500–03:10.900 |
| D04-09 | Confusion — Mos Emvy | 00:10.000–00:12.400 |
| D04-10 | Gladiator Season — GLD8TRZ | 03:23.250–03:25.650 |

Validate distinct groups/recording identities, not only different display labels. Preserve rank, selected policy, scores, native representatives, context intervals and media identities from the result. The metadata is not independent human verification of song identity. Do not replace awkward or weak matches, reorder after inspecting them, select another arm's passages or pad the list with additional windows from the same song. Missing/corrupt material is an explicit unavailable item, not a reason to silently substitute a better candidate.

Create a versioned D04 review manifest binding the package, query, job/result, population, selected arm and every review ID to its recording/group, sample rate, native scored/context frames and media hashes. Keep its immutable identity separate from evolving feedback. If the reference, candidate set or timing later changes, it is a new review version; earlier opinions cannot silently migrate to it.

## 2. Make the listening task easy to open and use

Reuse the installed D03 app and saved clips. Add only the focused review page/export and small amount of feedback handling needed for a coherent review. Prefer separate D04 scripts/assets or a small companion tool outside the frozen core/distribution packages. Do not rebuild the 292 MB distribution, replace its installed files, change numerical source/version identities or weaken consumer guards for presentation work. The delivery evidence already leaves little space in its 3 GiB setup allocation; creating another full environment/archive is unnecessary.

Provide a single tested command or launcher and a clear local review link. The existing app starts with:

```powershell
& "$env:USERPROFILE\Documents\Sound Search D03 à\installed\Scripts\python.exe" -I -m sound_search_distribution start --workspace "C:\SSS D03 à\w" --port 8776
```

Reuse the actual verified paths if unchanged; discover and report an explicit replacement if they moved. Do not create a new workspace/allocation to make a missing path work. Open the exact completed Loulou job, identified by prefix `06a4ee15`, rather than submitting Search or relying on whichever result a previous browser session selected. The result API takes a **job ID**, whereas result-media URLs bind a **result ID**. The existing read-only reference route is `/private-reference/loulou.wav`; resolve and verify its bytes/selection instead of calling the charged preview operation.

The review should put reference playback first, then the ten numbered cards. Each card needs title/artist, the scored interval, **Play passage**, and separately labelled **Play context**. Keep the reference easy to replay while comparing candidates. Stop the previous player when another begins; support pause/seek, keyboard use and readable narrow-screen layout. No autoplay, audio mixing, new normalization, resampling, separation or playback-speed changes. State that context is unscored and timestamps refer to the supplied audio file, without inventing an external streaming-service/master offset.

Keep the main page concise. It should explain that these are the baseline's candidates and ask about the type of sound. Raw hashes, distances and resource internals belong in an inspectable evidence area. Do not convert distance/rank into a confidence percentage or label a candidate a confirmed match. No flattering summaries or suggested answers next to the listening controls.

A thin local report may reuse verified clips through the existing result-bound routes or copy only its allowlisted media into a private review bundle. If exporting, preserve exact media bytes, recording/query/result bindings and checksums; never expose a general workspace file server. A companion server must bind loopback, enforce finite paths/sizes and preserve appropriate Host/Origin/token protection for any writes. Keep export/local-feedback writes separate from application operations; review clicks must not submit jobs, import references, alter recipes or write the D03 pool/registry.

Explain that **127.0.0.1 refers to the computer running the app**. A narrow desktop viewport is not evidence of phone access. Do not advertise the Windows localhost URL as playable on Leonardo's phone, open a LAN listener, deploy publicly or upload private audio to solve this. A private portable export is acceptable within the output limit, with an accurately tested opening method; do not promise Android playback unless it was exercised. The supported Windows listening route is sufficient for this stage.

## 3. Invite a small, honest human review

Finish the page, manifest, checks and instructions before asking for input. First invite Leonardo to replay the reference and say whether this is the intended recording/section and which sound he means within the mixture. A short everyday description or “unsure” is enough; do not require an instrument name or a new recording. This question now serves the first listening review, not an engineering approval gate.

Offer optional per-card responses: **similar type of sound**, **different**, **unsure**, or **not listened**; a brief reason may be added. Unanswered items start as not listened. A simple reply such as `reference: …; D04-01 similar; D04-02 different; D04-03 unsure` must work without an account, form completion or ten mandatory labels. If a local form is provided, export its responses as a small JSON/Markdown file and make save/export status explicit. Browser storage alone is not a durable submission; test reload and export/import, reject another review's IDs, and preserve edits without silently overwriting previous feedback.

Keep actual human responses, optional playback observations and technical QA separate. A play event, muted automation, opened page or successful seek is not evidence that Leonardo listened or found a match. Never fill ratings from model distances, generated descriptions, inferred instrument identity or an agent's own impressions. If no reply arrives, record **“listening review pending; relevance unmeasured”**. Do not remain in a blocking tool wait, manufacture a review or call the human portion complete. If Leonardo declines, record that explicitly without turning it into a negative rating.

If Leonardo says the wrong version/section/layer was used, retain this review as evidence about the original full-mixture query and record the mismatch. Do not reinterpret its results as a test of the corrected target. A new crop/query/search or additional resource use requires a subsequent concrete task; this prompt does not spend normal capacity on speculative revisions. Likewise, listening notes do not verify copyright permission or external master alignment.

When genuine responses are available, report the actual counts: shown, listened/rated, similar, different, unsure and unanswered. Preserve each response's review/item identity, provenance and revision. Distinguish unlistened from negative, and technical failure from perceptual rejection. Do not present a few selected top-ten judgments as a calibrated precision estimate, inter-rater agreement, unseen-catalogue generalization or proof of the model's failure cause. With one listener and one reference, the useful output is qualitative relevance evidence and concrete follow-up questions. Keep raw free-text notes private; commit only sanitized summaries and reproducible technical evidence.

## 4. Bound the work and verify the exact delivered review

No new inference, catalogue encoding, acquisition, model download, dependency change, GPU use, paid service or full D02 rerun is authorized. D03 verification is sealed; normal capacity is reserved for real user requests. **Both shares, every older pool and the external allocation registry must remain unchanged by D04 preparation and review.** Do not unseal verification, refill a ledger, create an alternate registry or hide a search inside QA.

This task authorizes a separate, small **non-inference D04 preparation allowance**: at most **600 aggregate supervised processing seconds**, **16 bounded processing invocations**, **6,000 source-audio seconds decoded for necessary validation**, and **128 MiB total new managed output**. Within that total, cap QA artifacts at **32 MiB**, review metadata/feedback at **16 MiB**, and any private media copies/export at **64 MiB**. Count retries, temporary files and export copies. Record usage in D04-owned receipts/inventory; reuse existing tooling rather than building another general scheduler. Each processing invocation retains a 120-second deadline, one numerical thread and the existing memory/I/O bounds. These invocations are preparation/export/audit workers, not individual HTTP requests or player clicks. Human listening and idle foreground service time are not processing-worker seconds; distinguish them in evidence.

Preserve the combined 4 GiB managed-storage limit and 4 GiB free-space headroom, including the reserved 512 MiB normal-use output and the new review. Do not copy the full 812 MB private closure or the whole distribution. Use explicit owned review paths; stop on a cap rather than deleting historical evidence. Preserve the three C01 staging folders whose deletion was denied with “blocked by policy”; do not retry that action through another tool/path.

Validate the saved result through the existing read-only API/provider and media reader. Check query/arm/population/group/order, native frames, media membership and original reference selection against the D03 manifest. For byte-identical reused clips, retain D03's independent native proof and verify fresh hashes/headers/frames; do not claim a new full-source audit. New or transformed audio is unnecessary. Fail if stale or cross-result media is substituted.

Exercise the delivered review's reference and all **20 candidate scored/context controls**, including play/pause/seek, one-at-a-time playback, reload, a fresh browser, desktop and 390px layout. Inspect long titles, missing-media errors and any feedback export/import. Test that loading, playback and feedback do not dispatch inference or change the application ledgers/registry. Use malformed/foreign/stale IDs in isolated fixtures; never corrupt the live package. Record browser/native/HTTP checks separately, including whether playback was muted and whether a physical phone was tested. No silent pacing workaround or injected UI success.

Run focused tests for new manifest/feedback/rendering behavior, applicable lint/format/JavaScript checks, and the inexpensive full regression suite if code/shared tooling changes. Documentation-only reuse need not trigger repeated expensive package/model acceptance. The public clone lacks private audio and the Windows installation: complete independent work and state exact blocked prerequisites if they are missing, without claiming actual listening-page playback passed. Do not substitute synthetic audio for the real reference/candidates.

## 5. Deliver, merge and leave an honest handoff

Deliver **`reports/D04_LISTENING.md`**, sanitized machine-readable evidence, the immutable review manifest, a blank feedback template and the working private local review page/bundle with its tested launch instructions. Keep audio, private paths, tokens and raw notes ignored. The Markdown report must be directly downloadable and readable without the app; it should identify the reference, list the ten candidates/times, explain how to play them and state what remains unmeasured. Do not rely on a screenshot or “Report” label without a real artifact.

Record package/result/review hashes, actual available items, old/new QA scope, resource usage, preserved pool/registry hashes and user-review state. Engineering delivery may be complete while listening is pending. Positive, negative, mixed and absent feedback must all be representable without rewriting that technical outcome. If feedback arrives during work, incorporate it as attributed user evidence; do not let it trigger unrequested algorithm work.

Follow the normal isolated-branch/PR workflow. Update relevant navigation/status documentation, review the diff, run affected checks, push, open a PR into current `main`, and merge automatically when checks/reviews/mergeability permit. The listening invitation is **not a code-merge approval requirement**. Merge the finished review tooling/report with human status pending if necessary, and preserve required private artifacts before removing only the owned task checkout/branches where permitted. Do not leave the technical work unmerged solely because optional ratings have not arrived.

Finish with the tested command/link, downloadable report, merge evidence and one short invitation to listen to the reference and candidates. State explicitly whether Leonardo's review is pending, partial, completed or declined. Do not call technical player verification a completed human review. Suggest later work only from observed feedback/limits, and distinguish hypotheses such as wrong query layer, limited catalogue or representation/ranking loss from demonstrated causes. **Do not automatically implement or start E01.**
