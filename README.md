# Similar Sound Search

Select a particular sound inside a song and find passages in other recordings with a similar sound character, with playable results and trustworthy timestamps. Timbre comes first, approximate pitch second; matching phrase rhythm or note order is deferred.

**Current state: A01 foundation complete.** This repository contains the brief, record contract, evaluation plan, an unverified reference manifest, and workspace locations. Audio processing, model execution, search, playback, and retrieval quality have not been implemented or tested. There is no application command to run yet.

The first reference is **daoud — Loulou & the loulous**, approximately **3:38–4:00** in Leonardo's marked recording. The audio file, recording version, excerpt offset, and exact event remain unverified. Missing audio does not block A01. No new labels or manually discovered similar songs are required; the first required listening review is D04.

## Project records

- [Project brief and roadmap](docs/PROJECT_BRIEF.md): goals, autonomy rules, stage boundaries, and workspace layout.
- [Reference and result contracts](docs/RECORDS.md): identity, provenance, unknowns, processing lineage, and timestamp mapping.
- [Evaluation contract](docs/EVALUATION.md): observable checks, evidence limits, and model-selection discipline.
- [Decisions and unresolved assumptions](docs/DECISIONS.md).
- [Status and A02 handoff](docs/STATUS.md).
- [Initial reference manifest](manifests/references/loulou.json).
- [Archived A01 prompt](history-implementations/Similar_Sound_Search_A01.md).

## Resume at A02

Follow [AGENTS.md](AGENTS.md) for implementation and GitHub delivery. Each implementation plan uses an isolated branch and a PR into `main`; checks, merge, and branch cleanup are part of completion. The [status record](docs/STATUS.md) includes a repeatable A01 smoke-check procedure.

Use the separate A02 prompt to inspect available runtime, hardware, audio inputs, and resource limits, then establish a reproducible Python environment. Inspect available files before requesting an indispensable input. A03 builds the starter catalogue; A04 builds benchmarks; A05 compares matchers; A06 delivers the first runnable baseline. A06 is an internal milestone; D04 is the first required user relevance review.

Code and configuration locations are reserved, without a placeholder application or dependency stack. Local audio, features, indexes, weights, run output, and secrets are excluded by [.gitignore](.gitignore). Keep sanitized manifests and shareable evidence reports versionable; see the brief before adding data.
