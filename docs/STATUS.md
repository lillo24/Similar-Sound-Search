# Project status

Updated 11 October 2026. **A01 complete; ready for the separate A02 prompt.** No audio-processing/search application or validated match exists yet.

## Inspected foundation

- Canonical remote: `https://github.com/lillo24/Similar-Sound-Search.git`.
- Checkout: `C:\Users\utente\Documents\GitHub\Similar-Sound-Search`.
- Delivery base revision: `bc9fc94dcb503d59266d154117f57b3faad23587` (`AGENTS.md`), from `main`. The initial A01 inspection used `ae9da07b75a37137004fe7a62510c7faca3a22c5` (`docs: archive A01 implementation prompt`).
- Initially cloned `a9626d26874cfcd45333ce2c9e897b3f2ad68dce`; fetched and fast-forwarded the newly published A01 prompt before editing. At that first inspection the checkout was clean, README and the archived prompt were the only project files, and no applicable instructions file was present. Leonardo subsequently committed `AGENTS.md`; its branch, PR, merge, and validation requirements govern delivery. No `implementation_plan_sections_suggestions.md` was found.
- Read the linked design document's direction, v2 roadmap, and autonomous-evaluation context. It is design evidence, not implementation evidence; relevant context is now durable in this repository.

## Delivered in A01

| Deliverable | Evidence |
| --- | --- |
| Purpose, state, and resume instructions | [README](../README.md) |
| Self-contained goals, autonomy rules, staged scope, and workspace layout | [PROJECT_BRIEF.md](PROJECT_BRIEF.md) |
| Practical reference/result contract, unknown handling, processing lineage, and source-time examples | [RECORDS.md](RECORDS.md) |
| Actual unverified reference record | [loulou.json](../manifests/references/loulou.json); no path/hash/verified interval invented |
| Observable evaluation categories, technical requirements, leakage control, and threshold policy | [EVALUATION.md](EVALUATION.md) |
| Decisions and unresolved assumptions | [DECISIONS.md](DECISIONS.md) |
| Reserved source/config/manifest/data/report locations and local-artifact exclusions | Directory markers and [.gitignore](../.gitignore) |

## Verification

- Reviewed the changed README and all new project records against the archived A01 prompt. Goals, stage identifiers, D04 review timing, explicit unknowns, evidence categories, and A02 boundaries agree. No upfront labels or listening gate was added.
- Reviewed the three timestamp examples: full-track crop and known-offset excerpt both map to recording seconds 218–240, while an unknown-offset excerpt remains at excerpt seconds 0–22. These are arithmetic examples, not tests on Loulou audio.
- Parsed the reference JSON and confirmed that path, hash, verified interval, and original offset remain null, with no selected events or processing operations claimed.
- Checked Markdown links, reference JSON, and whitespace across all versionable foundation files, including the subsequently committed `AGENTS.md`; all local links resolve and `git diff --check` reports no whitespace errors.
- Checked 89 Git-exclusion path cases with case-sensitive matching, including lower/upper/mixed-case audio and model extensions, local caches/secrets, retained directory markers, and versionable manifests/reports. All passed after correcting uppercase-extension handling.
- Confirmed that the archived A01 prompt is unchanged from the inspected base revision and that no unrelated work was present or modified.
- Relocated the checkout into `Documents\GitHub` on 11 October 2026 at Leonardo's request. Verified all 55 files, including Git metadata, by matching SHA-256 hashes before updating this location record. Git history, remote, and uncommitted A01 work were preserved; no files remain at the former location.

These were foundation/file checks, not an audio validation suite. No application tests, document-wording tests, model runs, downloads, or retrieval experiments were performed. Delivery uses the dedicated `codex/a01-foundation` branch and a PR into `main` under [AGENTS.md](../AGENTS.md); the GitHub PR and merge history provide the delivery record. No CI workflow was present in the delivery base.

## Repeatable A01 smoke check

Run these checks from the repository root before committing a foundation change. They need Git and PowerShell; Python/audio setup remains A02 work.

1. Run `git diff --check` (and `git diff --cached --check` after staging). Both must exit successfully without whitespace errors. Inspect `git status --short --untracked-files=all` and the full staged diff; only the intended plan's files should change. The archived A01 prompt and user-owned `AGENTS.md` must be preserved.
2. Parse and inspect the reference record:

   ```powershell
   $a01Reference = Get-Content -Raw -LiteralPath manifests/references/loulou.json | ConvertFrom-Json -ErrorAction Stop
   $a01Reference | Select-Object validation_status,requested_interval,verified_interval,timestamp_mapping
   $a01Reference.source | Select-Object availability,local_path,sha256,kind
   ```

   For this initial record, the requested interval is 218–240 seconds on a `claimed_recording` basis. The reference is unverified, the source is missing, and file path, hash, verified interval, mapping segments, and original offset remain null. No search or event-selection outcome may be inferred from the empty history/event lists.
3. Exercise exclusions without creating private files:

   ```powershell
   git -c core.ignorecase=false check-ignore --no-index -- data/audio/private.WAV data/features/example.npz data/models/weights.bin .env manifests/private/source.json
   ```

   Every input path must be printed as ignored. Check retained metadata separately:

   ```powershell
   git -c core.ignorecase=false check-ignore --no-index -- data/audio/.gitkeep manifests/references/loulou.json manifests/evaluation/split.json reports/evidence.md .env.example
   ```

   None of these paths should be printed; exit code 1 means none is ignored and is the expected result for this second command. The paths are hypothetical rule checks, not missing required assets. Pass paths as arguments: some Windows shell pipelines otherwise include carriage returns in Git's input filenames. Case-sensitive matching makes this check useful for Windows and Linux.
4. Follow all local links from the README and the project records; each must resolve. Review the record examples and evaluation contract for consistent coordinate bases, original-audio playback, development/held-out separation, and explicit limits on generated evidence. Missing Loulou audio and new user labels must not block this foundation.

Before merging, inspect the PR's current head, mergeability, reviews, and all available CI/status checks. A01 has no application build/test commands or CI workflow; do not report nonexistent CI as passed. These smoke checks cover the current foundation, while future runtime changes require their own meaningful checks.

## Capability and stage status

| Item | State |
| --- | --- |
| A01 durable foundation | Complete; adopted design and reference metadata only |
| Python/audio runtime and resource limits (A02) | Not established or tested |
| Catalogue acquisition (A03), benchmark generation (A04) | Not implemented or run |
| Matcher comparison (A05), first search/playback baseline (A06) | Not implemented or run |
| Event selection, separation, indexing/refinement, interface/package (B–D) | Planned; no capability claimed |
| Perceptual quality, mixture recovery, Loulou relevance | Unmeasured |
| Listening feedback | Not required until D04; no new user labels requested |

## A02 handoff

Use the separately supplied A02 prompt. Read the brief, records, evaluation contract, and decisions; reinspect Git status and any newer instructions. Establish runtime/dependency and resource evidence, locate available audio before requesting indispensable input, and verify source identity, file hash, duration, full-track/excerpt status, and timing before using the approximate Loulou request. Keep missing facts explicit. Do not apply full-track offsets twice to supplied excerpts.

Missing audio, unknown hardware, and unavailable catalogue/benchmark/model access are unresolved later inputs, not A01 blockers. Controlled engineering substitutes must be labelled and cannot stand in for evaluation of the intended Loulou reference. Do not add an upfront label collection or a new listening/approval milestone.
