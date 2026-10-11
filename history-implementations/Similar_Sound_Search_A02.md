# A02 — Runtime, inputs, and resource limits

Implement **A02 only** in https://github.com/lillo24/Similar-Sound-Search. Produce working runtime and audio-input tooling, execute meaningful checks, and complete the repository's branch/PR delivery workflow. This is an implementation task, not a request for another plan.

## Starting point and scope

Reviewed on 11 October 2026: A01 is merged through PR #1 at `c6e0068692460f3ff64fba8711e2fc9e9589a1cb`. It provides `README.md`, `AGENTS.md`, the five project records under `docs/`, `manifests/references/loulou.json`, Git exclusions, and reserved workspace directories. No Python environment, executable audio pipeline, models, or search exists at that revision.

Reinspect current `main`, local changes, and applicable instructions before editing. Read `docs/PROJECT_BRIEF.md`, `docs/RECORDS.md`, `docs/EVALUATION.md`, `docs/DECISIONS.md`, and `docs/STATUS.md`. Preserve their adopted direction: timbre first, approximate pitch second, phrase rhythm deferred, and no user-labelled dataset or listening gate before D04.

Use the existing `src/`, `config/`, `manifests/`, `data/`, and `reports/` responsibilities. Choose the smallest useful implementation within them. A03 owns catalogue acquisition, A04 the retrieval benchmark suite, A05 model comparison, and A06 the first search. Do not implement those stages, select a winning model, install a heavy model stack, or claim perceptual performance in A02.

## External context and inputs

- Run against the **actual machine available to this Codex session**. Detect its OS and resources. The Windows checkout recorded by A01 is historical context, not a guaranteed path or evidence about the current machine. Never present a cloud runner's hardware as Leonardo's PC.
- The intended audio is **daoud — Loulou & the loulous**, approximately **3:38–4:00** in the marked version. It is not committed to the repository. Look first in supplied task attachments and explicit project input locations; ChatGPT files and Google Docs are not automatically accessible to this agent.
- All necessary design context is now in the repository. Google Doc access is optional. Model checkpoints, external datasets, catalogue accounts, and user relevance labels are unnecessary for A02.
- If the actual reference is missing, leave the Loulou record unverified, implement its input path, and run clearly labelled deterministic engineering fixtures. Report the exact outstanding input at the end. Missing audio must not block independent runtime, input, timestamp, or resource work, and a substitute must never be reported as a Loulou experiment.

## 1. Establish and exercise a reproducible runtime

Inspect available Python interpreters, package tooling, CPU, RAM, writable disk space, audio decoders, and optional GPU/VRAM. Record the evidence and missing capabilities. Do not install GPU frameworks solely to discover whether a GPU exists.

Choose a supported Python version and a small dependency set compatible with the actual platform and likely later audio work. Explain consequential choices briefly. Add project-local setup and reproducible dependency specifications/lock or equivalent pinned resolution. Verify version-sensitive APIs against the selected versions' official documentation.

Keep a CPU-capable route. Use a project-local environment and avoid global Python, driver, or OS changes. A decoder or GPU that is unavailable must be reported explicitly; a functioning WAV/lossless engineering route is a valid limited fallback, with unsupported formats clearly identified. Do not claim dependency installation or format support that has not been exercised.

Provide one diagnostic/smoke command, with a simple CLI entry point chosen to fit the repository. It should report the environment and decoder capabilities, exercise decoding, channel handling, resampling, and a minimal acoustic measurement, and write a structured report. A minimal measurement checks plumbing; it is not the A05 matcher. Heavy model downloads, network access, and a supplied reference must not be prerequisites for the offline smoke path.

## 2. Inventory and inspect available audio

Implement a small input inspection/registration interface accepting an explicit file or bounded project input directory. Do not scan unrelated personal folders. Check supported formats, readable samples, duration, sample rate, channel count, file-byte SHA-256, and whether data are silent or invalid. Limit probing/decoding of large or malformed inputs within the resource policy.

Preserve the A01 record contract's identity, provenance, explicit unknowns, and separate requested/verified intervals. Implement validation only for the parts A02 uses. If a contract adjustment is necessary, version and document it and update affected examples and consumers together.

Inspect possible Loulou inputs rather than assuming a matching filename proves recording identity, version, or original offset. An existing short excerpt must not be cropped again at second 218. A file that decodes successfully can have verified technical metadata while recording identity, target event, or original offset remain unknown; preserve those distinctions.

Record known source association and permitted-use information from supplied context without inventing it. If the available asset cannot be confidently associated with the intended reference, register it as a candidate input and keep the Loulou association unverified. Exact sound-event selection belongs to B01 and must not introduce a required listening review now.

## 3. Prepare derivatives with trustworthy timestamps

Keep originals immutable. Add only the preparation needed to demonstrate the runtime: explicit channel policy, resampling, and an optional validated crop. Record the original and derivative hashes, sample counts/rates, tool/version, parameters, and a composable mapping back to the original available file.

Use the A01 distinction between file time and original-recording time. Apply a verified excerpt offset once. Unknown offsets remain null and use excerpt-relative display times. Do not convert the approximate Loulou request into a verified crop from duration alone.

Declare crop rounding, output duration, and resampler timing behavior. Do not confuse a sample-rate conversion with a change in playback speed. Account for measured decoder/resampler delay when relevant; disclose unverified compressed seek behavior. Reject invalid intervals or channels explicitly rather than silently clamping, dropping the target, or returning a successful placeholder.

Write outputs atomically where practical and avoid overwriting unrelated assets. Re-running an unchanged preparation should reuse a valid derivative or reproduce it consistently. Validate reuse against source identity and processing parameters; never attribute stale derivatives to changed input. This is limited preparation reuse, not C04's catalogue-wide processing system.

## 4. Establish actionable resource limits

Create a documented, machine-readable resource profile with explicit numeric limits chosen from the detected machine and a short smoke pilot. Include download bytes, managed disk use/free-space headroom, processing time, concurrency, and the model shortlist cap for later stages. Keep a small smoke tier and a bounded starter-catalogue tier distinguishable.

Default to no new paid services, no private-audio uploads, and no public deployment. Do not equate coding-token availability with permission to spend money on compute. Prefer modest initial limits over an unmeasured large batch.

Enforce applicable limits at A02 preparation boundaries, including oversized input/output estimates and insufficient space. Record limits that are configuration contracts for future stages rather than pretending that absent download/model/index code already enforces them. Use a clear stop/skip/failure result when a limit is reached; preserve completed work and explain the resumption command.

Report measured smoke runtime and managed output size separately from estimates for future workloads. Do not publish unrelated personal paths, hostnames, environment secrets, or a full dump of the machine. Use ignored local records for machine-specific details and sanitized shareable summaries where useful.

## 5. Verify the critical behavior

Run the setup and CLI you actually deliver. Use small deterministic audio fixtures generated during testing, with known channels, sample rates, event locations, and durations. These are engineering fixtures, not A04's perceptual/retrieval benchmark or real discovery songs.

Cover the meaningful risks:

- Decoding and metadata/hash capture on a valid input, plus corrupt, unsupported, and silent inputs with distinguishable outcomes.
- Stereo/channel policy and resampling, including sample-count rounding and preservation of known event timing within declared tolerances.
- Full-track crops, known-offset excerpts, and unknown-offset excerpts; apply original offsets once and never infer them from a filename or the requested interval.
- Invalid/out-of-bounds intervals and incomplete metadata, with actionable errors and no false verified states.
- Source immutability, changed-source invalidation, and repeatable preparation/reuse.
- Resource-limit refusal and recovery without presenting a partial output as complete.
- The missing-Loulou path: the offline smoke command works, and reference-specific status remains unverified/not run.

Assert independent known answers rather than only testing that a function agrees with its own output. Run formatting/static checks appropriate to the chosen stack and the tests covering changed behavior. Do not add slow model, network, or audio-collection checks to routine validation. If adding CI, follow `AGENTS.md` resource discipline and keep it small and relevant.

## Delivery and handoff

Update the nearest documentation, decision log, and stage status with what runs, supported/unsupported inputs, resource limits, measured costs, limitations, and exact setup/diagnostic/inspection/preparation commands for the detected platform. Keep reusable metadata versionable and private machine/input records in the existing ignored locations.

Follow `AGENTS.md`: use an isolated branch/worktree, inspect the diff, commit intended files, push, open a PR, and merge after applicable checks pass and there is no unresolved consequential issue. Complete the prescribed worktree/branch cleanup. Preserve the archived A01 prompt. Do not claim nonexistent CI as passed or stop at a local-only implementation.

Finish with the PR/merge reference, concise changes, actual verification results, detected environment, one runnable smoke command, supported audio capabilities, and any precise missing reference input. State whether A02 is complete or which part remains blocked. Distinguish working audio plumbing from retrieval quality, which A02 does not measure.

Leave the repository ready for **A03 — Automated starter catalogue**. Do not request new similar/dissimilar examples or a listening review.
