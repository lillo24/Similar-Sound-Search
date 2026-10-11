# Similar Sound Search

Select a particular sound inside a song and find passages in other recordings with a similar sound character, with playable results and trustworthy timestamps. Timbre comes first, approximate pitch second; matching phrase rhythm or note order is deferred.

**Current state: A02 runtime and input tooling complete.** The offline CLI inspects WAV/FLAC files and prepares bounded, immutable channel/crop/resample derivatives with hashes and source-time mappings. Catalogue acquisition, model comparison, search, and result playback remain later stages; retrieval quality is unmeasured.

The first reference is **daoud — Loulou & the loulous**, approximately **3:38–4:00** in Leonardo's marked recording. The actual audio is still missing; recording version, excerpt offset, and exact event remain unverified. Engineering fixtures do not substitute for that reference. No new labels or manually discovered similar songs are required; the first required listening review is D04.

## Run the offline diagnostic

From the repository root in PowerShell, using a working Python 3.12 executable:

```powershell
.\scripts\setup.ps1 -PythonExecutable python
.\.venv\Scripts\sound-search.exe smoke
```

The setup uses a local `.venv` and pinned binary dependencies. The smoke needs no audio download, network, model, GPU, or supplied reference and writes `reports/local/smoke.json`. [RUNTIME.md](docs/RUNTIME.md) covers interpreter selection, Linux equivalents, inspection/preparation commands, supported encodings, timestamp semantics, resource limits, and failure recovery. [A02 evidence](reports/A02_RUNTIME.md) distinguishes the exercised Windows CPU route from untested capabilities.

## Project records

- [Project brief and roadmap](docs/PROJECT_BRIEF.md): goals, autonomy rules, stage boundaries, and workspace layout.
- [Reference and result contracts](docs/RECORDS.md): identity, provenance, unknowns, processing lineage, and timestamp mapping.
- [Evaluation contract](docs/EVALUATION.md): observable checks, evidence limits, and model-selection discipline.
- [Decisions and unresolved assumptions](docs/DECISIONS.md).
- [Runtime and commands](docs/RUNTIME.md), [measured A02 evidence](reports/A02_RUNTIME.md), and [resource profile](config/resource_limits.json).
- [Status and A03 handoff](docs/STATUS.md).
- [Initial reference manifest](manifests/references/loulou.json).
- [Archived A01 prompt](history-implementations/Similar_Sound_Search_A01.md).
- [Archived A02 prompt](history-implementations/Similar_Sound_Search_A02.md).

## Resume at A03

Follow [AGENTS.md](AGENTS.md) for implementation and GitHub delivery. Each implementation plan uses an isolated branch and a PR into `main`; checks, merge, and branch cleanup are part of completion. Reinspect current code and run the [complete local validation](docs/RUNTIME.md#validation) before extending the pipeline.

Use the separate A03 prompt for automated starter catalogue acquisition under the resource and provenance contracts. A04 builds benchmarks; A05 compares matchers; A06 delivers the first search baseline. A06 is an internal milestone; D04 is the first required user relevance review. Missing Loulou audio does not block unrelated catalogue/runtime work, but prevents a reference-specific experiment.

The [source map](src/README.md) and [config map](config/README.md) describe ownership. Local audio, features, indexes, weights, run output, and secrets are excluded by [.gitignore](.gitignore). Keep sanitized manifests and shareable evidence reports versionable; see the brief before adding data.
