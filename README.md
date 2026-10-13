# Similar Sound Search

Select a particular sound inside a song and find passages in other recordings with a similar sound character, with playable results and trustworthy timestamps. Timbre comes first, approximate pitch second; matching phrase rhythm or note order is deferred.

**Current state: A05 development comparison delivered; provisional EfficientAT MN04 choice ready for A06.** Both the acoustic baseline and a genuine pretrained CPU model ran all 80 development queries under the prospectively revised hit@1 protocol. [A05 evidence](reports/A05_MATCHERS.md) records controlled-source results, controls, costs and limits. Human agreement remains unavailable: Grey1977 has zero eligible pairs. The A03 catalogue remains partial at 72 recordings/35 artists; real-catalogue search and held-out model checks remain A06 work.

The first reference is **daoud — Loulou & the loulous**, approximately **3:38–4:00** in Leonardo's marked recording. The actual audio is still missing; recording version, excerpt offset, and exact event remain unverified. Engineering fixtures do not substitute for that reference. No new labels or manually discovered similar songs are required; the first required listening review is D04.

## Run the offline diagnostic

From the repository root in PowerShell, using a working Python 3.12 executable:

```powershell
.\scripts\setup.ps1 -PythonExecutable python
.\.venv\Scripts\sound-search.exe --tier starter smoke
```

The setup uses a local `.venv` and pinned binary dependencies. The smoke needs no audio download, network, model, GPU, or supplied reference and writes `reports/local/smoke.json`. Use starter for a workspace containing the acquired catalogue: the default smoke tier still has its original 256 MiB managed-disk ceiling and zero download allowance. [RUNTIME.md](docs/RUNTIME.md) covers interpreter selection, Linux equivalents, inspection/preparation commands, supported encodings, timestamp semantics, resource limits, and failure recovery. [A02 evidence](reports/A02_RUNTIME.md) preserves the historical foundation.

## Generate, validate and score the evaluation suite

```powershell
.\.venv\Scripts\sound-search.exe --tier starter evaluation generate
.\.venv\Scripts\sound-search.exe --tier starter evaluation validate --split all
.\.venv\Scripts\sound-search.exe --tier starter evaluation known-answer
```

The delivered protocol requires its four locally validated A03 backgrounds; a fresh checkout needs the matching audio and private registration. [Evaluation commands](docs/EVALUATION.md#a04-delivered-commands-and-protocol) cover explicit network benchmark inspection, resumption, prediction scoring and recovery. A04 has separate finite allowances and never resets A03's exhausted acquisition ledger. Audio stays ignored; [evaluation manifests](manifests/evaluation/README.md) preserve recipes and truth. Ready metadata alone does not establish local availability.

## Project records

- [Project brief and roadmap](docs/PROJECT_BRIEF.md): goals, autonomy rules, stage boundaries, and workspace layout.
- [Reference and result contracts](docs/RECORDS.md): identity, provenance, unknowns, processing lineage, and timestamp mapping.
- [Evaluation contract](docs/EVALUATION.md): observable checks, evidence limits, and model-selection discipline.
- [Decisions and unresolved assumptions](docs/DECISIONS.md).
- [Runtime and commands](docs/RUNTIME.md), [measured A02 evidence](reports/A02_RUNTIME.md), and [resource profile](config/resource_limits.json).
- [Catalogue commands](docs/CATALOGUE.md), [measured A03 evidence](reports/A03_CATALOGUE.md), and [status/A05 handoff](docs/STATUS.md).
- [Matcher setup/commands](docs/MATCHERS.md), [measured A05 evidence](reports/A05_MATCHERS.md), and [provisional choice](manifests/matchers/choice.json).
- [Measured A04 evidence](reports/A04_BENCHMARKS.md) and [frozen protocol](manifests/evaluation/protocol.json).
- [Initial reference manifest](manifests/references/loulou.json).
- [Archived A01 prompt](history-implementations/Similar_Sound_Search_A01.md).
- [Archived A02 prompt](history-implementations/Similar_Sound_Search_A02.md).
- [Archived A03 prompt](history-implementations/Similar_Sound_Search_A03.md).
- [Archived A04 prompt](history-implementations/Similar_Sound_Search_A04.md).
- [Archived A05 prompt](history-implementations/Similar_Sound_Search_A05.md).

## Resume at A06

Follow [AGENTS.md](AGENTS.md) for implementation and GitHub delivery. Each implementation plan uses an isolated branch and a PR into `main`; checks, merge, and branch cleanup are part of completion. Reinspect current code and run the [complete local validation](docs/RUNTIME.md#validation) before extending the pipeline.

A05 selected the frozen EfficientAT MN04 adapter provisionally on controlled development evidence. A06 integrates the first real-catalogue search and explicitly initiates its held-out check with that exact choice. Exact-instance diagnostics and oracle scores do not measure perceptual quality. A06 is internal; D04 remains the first required user relevance review. Missing Loulou audio prevents a reference-specific experiment. Preserve benchmark exclusions, the A03 shortfall and existing resource ceilings.

The [source map](src/README.md) and [config map](config/README.md) describe ownership. Local audio, features, indexes, weights, run output, and secrets are excluded by [.gitignore](.gitignore). Keep sanitized manifests and shareable evidence reports versionable; see the brief before adding data.
