# Similar Sound Search

Select a particular sound inside a song and find passages in other recordings with a similar sound character, with playable results and trustworthy timestamps. Timbre comes first, approximate pitch second; matching phrase rhythm or note order is deferred.

**D04 listening review is ready; human response pending.**
The [standalone review report](reports/D04_LISTENING.md),
[immutable input](manifests/listening/d04-v1.json) and
[listening instructions](docs/LISTENING.md) retain the exact saved reference and
ten baseline candidates. Technical verification is recorded separately from
human relevance.

The versioned offline archive, installed launch command, private prerequisites,
finite runtime policy and technical evidence are in [D03_PACKAGE.md](reports/D03_PACKAGE.md)
and [package setup/recovery](docs/PACKAGE.md). Core 0.3.0 and the pinned numerical
dependencies are preserved.

The frozen 24-development/16-confirmation comparison completed on independent
generated performances. Event-multi improved event recovery but lost positive-group
coverage at twenty in both splits, so original mixture / legacy mean / pitch off
remain defaults. [D02 evidence](reports/D02_EVALUATION.md),
[machine-readable results](reports/D02_EVALUATION.json) and
[evaluation commands](docs/ASSESSMENT.md) retain every case and the failed gate.

Import a reference, select native
intervals, save one to eight examples, search the existing 72 recordings and listen
to exact scored passages with separate context. Original mixture, legacy mean and
pitch off remain defaults. [D01 evidence](reports/D01_INTERFACE.md) records real
adoption, warm/new-query searches and playback. C04 remains historically partial
145/148; A03 remains partial at 72 recordings/35 artists. Human similarity is unmeasured.

For the focused D04 review, run `powershell -NoProfile -ExecutionPolicy Bypass
-File scripts/listen-d04.ps1` and open **http://127.0.0.1:8777/** on the same
Windows computer. The separate companion uses exact saved clips and optional
private feedback, with no inference.

For the general product, start the installed D03 delivery in a foreground terminal:

```powershell
& "$env:USERPROFILE\Documents\Sound Search D03 à\installed\Scripts\python.exe" -I -m sound_search_distribution start --workspace "C:\SSS D03 à\w" --port 8776
```

Open **http://127.0.0.1:8776/**; Ctrl+C stops owned work. Choose **Open a completed
search** to reopen the original Loulou or generated two-example acceptance result
without spending more inference allowance. Fresh searches have finite admission
limits. D03 protects a separate normal-use share; the historical D01 allowance
cannot fund another full search. The old 8774 launcher remains available for its
saved results and preserves its original ledgers.
[Application setup, contracts and recovery](docs/APPLICATION.md) and the
[D02 interface](manifests/application/d02-interface.json) describe the product boundary.
Private audio, model and ignored B/C artifacts must already be available; a public
clone can run the isolated tests but cannot reconstruct the private catalogue.

The supplied **daoud — Loulou & the loulous** MP3 is now available and technically registered. B03 uses the complete **218..240s** available-file mixture; recording identity, marked-version alignment, master offset, rights and intended layer remain unverified. [Availability](manifests/queries/loulou-availability.json) preserves these distinctions and the historical missing-input record. The first required listening review remains D04.

Open the B03 query/revision demonstration from this delivery checkout with:

```powershell
.\scripts\listen-queries.ps1
```

Visit `http://127.0.0.1:8769/`; Ctrl+C stops the listener. [Query contracts, migration and commands](docs/QUERIES.md) cover saved revisions, explicit bindings, missing assets and finite allowances. Historical listeners remain on 8766/8767/8768. Local audio, weights, features and playback are not restored by Git in a fresh checkout; the previously supplied root MP3 retains its existing repository status.

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
- [Event selection/crop commands](docs/EVENTS.md), [measured B01 evidence](reports/B01_EVENTS.md), and [event declarations/results](manifests/events/README.md).
- [Query/revision commands](docs/QUERIES.md), [B03 evidence](reports/B03_QUERIES.md), and [query declarations/results](manifests/queries/README.md).
- [Measured A04 evidence](reports/A04_BENCHMARKS.md) and [frozen protocol](manifests/evaluation/protocol.json).
- [Initial reference manifest](manifests/references/loulou.json).
- [Archived A01 prompt](history-implementations/Similar_Sound_Search_A01.md).
- [Archived A02 prompt](history-implementations/Similar_Sound_Search_A02.md).
- [Archived A03 prompt](history-implementations/Similar_Sound_Search_A03.md).
- [Archived A04 prompt](history-implementations/Similar_Sound_Search_A04.md).
- [Archived A05 prompt](history-implementations/Similar_Sound_Search_A05.md).
- [Archived A06 prompt](history-implementations/Similar_Sound_Search_A06.md).
- [Archived B01 prompt](history-implementations/Similar_Sound_Search_B01.md).
- [Archived B02 prompt](history-implementations/Similar_Sound_Search_B02.md).
- [Archived B03 prompt](history-implementations/Similar_Sound_Search_B03.md).

## A06 handoff

Follow [AGENTS.md](AGENTS.md) for implementation and GitHub delivery. Each implementation plan uses an isolated branch and a PR into `main`; checks, merge, and branch cleanup are part of completion. Reinspect current code and run the [complete local validation](docs/RUNTIME.md#validation) before extending the pipeline.

A06 integrated the frozen A05 choice through A02 preparation, A03 original validation and A04 scoring. Its [historical evidence](reports/A06_SEARCH.md) retains the single held-out check and original missing-reference state; B03 separately updates availability and queries. Controlled results and pipeline operation do not establish perceptual quality. Preserve benchmark exclusions, the A03 shortfall and all lifetime ledgers.

The [source map](src/README.md) and [config map](config/README.md) describe ownership. Local audio, features, indexes, weights, run output, and secrets are excluded by [.gitignore](.gitignore). Keep sanitized manifests and shareable evidence reports versionable; see the brief before adding data.

## B01 handoff

B01 adds deterministic event proposals, explicit/manual native crops and an audited
read-only handoff to the existing matcher/catalogue. Automatic selection remains
experimental and explicit/coarse selection is default. The bounded comparison is
partial after a documented insertion-timing audit; it does not establish human or
Loulou relevance. Two actual catalogue searches and Chrome/HTTP playback checks passed.
Open the saved event/search report with `.\scripts\listen-events.ps1` on port 8767.
[B01 evidence and exact commands](reports/B01_EVENTS.md) own results, limitations,
resource/preservation proof and the concrete B02 handoff. That batch ended before B02.

## B02 optional processing

B02 adds original/HPSS/audio-cue processing with explicit transformation lineage,
finite accounting and paired development evaluation. Original audio stays default:
both processed roles miss the prospective retrieval/preservation gates. No learned
separator ran; controlled gains do not establish intended-layer or human relevance.
[B02 evidence and B03 handoff](reports/B02_SEPARATION.md) and
[commands/contracts](docs/SEPARATION.md) own the current scope and limits.
Open the saved comparison with `.\scripts\listen-separation.ps1` on loopback port 8768.
The B02 report preserves its historically missing Loulou input. B03 separately
registers the supplied file and retains version/offset uncertainty.

## B03 reusable queries

Use [the query CLI](docs/QUERIES.md) for save/show/revise/select/load/export/import and
exact search executions. The local report includes the original Loulou mixture,
unordered examples and the existing Donnie guided event with its contaminated cue.
Pitch .03 is an explicit experimental preference; timbre still selects every passage.
[B03 evidence](reports/B03_QUERIES.md) owns validation, outcomes, costs and recovery.
C01 catalogue-wide component indexing is the next handoff and is not started here.
