# Similar Sound Search

Select a particular sound inside a song and find passages in other recordings with a similar sound character, with playable results and trustworthy timestamps. Timbre comes first, approximate pitch second; matching phrase rhythm or note order is deferred.

**Current state: A03 catalogue ingestion implemented and exercised with 72 distinct real recordings from 35 artists.** The CLI acquires a bounded Internet Archive/blocSonic sample, verifies immutable originals and prepares centred analysis excerpts through the shared WAV/FLAC/MP3 CPU pipeline. [A03 evidence](reports/A03_CATALOGUE.md) records the actual partial catalogue, counts, costs and limits. Model comparison, search and result playback remain later stages; retrieval quality is unmeasured.

The first reference is **daoud — Loulou & the loulous**, approximately **3:38–4:00** in Leonardo's marked recording. The actual audio is still missing; recording version, excerpt offset, and exact event remain unverified. Engineering fixtures do not substitute for that reference. No new labels or manually discovered similar songs are required; the first required listening review is D04.

## Run the offline diagnostic

From the repository root in PowerShell, using a working Python 3.12 executable:

```powershell
.\scripts\setup.ps1 -PythonExecutable python
.\.venv\Scripts\sound-search.exe --tier starter smoke
```

The setup uses a local `.venv` and pinned binary dependencies. The smoke needs no audio download, network, model, GPU, or supplied reference and writes `reports/local/smoke.json`. Use starter for a workspace containing the acquired catalogue: the default smoke tier still has its original 256 MiB managed-disk ceiling and zero download allowance. [RUNTIME.md](docs/RUNTIME.md) covers interpreter selection, Linux equivalents, inspection/preparation commands, supported encodings, timestamp semantics, resource limits, and failure recovery. [A02 evidence](reports/A02_RUNTIME.md) preserves the historical foundation.

## Acquire or resume the catalogue

```powershell
.\.venv\Scripts\sound-search.exe --tier starter catalogue acquire --job starter
```

Repeat after a bounded invocation stop. Download, attempt and job-time allowances persist across invocations; an exhausted lifetime allowance does not reset. [Catalogue commands](docs/CATALOGUE.md) document the pilot, frozen selection, verification, explicit local import and recovery. Audio stays ignored locally; [catalogue manifests](manifests/catalogue/README.md) retain sanitized identity, licence evidence, hashes and duplicate groups. Ready metadata in a fresh checkout does not mean the corresponding audio is locally available.

## Project records

- [Project brief and roadmap](docs/PROJECT_BRIEF.md): goals, autonomy rules, stage boundaries, and workspace layout.
- [Reference and result contracts](docs/RECORDS.md): identity, provenance, unknowns, processing lineage, and timestamp mapping.
- [Evaluation contract](docs/EVALUATION.md): observable checks, evidence limits, and model-selection discipline.
- [Decisions and unresolved assumptions](docs/DECISIONS.md).
- [Runtime and commands](docs/RUNTIME.md), [measured A02 evidence](reports/A02_RUNTIME.md), and [resource profile](config/resource_limits.json).
- [Catalogue commands](docs/CATALOGUE.md), [measured A03 evidence](reports/A03_CATALOGUE.md), and [status/A04 handoff](docs/STATUS.md).
- [Initial reference manifest](manifests/references/loulou.json).
- [Archived A01 prompt](history-implementations/Similar_Sound_Search_A01.md).
- [Archived A02 prompt](history-implementations/Similar_Sound_Search_A02.md).
- [Archived A03 prompt](history-implementations/Similar_Sound_Search_A03.md).

## Resume at A04

Follow [AGENTS.md](AGENTS.md) for implementation and GitHub delivery. Each implementation plan uses an isolated branch and a PR into `main`; checks, merge, and branch cleanup are part of completion. Reinspect current code and run the [complete local validation](docs/RUNTIME.md#validation) before extending the pipeline.

A04 builds benchmarks and controlled test generation, separately from A03 discovery music. A05 compares matchers; A06 delivers the first search baseline. A06 is an internal milestone; D04 is the first required user relevance review. Missing Loulou audio does not block independent benchmark work, but prevents a reference-specific experiment. Preserve the measured A03 shortfall and existing resource ceilings when consuming the catalogue.

The [source map](src/README.md) and [config map](config/README.md) describe ownership. Local audio, features, indexes, weights, run output, and secrets are excluded by [.gitignore](.gitignore). Keep sanitized manifests and shareable evidence reports versionable; see the brief before adding data.
