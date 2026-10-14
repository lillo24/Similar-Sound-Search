# Similar Sound Search

Select a particular sound inside a song and find passages in other recordings with a similar sound character, with playable results and trustworthy timestamps. Timbre comes first, approximate pitch second; matching phrase rhythm or note order is deferred.

**Current state: A06 local search and original-passage playback delivered.** The unchanged EfficientAT MN04 choice indexes all 72 available recordings over their full available durations: 44,025 passages across 3.098 hours. Single and unordered multiple-example queries return ten distinct recording candidates with parent duplicates excluded. [A06 evidence](reports/A06_SEARCH.md) records operation, costs and the single held-out check: 21/24 source-consistency query hits at rank one and 32/32 target events recovered within ten results. Human agreement remains unavailable; the broader A03 catalogue remains partial at 72 recordings/35 artists.

The first reference is **daoud — Loulou & the loulous**, approximately **3:38–4:00** in Leonardo's marked recording. The actual audio is still missing; recording version, excerpt offset, and exact event remain unverified. Engineering fixtures do not substitute for that reference. No new labels or manually discovered similar songs are required; the first required listening review is D04.

Open the delivered alternative engineering demo from this checkout with:

```powershell
.\scripts\listen-search.ps1
```

Visit `http://127.0.0.1:8766/`; Ctrl+C stops the listener. It verifies and serves only the owned report and original stereo clips. [Search setup, explicit queries and recovery](docs/SEARCH.md) cover missing local assets and finite cumulative allowances. Audio, weights and the completed index remain private on this delivery machine; Git does not restore them in a fresh checkout.

The fixed A06 compute allowance is consumed; opening the completed listening reports needs no new compute. An extra full-index repeat stopped at that cap. Later catalogue-page control required a Chrome extension update; earlier engineering browser playback checks passed. These limits are recorded in the evidence report.

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
- [Local search/playback commands](docs/SEARCH.md), [measured A06 evidence](reports/A06_SEARCH.md), and [search reproducibility records](manifests/search/README.md).
- [Measured A04 evidence](reports/A04_BENCHMARKS.md) and [frozen protocol](manifests/evaluation/protocol.json).
- [Initial reference manifest](manifests/references/loulou.json).
- [Archived A01 prompt](history-implementations/Similar_Sound_Search_A01.md).
- [Archived A02 prompt](history-implementations/Similar_Sound_Search_A02.md).
- [Archived A03 prompt](history-implementations/Similar_Sound_Search_A03.md).
- [Archived A04 prompt](history-implementations/Similar_Sound_Search_A04.md).
- [Archived A05 prompt](history-implementations/Similar_Sound_Search_A05.md).
- [Archived A06 prompt](history-implementations/Similar_Sound_Search_A06.md).

## A06 handoff

Follow [AGENTS.md](AGENTS.md) for implementation and GitHub delivery. Each implementation plan uses an isolated branch and a PR into `main`; checks, merge, and branch cleanup are part of completion. Reinspect current code and run the [complete local validation](docs/RUNTIME.md#validation) before extending the pipeline.

A06 integrates the frozen A05 choice through A02 preparation, A03 original validation and A04 scoring. Exact ranking, saved-query reuse, bounded resumable shards and verified original playback are implemented. Controlled held-out results and pipeline operation do not establish perceptual quality. This batch ends at A06; later stages need their own prompts. D04 remains the first required user relevance review. Missing Loulou audio prevents its reference-specific experiment. Preserve benchmark exclusions, the A03 shortfall and all lifetime ledgers.

The [source map](src/README.md) and [config map](config/README.md) describe ownership. Local audio, features, indexes, weights, run output, and secrets are excluded by [.gitignore](.gitignore). Keep sanitized manifests and shareable evidence reports versionable; see the brief before adding data.
