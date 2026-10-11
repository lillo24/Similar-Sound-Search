# A01 — Target and success definition

Implement A01 for **Similar Sound Search**. Make the actual repository changes, verify them, and report back. This standalone handoff covers **A01 only**; A02 onward will be supplied separately. Ending this task at A01 does not introduce a listening or approval gate into the roadmap.

## Repository and current evidence

Canonical repository: https://github.com/lillo24/Similar-Sound-Search

Inspected on 11 October 2026: `main` at `a9626d26874cfcd45333ce2c9e897b3f2ad68dce` contains only a short `README.md` describing the intended sound-selection and search pipeline. No application, processing pipeline, tests, or validated retrieval results were present in that inspected branch. No `AGENTS.md` or `implementation_plan_sections_suggestions.md` was present there.

Reinspect the actual checkout before acting: it may now contain newer commits or uncommitted work. Current repository evidence takes precedence over this snapshot when describing what exists. Keep implemented behavior, adopted design, tentative proposals, and experimental results distinct.

## External context and dependencies

The adopted context required for A01 is included below. Do not assume access to this conversation, ChatGPT Project uploads, or a connected Google Doc.

- **Google Doc:** “Similar Sound Search”, https://docs.google.com/document/d/14YC-w8eGEEj8eKTKCx7Fn8L3bOMNx1bjRdPjW1TRR-s . Relevant sections are “Direction — sound type first”, “Roadmap v2 — Plan index”, and “Autonomous build & evaluation”. These provide design context, not implementation evidence. Consult them if accessible; their absence does not block A01.
- **Reference audio:** daoud — *Loulou & the loulous*, approximately **3:38–4:00** in Leonardo’s marked recording. The actual source file, version, excerpt offset, and exact target event must be verified from available audio in later input work. No source path or audio attachment is guaranteed by this prompt. Audio is **not required to finish A01**.
- **Datasets, model checkpoints, hardware, and credentials:** no downloads, external credentials, or model execution are required for A01. A02 inspects runtime and inputs; later stages establish permitted catalogue and benchmark access.

If an external item is unavailable, record precisely what is missing and continue independent work. Any later substitute must be labelled as an engineering test and must not be reported as an evaluation of the intended Loulou reference.

## Adopted product direction

The goal is to select one particular sound inside a song and find passages in other recordings containing a similar sound character, with playable results and trustworthy timestamps.

Similarity priorities:

1. **Timbre first:** texture, harmonic/noisy character, attack, decay, and internal modulation of the selected sound. Leonardo describes the first target as electronic-sounding; its instrument identity is unverified.
2. **Approximate pitch second:** roughly compatible pitch can help, but exact notes are unnecessary. Pitch preference must remain separately inspectable, with tolerance to be tested.
3. **Phrase rhythm later:** matching the original rhythm, melody, or note order is not required. The way an individual sound starts, evolves, and fades still matters.

One complete note/event or several examples of the same sound in any order are candidate query forms. Treat these as options to test. The target should remain identifiable among surrounding instruments; whole-song mood, genre, or recording identity are insufficient substitutes for this goal.

The intended pipeline uses pretrained audio representations compared with a simpler acoustic baseline. Start with original audio; optional separation on queries and candidate passages is a later experiment whose value must be measured. Do not assume that every audible source can be cleanly separated. Custom training is conditional future work.

The implementation agent handles catalogue collection, published benchmark reuse, controlled test generation, model comparison, indexing, debugging, and packaging. Leonardo must not have to discover similar songs or create a labelled dataset beforehand. His first required listening review is **D04**, after the complete prototype works and has been automatically tested.

Resolve routine technical decisions autonomously. Default to available local resources and no new paid services. Record indispensable missing inputs or resource commitments after completing independent work. Preserve original audio, track permitted use and provenance, and exclude private audio and secrets from version control.

## Work to complete

### 1. Establish the repository foundation

Inspect the working directory, Git status, remotes, and applicable repository instructions. Work in the existing checkout of the canonical repository. If no checkout exists, clone that repository into the authorised workspace rather than creating a disconnected replacement project. Preserve unrelated changes.

Read `implementation_plan_sections_suggestions.md` if it has since appeared in the repository or supplied task context. Its sections are suggestions, not a mandatory template.

Prefer a Python audio-processing core unless current repository evidence gives a reason otherwise. Record the choice as a foundation decision; runtime setup belongs to A02. Establish sensible locations for code, configuration, manifests, local audio, features, and reports without creating a pretend application or unnecessary abstractions.

### 2. Persist the brief and roadmap boundaries

Write durable project context so later sessions can work without this conversation. Include the target, similarity priorities, autonomy rules, unknowns, and evidence categories above.

Preserve the adopted stage identifiers and dependencies:

| Stage | Scope |
| --- | --- |
| A01 | Target and success definition; repository foundation |
| A02 | Runtime, inputs, and resource limits |
| A03 | Automated starter catalogue |
| A04 | Benchmarks and controlled test generation |
| A05 | Candidate matchers and comparison harness |
| A06 | First complete search baseline with playable passages |
| B01–B03 | Event selection, optional separation, reusable queries, and pitch preference |
| C01–C04 | Passage/stem indexing, candidate retrieval, refinement, and resumable processing |
| D01–D04 | Interface, automatic evaluation, runnable package, then first listening review |
| E01–E03 | Broader catalogue sources, measured optimisation, and maintenance |
| F01–F03 | Conditional learned ranking, representation fine-tuning, and future rhythm target |

A06 is a runnable baseline and an internal evidence report; D04 is the first required user relevance review. Do not silently renumber stages or turn reference selection, training, or manual labels into new prerequisites.

### 3. Define reference and result records

Document a practical record contract, with illustrative examples if useful. Executable storage or retrieval code is not required in A01.

Reference records should cover recording identity, source/provenance, actual available file, content hash, full-track versus excerpt status, requested and verified intervals, selected events, processing history, and mapping back to source time.

Result records should cover source recording, matched interval, timestamp basis, original passage for playback, representation/model version, processing lineage, and ranking score meaning. Scores are not calibrated probabilities unless independently established as such.

Represent unknown information explicitly. An excerpt with an unknown original offset uses excerpt-relative timestamps. Keep requested timing distinct from verified timing, and do not apply a full-track crop offset twice to an existing excerpt. The initial Loulou record can remain unverified with no file path or hash.

### 4. Write the evaluation contract

Define observable checks and the claims they support:

| Check | What it can establish |
| --- | --- |
| Agreement with published human timbre judgments | Perceptual ranking agreement within the evaluated data |
| Same source/preset playing different phrases or nearby pitches | Controlled source consistency despite those changes |
| Contrasting sounds playing the same notes | Whether note similarity overwhelms sound-character differences |
| Known targets inside mixtures at known times, including absent-target cases | Candidate retrieval, localisation, and distractor behavior in controlled mixtures |
| Indexing, source mapping, and original-passage playback | Technical correctness of the search workflow |
| Later listening judgments on real recordings | Whether returned candidates match the intended sound character |

Generated examples provide known sources and locations, not independent perceptual labels. Same-preset identity is a useful proxy rather than proof of identical perceived timbre. Transformations can change the sound character. Retrieving the reference recording or its copies is a diagnostic, not successful discovery.

Keep real-song discovery audio, generated diagnostics, and human-rated evaluation data distinguishable. Do not claim arbitrary-catalogue recall from top-result judgments or controlled tests. Measure candidate retrieval separately from refinement: a reranker cannot recover a passage absent from its shortlist.

### 5. Define model-selection discipline

Separate development and held-out evaluation by source recording or instrument/preset identity as appropriate; keep related crops and transformations together. Record possible leakage, including unknown pretrained-model training overlap.

Specify technical correctness requirements now. Any numerical quality threshold must have a stated basis and be set before inspecting comparison results; do not invent a universal timbre-accuracy target. Keep final held-out checks separate from iterative tuning.

Distinguish technical test success, benchmark performance, and human relevance. The matcher's own scores do not independently validate quality. Unrun experiments remain unrun; unavailable evaluation data does not become a request for Leonardo to create labels.

### 6. Create concise, durable records

Use existing conventions, or create equivalents of:

- `README.md`: project purpose, actual current state, and where to resume.
- `docs/PROJECT_BRIEF.md`: adopted goals, scope, and operating rules.
- `docs/EVALUATION.md`: evaluation categories, evidence limits, and selection discipline.
- `docs/DECISIONS.md`: decisions with reasons and unresolved assumptions.
- `docs/STATUS.md`: stage status, completed evidence, and readiness for A02.

Place the record contracts where they fit best rather than duplicating them across documents. Add appropriate Git exclusions for local/private audio, weights, caches, and secrets, while keeping useful manifests and reproducibility records versionable. Paths above are suggestions if newer conventions exist.

## Verification and final handoff

Review the resulting diff for consistency, preserved existing work, clear stage boundaries, and observable outcomes. Confirm that missing audio or new user labels do not block A01. Do not write tests that merely assert document wording or run unrelated application tests for a documentation-only foundation.

Finish with a concise report containing the repository location and inspected revision, files changed, decisions and reasons, verification performed, unresolved assumptions, and readiness for A02. Explicitly distinguish foundations created from capabilities implemented or experimentally validated.

Complete **A01 only**. Leave the project ready for the separate A02 prompt.
