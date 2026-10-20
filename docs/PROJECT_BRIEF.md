# Project brief

Adopted on 11 October 2026 for A01. This is a design brief, not evidence that the search works. [STATUS.md](STATUS.md) records implemented and tested capabilities.

## Goal and reference

Find passages in other songs that contain a sound like one selected element of a reference recording, even among overlapping instruments. Return the source recording, the matching interval, and playback of the original passage. Whole-song genre, mood, or recording recognition does not establish success.

First reference: **daoud — Loulou & the loulous**, approximately **3:38–4:00 (218–240 seconds)** in Leonardo's marked version. "Electronic-sounding" describes his impression; instrument identity is unverified. B03 technically registers the supplied 243.586667s MP3 and preserves its full available-file 218..240s mixture. Recording identity, marked-version alignment, master offset, rights and intended layer remain unverified. The [initial reference manifest](../manifests/references/loulou.json) retains its historical unknowns; [separate current availability](../manifests/queries/loulou-availability.json) records the supplied file without inventing marked-version evidence.

Tom's Diner's "Thhh" vocal sound is a possible later generalisation example from the design notes. Its audio is not supplied or verified here; it does not replace the Loulou reference or add an A01 prerequisite.

Input update, 20 October 2026: main now supplies the root MP3 named
`SpotiDownloader.com - loulou & the loulous - daoud.mp3`. B03 owns separate registration
and availability evidence; the initial reference manifest and earlier reports remain
historical. File availability does not verify its marked version, external master
alignment, rights, intended layer or complete event boundaries. Use validated native
available-file coordinates through [the reusable-query contract](QUERIES.md).

## Similarity priorities

1. **Timbre first:** texture, harmonic/noisy character, attack, decay, and internal modulation of the selected sound.
2. **Approximate pitch second:** roughly compatible pitch may help. Keep the pitch preference separately inspectable; its useful tolerance is an experiment, not an adopted numerical rule.
3. **Phrase rhythm later:** matching melody, rhythm, or note order is unnecessary for the first build. Preserve the evolution of an individual event, including its attack and decay.

A06 supports an explicitly selected complete event or a bounded unordered collection of examples through local files/crops. Identical examples deduplicate; mean per-example distance is order-invariant. Automatic event/layer selection remains future work. A05 compared original-mixture pretrained representations with a simpler acoustic baseline. Optional separation must earn its cost through measured retrieval improvement, retaining original audio for playback. Clean separation of every source is not assumed. Custom training and rhythm search belong to conditional future work.

## Autonomy and resources

The implementation agent handles permitted catalogue collection, published benchmark reuse, controlled test generation, matcher comparison, indexing, debugging, and packaging. Leonardo does not need to discover similar songs, prepare labels, or approve routine technical decisions. The first required listening review is **D04**, after the complete prototype works and has been automatically tested. A06 produces internal evidence without a listening gate.

Default to available local resources and no new paid services. A02 establishes compute, disk, dependency, and run limits before expensive experiments. Locate available inputs and complete independent work before reporting an indispensable missing input/access decision or a resource commitment outside the agreed budget. Missing Loulou audio does not block A01 or unrelated engineering tests; a substitute must be labelled as an engineering test, never as validation of the intended reference.

Keep original audio unchanged. Record provenance and permitted use; metadata access alone does not provide analysable song audio. Preserve private audio and secrets locally, and sanitize manifests/reports before versioning them.

## Roadmap and dependencies

| Stage | Scope | Dependency or milestone |
| --- | --- | --- |
| A01 | Target and success definition; repository foundation | Complete; documentation and workspace |
| A02 | Runtime, inputs, and resource limits | Complete; bounded CPU WAV/FLAC pipeline, see [runtime](RUNTIME.md) |
| A03 | Automated starter catalogue | Implemented; real bounded blocSonic acquisition, [partial catalogue evidence](../reports/A03_CATALOGUE.md) |
| A04 | Benchmarks and controlled test generation | Implemented; frozen controlled suite/harness, published data quarantined; [evidence](../reports/A04_BENCHMARKS.md) |
| A05 | Candidate matchers and comparison harness | Delivered acoustic/MN04 development comparison and provisional choice; [evidence](../reports/A05_MATCHERS.md) |
| A06 | First complete search baseline with playable passages | Delivered: all 72 local originals, 44,025 passages, explicit queries, original stereo playback, one unchanged held-out check; [evidence](../reports/A06_SEARCH.md) |
| B01–B03 | Event selection, optional separation, reusable queries, and pitch preference | Extends the baseline; measures query and separation choices |
| C01–C04 | Passage/stem indexing, candidate retrieval, refinement, and resumable processing | Uses reproducible queries; measures shortlist coverage before refinement |
| D01–D04 | Interface, automatic evaluation, runnable package, then first listening review | Integrates B/C; automatically tests before the D04 review |
| E01–E03 | Broader catalogue sources, measured optimisation, and maintenance | Expands the bounded prototype with explicit resource costs |
| F01–F03 | Conditional learned ranking, representation fine-tuning, and future rhythm target | Optional improvements after measured need; not prerequisites |

Dependent B/C/D engineering may interleave without changing identifiers or adding listening/approval gates. A01–A06 engineering is implemented; A03's catalogue and A04's published human evidence remain explicitly partial. A06's pipeline and held-out controlled results are separate from unmeasured human/Loulou relevance. This batch ends at A06; later prompts define their own work. The D04 goal is about ten distinct-song candidates, timestamps, direct playback, and an evidence report with optional feedback. Report weak or fewer candidates honestly rather than padding apparent successes.

## Workspace layout

| Location | Purpose | Version-control policy |
| --- | --- | --- |
| `src/` | Shared audio runtime, catalogue/evaluation/matchers and A06 local search; [source map](../src/README.md) | Source versioned; finite CPU workers and local listening reports |
| `config/` | Reproducible resource/input contracts; [config map](../config/README.md) | Versioned without secrets; `config/local/` and `*.local.*` ignored |
| `manifests/references/` | Reference records | Sanitized metadata versioned; initial Loulou record is unverified |
| `manifests/catalogue/` | Frozen source descriptors, ready identities, provenance, hashes, and duplicate groups | Sanitized records versioned; audio availability verified locally |
| `manifests/evaluation/` | A04 dataset versions, recipes, ground truth, family splits and frozen protocol | Sanitized reproducibility records versioned; audio remains local |
| `manifests/search/` | A06 declarations, full-file coverage, query/demo and browser evidence | Sanitized records versioned; private features/predictions/reports stay ignored |
| `manifests/private/` | Private paths, access details, or sensitive metadata | Ignored |
| `data/audio/` | Immutable catalogue originals, separate engineering fixtures and prepared bundles; later evaluation audio | Contents ignored except directory markers |
| `data/features/`, `data/indexes/` | Derived features and versioned-by-key indexes | Contents ignored except directory markers |
| `data/models/`, `data/runs/` | Model weights, raw run output, and temporary products | Contents ignored except directory markers |
| `reports/` | Shareable evidence summaries and selected reproducibility records | Versioned after privacy review; `reports/local/` ignored |
| `docs/`, `history-implementations/` | Durable context and archived task prompts | Versioned |

Remaining directory markers reserve later-stage locations. A02's runtime and A03's acquisition are implemented in source, with audio/raw source snapshots/ledgers generated privately. Git exclusions apply only to untracked files and are not a substitute for reviewing a diff before publishing.

## Context and evidence

The [archived A01 prompt](../history-implementations/Similar_Sound_Search_A01.md) is the task definition. The [Similar Sound Search design document](https://docs.google.com/document/d/14YC-w8eGEEj8eKTKCx7Fn8L3bOMNx1bjRdPjW1TRR-s), read on 11 October 2026, supplies "Direction — sound type first", "Roadmap v2 — Plan index", and "Autonomous build & evaluation". Its older Tom's Diner example does not override the explicit first Loulou reference in A01 and the v2 autonomous plan. No future session needs access to that document to understand this brief.

Keep four evidence categories distinct: **adopted design** (this brief and decisions), **tentative proposals** (query forms, models, separation, pitch tolerance), **implemented behavior** (supported by code), and **experimental results** (supported by a reproducible run). A01 establishes the first category and records proposals; it supplies no retrieval experiment.
