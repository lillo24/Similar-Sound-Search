# B03 reusable queries and pitch preference

B03 keeps original audio and pitch off as defaults. A named query points to immutable
revisions. A materialization binds a revision to validated local audio/features; an
execution additionally binds the exact index, complete timbre winners and pitch policy.
Display labels never identify content or execute shell/HTML code.

## Recipe, local bindings and availability

`queries register FILE` calls A02's full sequential inspection/registration, preserving
byte/PCM identity, native geometry, decoder/version evidence, provenance/context and
optional prepared-parent receipt. `--sha256` verifies an expected input hash. Explicit
files must be inside the project; no directory or disk search supplies substitutes.
The registration, portable asset identity and explicit local binding are separate.

Save `b03-query-input-1` with one to eight examples:

```json
{
  "schema_version": "b03-query-input-1",
  "examples": [{
    "asset_id": "ASSET_ID_RETURNED_BY_REGISTER",
    "event": [9613800, 10584000],
    "context": [9569700, 10628100],
    "selection": {
      "origin": "explicit approximate available-file region",
      "version": "b03-manual-native-1",
      "complete": false,
      "uncertainty": ["mixed reference; marked version/master alignment/intended layer unverified"]
    }
  }],
  "pitch": {"version": "b03-pitch-1", "weight": 0, "scale_semitones": 12}
}
```

These illustrative frames are 218..240s selected / 217..241s context at 44.1 kHz;
first validate the actual full available file and frame support. Never apply those
bounds to a short excerpt. Original event/context each permit at most thirty seconds.
Loading never redetects or changes the selected integer half-open native bounds.
Selection origin/version, completeness/overlap/censoring uncertainty remain explicit.

For an existing optional component, replace the original example with:

```json
{
  "transform_record": "data/runs/separation/processed/TRANSFORM_ID/record.json",
  "component": "extracted",
  "selection": {
    "origin": "explicit B02 event reuse",
    "version": "b03-b02-selection-1",
    "complete": false,
    "uncertainty": ["mixed cue; isolated layer and complete real note unverified"]
  }
}
```

The exact transformation receipt, source/cue byte/PCM hashes, method/settings/code,
output/component/map and event/context bounds are dependencies. Cues are not extra
retrieval examples. Missing source, parent, output or actual guided cue fails; no
experimental variant silently switches to original. B02 limits and allocation checks
still apply. A twenty-two-second original query is valid but cannot be processed by
changing its label or truncating its support.

Normalized `b03-query-recipe-1` embeds portable source metadata and processing choices,
canonical contributing selections and pitch preference. Its digest is the revision ID.
Exact repeated contribution records collapse, while distinct parent/selection records
remain. Feature aggregation uses unordered **unique selected PCM**, with every source,
duplicate and cue exclusion unioned first. Reordering/duplicates never add weight.

`b03-name-1` stores a display label, selected revision and revision history. Revising
requires `--expected` current selected revision; rename/select require the current
name `record_hash`. A separate process lock and atomic writes reject conflicting
updates. Labels are escaped display data. Immutable revision/artifact records refuse
different content; incomplete JSON/audio is preserved as a failure or interrupted state.

`show`/`list` inspect metadata without inference. `validate` reports ready, valid recipe
without materialization, missing, corrupt, incompatible or interrupted state, with
nonzero status for failed validation. `load` validates actual source/cue/selected media
and feature hashes before claiming reuse. `materialize` resumes the same revision;
an in-progress pointer does not hide the retained previous immutable artifacts.

## Reuse and transport

Feature blobs bind exact selected PCM/native dimensions and the frozen representation.
Labels, pitch preferences and source provenance do not alter that blob identity. A
pitch-only revision reuses the same underlying query/audio/features. Changed PCM or
preprocessing invalidates features. A changed cue/configuration invalidates a guided
transformation; byte-identical output PCM may still share a validated feature blob.
Its separate provenance/exclusion and execution identity remain distinct.

Reports select the execution's exact immutable materialization, even after an explicit
local rebind creates a newer materialization of that same portable revision. Query
validation can be shared within one report for identical immutable query hashes;
rendering uses the validated source samples instead of decoding the same file twice.
Player origins are independently derived again from original A02/B02 mapping receipts.

Materializations snapshot their exact local bindings; subsequent explicit rebinding
does not rewrite an earlier receipt/result. A relocation may create a new local A02
preparation/materialization while preserving the portable revision and PCM feature key.
Unchanged work still pays actual validation/source reads and worker time. Query pitch
estimates are calculated/cached during explicit materialization, even when ranking is
off; metadata-only naming/show/export operations do not calculate them.

`export` writes `b03-query-export-1` with the recipe and hashed dependency inventory to
the owned exports folder. No binding paths, audio, secrets, weights or features are
transported. `import` can install inspectable unresolved metadata. `--bindings FILE`
supplies a JSON object from dependency ID to explicit project-relative `path`, plus
`parent_record` when required. Every supplied binding is checked before publication:
same filename/different bytes, wrong parent/map and wrong cue/transform are errors.

Original assets can bind a different relative filename with exactly matching bytes,
PCM, metadata/context and parent receipt. Historical B02/A02 dependencies must retain
their receipt's full project-relative dependency layout in another checkout; bind the
exact unchanged receipt and restore that closure. Do not rewrite an old receipt to
disguise relocation. Missing closure remains unresolved/missing. No automatic media
search, bulk audio export, remote sync or destructive garbage collection is provided.

To migrate an A06/B01 query, register its original or prepared source with the matching
A02 context/parent receipt and copy its verified native bounds and selection origin
into a new recipe. Existing B02 variants instead bind the unchanged transformation
receipt/component. Keep old records intact; a saved feature path alone is not a recipe.
Unknown schemas require an explicit future migration and fail rather than guessing.

The `TransformContext` read-only adapter keeps the original B02 configuration/root and
validators but delegates all charges to B03. New `queries process INPUT --mode ...`
uses those same semantics with B03-owned output. Neither path invokes the B02 worker
or modifies its ledger. Current B03 index compatibility reuses `events.compatibility`
unchanged, writes a new consumer receipt and never re-embeds A06 arrays. Historical
`search/pitch.py`, `compatible_code`, protected functions and old proofs remain intact.

## Secondary pitch and complete winners

The only optional policy is `b03-pitch-1`, weight **0.03**, twelve-semitone scale;
off has weight zero. No sensitivity setting/sweep is admitted. Timbre still selects
one best scored native passage per original duplicate group, using the existing mean
per-example distance and stable ties. B03 retains **every eligible group winner before
top-ten truncation**, binding query, index/shards, exclusions, receipt and support.
Pitch only reorders that complete set, never selects a different passage or enlarges
coverage. A saved top ten alone is refused as a reranking intermediate.

The unchanged conservative estimator uses arithmetic channel mean, resampling to
8 kHz, stable narrow fundamentals roughly 50..500 Hz, and explicit abstention reasons.
Each estimate binds actual selected PCM, native support, estimator and preprocessing.
It is not a polyphonic tracker. Processed-variant estimates describe that waveform,
not an identified original layer. A conditioning cue contributes no pitch vote.

Contribution is `0.03 * mean(min(1, abs(12*log2(query_hz/candidate_hz))/12))` over unique
examples. Octaves are not folded. All required query estimates and the candidate must
be reliable; otherwise contribution is zero, visibly explaining uncertainty. The UI
shows timbre distance, pitch contribution and resulting score separately. For multiple
different notes even a candidate matching one note can incur a penalty; there is no
melody/intended-note inference. All-abstention ordering equals off. This is an
experimental preference, without calibrated relevance or a default-policy promotion.

## Windows operations and safe resumption

Global flags precede `queries`. Use the pinned environment from the repository root:

```powershell
.\.venv\Scripts\python.exe -m similar_sound_search --tier starter --report reports/local/b03-register.json queries register 'SpotiDownloader.com - loulou & the loulous - daoud.mp3' --context config/local/b03-loulou-context.json --sha256 2fc1256b1ac35134cfaef177aaf032277a0e375c676e50d391a1e3b22046ae30
# Fill INPUT_JSON with registered asset ID and validated native bounds.
.\.venv\Scripts\python.exe -m similar_sound_search --tier starter queries save INPUT_JSON --name 'Mixed reference'
```

Use that same executable/global prefix for the operations below; replace identifiers
with returned values and `--report` to retain each command's result:

```powershell
queries list
queries show --query-id QUERY_ID
queries show --revision REVISION_ID
queries rename --query-id QUERY_ID --name 'New display label' --expected NAME_RECORD_HASH
queries revise RECIPE_JSON --query-id QUERY_ID --name 'New display label' --expected CURRENT_REVISION
queries select --query-id QUERY_ID --revision EARLIER_REVISION --expected NAME_RECORD_HASH
queries validate --revision REVISION_ID
queries materialize --revision REVISION_ID
queries load --revision REVISION_ID
queries export --revision REVISION_ID
queries import EXPORTED_JSON --bindings LOCAL_BINDINGS_JSON
queries preflight
queries known-answer
# Commit exact verified geometry/protocol and producer before the one comparison.
queries compare
# Finish package code changes before the necessary delivery verification pass.
queries compatibility --index A06_INDEX_JSON
queries search --revision REVISION_ID --index A06_INDEX_JSON --receipt B03_RECEIPT
queries report REPORT_INPUT_JSON
queries verify-native reports/local/b03-report.json
.\scripts\listen-queries.ps1
```

Pitch is part of an explicit revision; copy the normalized recipe, set its pitch object
to the primary policy and `revise`, then materialize/search that revision. Search results
retain that exact revision even if a mutable name later selects another revision.
Reopening a previous revision reproduces its choices. Unchanged commands resume
bounded units with retained charges; producer drift refuses a replacement comparison.

The listener uses `127.0.0.1:8769`, validates media hashes/ranges/contained paths and runs
no inference. Ctrl+C stops it. Ports 8766/8767/8768 and historical listeners remain.
Candidate audio is always an original catalogue crop with native rate/channels, explicit
PCM16 gain and truthful available-file time; unknown master offset stays unknown.

## Finite accounting

`config/queries.json` fixes one offline ledger under `data/runs/queries`. Ceilings are
3,600 aggregate worker seconds, 256 workers, 90,000 source-read seconds, 1,024 features /
6,000 feature-audio seconds, sixteen query/rank jobs, 64 clips / 64 MiB and 256 MiB new
managed output. Transformation caps are 32 inputs / 240 input seconds; pitch analysis
is at most 3,600 seconds. Comparison is one batch / eight cases / sixteen arm queries.
New prepared/query/feature output is additionally bounded at 96/64/32 MiB. A fixed
16 MiB metadata envelope includes shared coordinators and atomic partials within the
overall managed reservation. Actual metadata publication is separately bounded.

Existing starter CPU/thread 1, 120s worker, 1 GiB working, 256 MiB I/O, 4 GiB combined
managed storage/free headroom limits remain. Combined inventory includes separation
and query public manifests. New namespaces cannot replenish old allowances; names,
restarts and policy increases cannot mint B03 credit. Source/parent/cue validation,
failed/interrupted workers, cold/reused processing, pitch, features, ranking, report
and native QA are charged. Setup/tests/non-inference preservation and browser/HTTP
engineering checks are recorded separately. No network, model acquisition or GPU is
required. Matching private inputs/index/checkpoint are required in a new checkout.

Read accounting retains the established whole-source validation-equivalent convention:
one full sequential decode, including its pre/post consistency hashes, counts the
source duration once. A separate original hash or parent validation counts separately;
every repeated decode is charged again. Successful workers retain measured peak working
bytes per action; interrupted/failed worker time and uncertain reservations remain
charged even where a peak measurement is unavailable.
