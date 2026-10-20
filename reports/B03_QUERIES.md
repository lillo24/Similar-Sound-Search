# B03 — Reusable queries and pitch preference

20 October 2026. B03 implements immutable saved query revisions, explicit local
materializations and exact search executions. Original audio and pitch off remain
defaults. C01 is not implemented. Engineering reproducibility passed; the controlled
pitch check was neutral on source-family hits, and human/Loulou relevance is unmeasured.

## Scope and boundaries

The new `queries` owner composes A02 native preparation, unchanged B02 transformation
validators and audited read-only A06 search. It does not rebuild catalogue features,
redetect saved events, retune separation, acquire media/models, repeat held-out scoring,
add melody/rhythm/refinement, or implement a general cache service.

[Contracts, schemas and migration](../docs/QUERIES.md),
[source ownership](../src/similar_sound_search/queries/README.md) and
[public evidence map](../manifests/queries/README.md) define the interfaces. The
prospective policy/integration were committed at `59f079f`; implementation `14b637f`
preceded geometry/protocol commit `d8bac35`. The two-module execution repair was
declared at `8f74415` and implemented/checked at `6a06f05`, before real-query ranking.
Historical frozen adapters, `search/pitch.py`, distance/tie/exclusion functions,
configuration, receipts, predictions, held-out outputs and ledgers remain unchanged.

## Supplied reference and exact choices

The previously committed root MP3 is now technically available, rather than missing.
A02 registration verified SHA-256
`2fc1256b1ac35134cfaef177aaf032277a0e375c676e50d391a1e3b22046ae30`,
9,797,656 bytes, 10,742,172 finite frames / 44,100 Hz / stereo, 243.586667 seconds.
[Availability](../manifests/queries/loulou-availability.json) is separate from the
unchanged initial reference manifest and B02's historically correct missing-input report.
No compressed seeking was used: registration/materialization decoded sequentially.

The primary original mixture is **218..240s**, native half-open frames
**9,613,800..10,584,000**, with 217..241s context. The full 22 seconds were preserved;
no B02 processing or invented clean cue was applied. The unordered pair uses
218..220.4s and 220.4..222.8s. Recording identity, marked-version alignment, master
offset, rights, intended layer and complete-note status remain unverified. These are
available-file coordinates, never verified master timestamps.

The existing Donnie Ozone guided variant was saved/materialized/reopened through
B03-charged read-only validation: transformation
`4dda57f36c48eb6d1f3bca4b7a8ecda45a81a614e2dae1560d2d33ba42896739`,
component `extracted`, event 10..12.4s, original context 9..17s and actual contaminated
cue 12.4..14.8s. It remains a processed waveform with uncertain layer/completeness.
No second B02 three-arm catalogue experiment or historical worker was invoked.

| Choice | Immutable revision |
| --- | --- |
| original | `c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3` |
| pitch | `ee2515234ccbeb3726c882d44e7a21fea9d8a4563ecc63a5a115bc4d76b9b7b2` |
| multiple | `e42ee0e09abb80ac0fb0fe7f2a154313c2df61d2583e62890cb2b430a7bf899c` |
| guided | `9634093de562f30acca87e1a0947c33da77ae77e288bcc6c3e97468399cae9bf` |

Original and pitch-only revisions share underlying query
`40d72bd6548685be3da3be7c481ae369f8580291ef3e1d4955ec1f736389a6bb`. Their immutable materialization/execution receipts retain
the exact revision even after the mutable display head selects another revision.
[Delivery identities](../manifests/queries/delivery.json) supplies full hashes.

## Reproduction and binding

The portable schema `b03-query-recipe-1` owns asset identities, unordered contributing
example records and explicit pitch policy. An original example records `asset_id`,
native `event`/`context`, and selection origin/version/completeness/uncertainty. A
processed example records the exact transformation/component/output/map/configuration
and source/cue ancestry. Every contributing parent exclusion is unioned before unique
PCM examples are averaged. Labels, local paths and execution/index IDs are separate.

[Metadata-only original export](../manifests/queries/example-original.json) is a real
schema example, with dependency inventory and no audio/features/absolute machine paths.
Importing it on another checkout can remain explicitly unresolved. To execute, supply
an explicit binding JSON `{"ASSET_ID":{"path":"relative/source.mp3"}}` containing the
exact bytes and matching decoder/context/parent identities, then validate/materialize.
Historical B02/A02 closure relocation must retain its recorded relative layout;
never rewrite a receipt. Temporary tests reject same-name/different-byte media,
wrong parent/map/cue, missing media, corrupt features and partial/conflicting writes.
No disk crawl or substitute lookup occurs.

The delivery's ignored `config/local/b03-*.json` inputs and `reports/local/b03-*.json`
command reports remain in this checkout. [Actual exercised arguments and timings](../manifests/queries/commands.json)
are sanitized to project-relative paths. The delivery used these PowerShell command
forms; the two search examples explicitly select revisions rather than the mutable
name used in the exact recorded arguments:

```powershell
$py = '.\.venv\Scripts\python.exe'
$name = '5daaebfa5e4537832e87a4300bad04ef3f401856bc8fb2730a513525afbf7058'
$r0 = 'c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3'
$r1 = 'ee2515234ccbeb3726c882d44e7a21fea9d8a4563ecc63a5a115bc4d76b9b7b2'
$index = 'data/indexes/a06/d027f2cd5ca817bc320542df16a540346325403bcb967fd248216c8c466731e2/index.json'
& $py -m similar_sound_search --tier starter queries save config/local/b03-original-input.json --name 'Loulou supplied mixture 218..240s'
& $py -m similar_sound_search --tier starter queries show --query-id $name
& $py -m similar_sound_search --tier starter queries load --query-id $name
& $py -m similar_sound_search --tier starter queries export --revision $r0
& $py -m similar_sound_search --tier starter queries import "data/runs/queries/exports/$r0.json" --bindings config/local/b03-original-bindings.json
& $py -m similar_sound_search --tier starter queries revise config/local/b03-pitch-recipe.json --query-id $name --expected $r0 --name 'Loulou mixed reference - experimental pitch .03'
& $py -m similar_sound_search --tier starter queries materialize --revision $r1
& $py -m similar_sound_search --tier starter queries compare
& $py -m similar_sound_search --tier starter queries compatibility --index $index
$receipt = (Get-Content reports/local/b03-compatibility.json -Raw | ConvertFrom-Json).receipt
& $py -m similar_sound_search --tier starter queries search --revision $r0 --index $index --receipt $receipt
& $py -m similar_sound_search --tier starter queries search --revision $r1 --index $index --receipt $receipt
& $py -m similar_sound_search --tier starter queries report config/local/b03-report-input.json
& $py -m similar_sound_search --tier starter queries verify-native reports/local/b03-report.json
.\scripts\listen-queries.ps1
```

The recorded searches actually resolved `--query-id` after explicit `select` commands;
the equivalent `--revision` forms above avoid changing the delivery's current head.
`rename` and `select` used the current name `record_hash` for optimistic checks;
`revise` used the selected revision. `list`, `show`, `save`, `rename`, `revise`, `select`
and `export` perform metadata work without model inference. Import validates every
supplied binding before publication. Repeating the completed comparison reads saved
predictions; a new producer/plan is refused. Do not rerun finite delivery work casually.

## Verified invariance and development outcome

| Check | Feature attempts before | After | New features |
| --- | ---: | ---: | ---: |
| rename_restart_load | 24 | 24 | 0 |
| reorder_duplicate | 26 | 26 | 0 |
| pitch_only | 28 | 28 | 0 |

Rename/restart/load preserved original query/features; reordering and duplicating the
two inputs preserved the exact portable revision and materialized query. The pitch-only
revision reused the same original query/features with zero new feature attempts.
Export/import preserved revision identity and validated explicit source bytes. The
controlled direct/saved/reopened path matched feature rows, pitch-off distances and
candidate order exactly in **7/7 usable cases**; silence remains an explicit failure
with both failed arms retained in its separate diagnostic stratum.

[Prospective protocol](../manifests/queries/protocol.json) fixes one batch, eight cases /
sixteen arm queries, sixteen candidate groups, K=1/5/10, six primary and two diagnostic
cases. Independent saved-array FFT/projection/support checks preceded model comparison:
candidate event frames 7,200..64,800 and query frames 9,600..67,200 at 24 kHz.
Content-addressed identical signals share 23 actual files; two independent geometry
passes and their original auditor snapshots remain retained and charged. The second
pass only corrected script formatting and addressed output by source hash.

Families/harmonic envelopes are familiar inspected deterministic development material;
family identity is a timbre proxy, not human similarity. No A06 held-out repeat ran.
Off versus fixed .03 / twelve-semitone absolute-register preference yielded:

| Metric | Off | Primary pitch |
| --- | ---: | ---: |
| Primary source-family hit@1 | 4/6 | 4/6 |
| Primary source-family hit@5 | 5/6 | 5/6 |
| Primary source-family hit@10 | 6/6 | 6/6 |

Top-1 paired gains/losses were **0/0**. Five of seven usable complete rankings changed.
There were no primary paired losses at K=1/5/10. All candidate contributions independently
matched the declared formula and lay in [0,.03]. No sweep, sensitivity setting,
replacement case or post-ranking reference change followed.

| Case | Stratum | Query Hz (None = abstention) | Off / primary top-1 hit | State |
| --- | --- | --- | --- | --- |
| single-220 | primary | 222.2222222222222 | 1 / 1 | complete |
| octave-440 | primary | 444.4444444444444 | 1 / 1 | complete |
| single-261 | primary | None | 1 / 1 | complete |
| low-130 | primary | 131.14754098360655 | 0 / 0 | complete |
| multiple-registers | primary | 222.2222222222222,444.4444444444444 | 1 / 1 | complete |
| processed-mixture | primary | 222.2222222222222 | 0 / 0 | complete |
| noisy-chord | ambiguous_diagnostic | None | 1 / 1 | complete |
| silence | absent_diagnostic | unavailable | 0 / 0 | failed |

The processed-mixture case remained wrong-family at rank one. Pitch attracted the
222.22 Hz wrong-family candidate with timbre distance .166624 over the off winner
at .140581 / 444.44 Hz. This demonstrates a real timbre-order trade-off without a
source-consistency gain. The low-register case also remained wrong-family. A harmonic
261.6 Hz query and the noisy chord abstained, preserving their off ordering. The
multiple-register query explicitly kept both different notes, with .015 penalties at
either matching octave; no melody or octave folding was inferred.

## Pitch known answers and catalogue execution

The unchanged conservative estimator achieved **3/3** reliable known-answer tones:

| Truth Hz | Estimate Hz | Absolute cents error |
| --- | ---: | ---: |
| 110 | 109.589041 | 6.479985 |
| 220 | 222.222222 | 17.399484 |
| 440 | 444.444444 | 17.399484 |

Silence, white noise, a 220+330 chord and 880 Hz all abstained (4/4 expected abstentions).
These deliberately selected engineering checks do not establish polyphonic coverage.
The .015 multiple-note mean, zero missing-query contribution and hard bounds passed.
Pitch remains limited roughly to stable narrow monophonic fundamentals 50..500 Hz.

A single fresh B03-owned compatibility pass validated the original 72-file / 123-shard
A06 index, its checkpoint, representations, sources/groups and protected producer/math.
No catalogue embeddings were rebuilt. Both original saved-reference executions scored
**44,025 passages / 72 eligible groups**, returning
10 distinct original-mixture candidates each. They share the
complete timbre-winner set `c2c637201e78f8f74dc7292b74f9a5c2051820cb95b57c12f99a0b1aa09fae95` and exactly the same
native passages/distances. Pitch reranks that complete set before taking ten.

The real query pitch was **None**: ambiguous/polyphonic/unstable or outside 50..500Hz.
Primary candidate coverage was 3/72;
nonzero contributions were 0/72.
Same top-ten ordering between policies: **True**. Missing query
pitch contributes zero; no frequency was invented and no new reference was selected.
These results establish operation and reproducibility, not intended-layer or human relevance.

## Playback and preservation

Run `.\scripts\listen-queries.ps1`, open **http://127.0.0.1:8769/** and use Ctrl+C
to stop the loopback listener. It serves the owned bundle only, with no inference.
The bundle retains four exact revisions and two executions, original contexts/selected
examples, the actual Donnie cue/derived event, pitch reasons and separate score terms.
Original native catalogue crops retain truthful available-file timestamps and explicit
PCM16 playback-only gain; feature/processing gain stays unchanged.

Native verification: 32 player items checked
against original/derived bytes, native rate/channels/frames, independent PCM16 conversion,
gain, source/parent mappings and timestamps. [Delivery evidence](../manifests/queries/delivery.json)
records HTTP media/hash/range/containment and actual Chrome load/play/pause/seek outcomes,
including exact exercised player roles and any gaps. HTTP success alone is not playback proof.
All 32 controls passed native key-driven play/pause and explicit range seeking; every
media clock advanced by more than .05s while playing. All 18 unique HTTP media files
matched their bytes and MIME types; range/containment checks passed. Chrome initially
had a zero-sized layout, preventing interaction/screenshots. A temporary supported
1200x900 test viewport recovered it; the override was cleared and the owned tab closed.
The owned verification listener was stopped after QA; the command above starts it again.
Historical listeners/ports 8766/8767/8768 are preserved.

The pre/post audit covers **9,060 protected files / 1,256,651,270 bytes**, including prior
audio, index/features, manifests, ledgers, predictions/reports, prompts, frozen modules
and the supplied MP3. **9,059** retained byte/size/mtime identity; the sole predeclared
change adds query configuration to `config/README.md`. No unexpected change occurred.
New ignored records/features/playback stay under verified owned B03 paths; native
query crops retain shared immutable A02 `data/audio/prepared` bundle paths and are
charged to B03. These artifacts remain in the delivery checkout;
Git transfers code/metadata, not the private catalogue/checkpoint/features/playback.
[Retention evidence](../manifests/queries/retention.json) binds 436 verified ignored
delivery files / 43,563,460 bytes, including referenced shared native bundles. Their
hash inventory is checked again after Git cleanup. The test tab and listener were
closed, and the temporary viewport override was cleared.

## Costs, failures and verification

Fixed B03 charged worker time: **1128.016/3,600s**.
No pending worker/read reservation remains. Successful measured peak RSS/working set
was **297.262 MiB** under the 1 GiB worker ceiling. Per-action cold/reuse timing,
all reservations and ceilings are in [resources](../manifests/queries/resources.json).
Actual feature blobs: **26**; attempt counts additionally retain failures.

| Cumulative counter | Used | Ceiling |
| --- | ---: | ---: |
| metadata_bytes | 10,814,350 | 16,777,216 |
| clips | 18 | 64 |
| comparisons | 1 | 1 |
| workers | 94 | 256 |
| processing_inputs | 1 | 32 |
| managed_output_bytes | 73,250,336 | 268,435,456 |
| query_preparation_bytes | 26,454,656 | 67,108,864 |
| feature_bytes | 1,878,016 | 33,554,432 |
| read_audio_seconds | 68,829.157 | 90,000 |
| comparison_cases | 8 | 8 |
| processed_window_seconds | 86.800 | 6,000 |
| preparation_bytes | 7,674,880 | 100,663,296 |
| pitch_audio_seconds | 374.400 | 3,600 |
| feature_windows | 28 | 1,024 |
| separator_input_seconds | 2.800 | 240 |
| comparison_queries | 16 | 16 |
| query_jobs | 15 | 16 |
| clip_bytes | 20,465,568 | 67,108,864 |

The first model comparison failed before any query predictions because two feature
consumers initialized the frozen adapter in one process. PyTorch's interop pool may
be configured only once. The prospective execution repair shared one unchanged model
per B03 worker, persisted progress before work and recovered unique pending case/arm
reservations. Sixteen candidate feature blobs and every original charge were verified
and retained; the explicit bootstrap did not mint a second batch. See
[declaration](../manifests/queries/execution-repair-plan.json) and
[checked producer](../manifests/queries/execution-repair.json).

Windows commit exhaustion caused initial offline-test failures and later interrupted
the same comparison after five completed predictions. A separate non-inference Torch
documentation import also raised MemoryError. Memory recovered without changing OS
settings, dependencies or other applications. The same pending sixth case resumed,
preserving all predictions/charges; the batch finished with its original 8/16 counters.
Silence's explicit domain refusal is the only completed-batch failed case. No failure
was replaced or hidden. Failed-worker peaks are unavailable where execution stopped.
The first real guided materialization also reported the CPU backend error
`could not create a primitive`. An unchanged retry of the exact same validated
revision succeeded; both attempts remain charged. No backend, descriptor, audio or
model setting was changed, and the original failure's underlying cause is unverified.

The final full offline suite passed **218 tests** (189 unchanged earlier tests plus 29
B03 tests), with single numerical threads; unittest time was 125.711s. Ruff lint and
format passed across all source/tests plus the independent geometry script (99 files).
Pinned offline editable install, `pip check`, package/CLI checks and isolated starter
smoke passed. No dependencies/global packages/driver or model changed. All offline
tests use disposable roots/fake features; delivery ledgers were used only by the
explicit integration commands. Windows is the exercised platform; Linux regression
was not rerun here. No hosted CI is configured or claimed; PR checks/status/reviews
and latest main are verified separately before merge.

## Concrete C01 handoff

1. Start a new isolated plan/branch from merged main and inspect current `queries`,
   B02 transformations and the read-only A06 compatibility contract. B03 ends here.
2. Keep portable revision/materialization/execution identities separate. Every proposed
   catalogue component needs B02-style source/config/output/map/cue provenance and all
   parent exclusions; a processed waveform is not an unchanged A02 crop.
3. Treat the 72 originals / 44,025 original passages / 123 shards as immutable. The
   current audited receipt authorizes this B03 producer only; a C01 consumer needs a
   fresh declared audit and a separate fixed budget before any new component work.
4. Verify exact delivery-machine source/cue/checkpoint/index availability. Public JSON
   does not transfer them. The supplied Loulou file is decodable, while identity,
   alignment, master offset, rights and layer remain unverified. Donnie's cue remains
   contaminated and its guided output experimental.
5. Prospectively bound catalogue-wide component counts, storage, CPU/read/worker cost
   and duplicate/result support. Do not replenish B03/B02 or repeat closed comparisons.
   Preserve original/off defaults, full winner support and truthful original playback.
6. Retain development exposure, quarantined Grey1977 human evidence and the partial
   A03 target. Human similarity/Loulou relevance remains unmeasured; D04 is the first
   required listening review. No new labels are requested by this delivery.
