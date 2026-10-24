# Local Sound Search (D01)

From the repository root on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-sound-search.ps1
```

Open **http://127.0.0.1:8774/**. Keep this foreground terminal open; Ctrl+C stops
admission and waits for its own bounded worker. Port conflicts fail explicitly.
Python 3.12 and the existing pinned `.venv`/model are required; no additional package,
service, account or download is installed. Other platforms can use
`python -m similar_sound_search.application --root . --port 8774` with the pinned
environment. Only the actual Windows environment is claimed when exercised.

## Workflow and timing

Import a file through the browser picker; the app copies only those explicit bytes
into private D01 storage, validates format/full sequential decoding through A02/B03,
and reports actual rate/channels/length. Filenames are display text. Provenance,
rights, intended layer and version/master alignment remain unknown unless supplied.
An extension alone is never validation. Imports do not enter discovery.

Select integer half-open native frames with waveform edges, keyboard sliders or
numeric fields. The reduced min/max waveform and browser playback clock are
previews. Selected and context bounds remain separate; original event/context are
each at most thirty seconds. Add one to eight examples, including disjoint intervals
or multiple registered sources. Save a named immutable B03 recipe revision, then
search. Reordering and repeated selected PCM add no weight; all contributing parent
exclusions survive deduplication. Edits require the prior selected revision; renames
require the name record hash. Historical B03 names/heads are read-only.

Default policy is original mixture, legacy mean, pitch off. Event-multi is experimental.
C03 refinement is available only for the exact original Loulou/C01/C02/C03 chain.
Unsupported pitch/transforms/automatic selection/new-query refinement are unavailable,
not ignored. Loulou remains its full 218..240s selection, frames 9,613,800..10,584,000
at 44.1 kHz, with 217..241s context and the pinned original revision/materialization.

Every result keeps all eligible groups, twenty shortlisted and at most ten displayed.
Legacy distances are lower-better; event credits higher-better. Players use the
selected result's actual native representative and a separate unscored context.
Additional retained passages remain distinct. These are candidate matches, without
a confidence percentage or measured perceptual-quality guarantee.

## Ownership, admission and failure

`config/application.json` and `manifests/application/protocol.json` fix D01 roots and
one pool `data/runs/application/pool.json`. Limits are 3,600 worker seconds, 256
workers, 90,000 full-source read seconds, 1,024 new query/fixture rows, 6,000 feature
seconds, 32 MiB features, 64 jobs, 64 clips/128 MiB clips, 128 MiB metadata, 64 MiB
preparation/waveforms, 128 MiB imports and 512 MiB managed output. No catalogue
expansion/embedding is authorized. All retries, failures and UI work share it.

Ordinary metadata cannot exceed **96 MiB**. At least **32 MiB** is protected for
terminal/recovery bookkeeping. Whole-path geometry reserves groups, adoption/scoring,
state transitions and finalization before request admission; larger example sets
receive a larger estimate. Every actual publication debits serialized destination
plus atomic temporary and overhead before writing. Pool replacements are bounded
and counted. A bounded 256 KiB protected slot precedes each attempt, including success/failure,
journal, settlement and recovery. Terminal publication calls no ordinary writer.
Failed writes retain charges/temporaries. Logical unspent allocations can be released;
actual writes and unobservable worker reservations cannot be refunded.

The original delivery estimates undercounted new score/progress serialization. Both
blocked requests retained truthful protected terminal state and all prior charges;
each received one prospectively declared 8 MiB remaining-path allocation from this
same pool. The corrected estimator now budgets 512 KiB per source plus bounded
group/control geometry before a fresh search. It can refuse another full search
when the remaining ordinary allowance is too small; existing completed results stay
readable. No ceiling, failed-attempt charge or C04 reservation was changed.

The initial 40 MiB acceptance hold protects required finalization/warm/UI work from
exploratory requests. Each worker has a 120s actual-PID deadline, one numerical thread,
1 GiB numerical working limit, 256 MiB input/decoded/output, and the starter 4 GiB
managed/free headroom. Server memory and worker overlap are measured separately.
Status/playback never triggers hidden inference. MP3 validation charges full sequential
source reads. Cache validation checks bytes/PCM/hashes, never mtime alone.

An OS lock probe distinguishes an active owner from an old lock file. Stale running
records are shown as interrupted, with last durable state separately visible. Resume
only when the owned coordinator/worker stops; committed sources/scores are freshly
audited before remaining work. A journal replays settlement idempotently. If elapsed
time cannot be observed, the complete worker reservation remains charged. An all-write
filesystem refusal raises **PersistenceError**; observed stopped state does not claim
that an impossible durable error write succeeded.

Finalization recovery is explicit: the original recovery freshly hashed all source
bytes and reopened every array. The later new-query recovery reopened candidate
arrays, freshly validated query materialization and independently checked all
committed score supports against those arrays, retaining earlier full PCM proofs.
That latter mode does not claim another full original-source scan. It admits only
remaining media/publication units; a normal warm search still reads all originals.

C04 stays historical **partial 145/148**, including its pool, pending 120 seconds,
orphan groups and fixture last-complete. D01 publishes its own complete result only
after adopted dependencies, bounded aggregation, C03 audit where compatible and
media commit. No historical record is rewritten or re-embedded.

## HTTP/API and D02 handoff

Python operations are in `similar_sound_search.application.api`; synchronous bounded
orchestration is `job.run(root, limits, job_id)`. HTTP uses the same operations through
an independent coordinator thread. POST `/api/submit` accepts `{kind,input,request_id}`;
stable request IDs are durable and conflicting retries fail. Search input is
`{query:{historical,revision,materialization},arm}`. `materialization:null` means
materialize that immutable new revision once; its committed exact receipt is used by
later units. Other kinds: register, copy-reference, save, rename, preview, validate,
and metadata-preflight. Upload is explicit bounded POST `/api/upload` with content
length, an opaque upload ID and display filename. Inputs never accept shell commands,
remote URLs or arbitrary filesystem reads.

Inputs to `/api/submit` use these stable operation shapes (all IDs are opaque SHA256
except the client request ID). Each operation returns a persisted job, then an
operation result with `output` after completion:

| Kind | `input` |
| --- | --- |
| `register` | `{upload_id,label}` after explicit upload; produces asset and waveform references |
| `copy-reference` | `{revision}` for an available original/pitch-off historical B03 revision |
| `save` | `{label,examples}`; editing adds `{query_id,expected}` with the prior selected revision |
| `rename` | `{query_id,expected,label}` with the current name record hash |
| `preview` | `{asset_id,bounds:[first,last]}` in source-native half-open frames |
| `search` / `validate` | `{query:{historical,revision,materialization},arm}` |
| `native-qa` | `{job_id,start}` for two displayed cards of a completed acceptance result |
| `metadata-preflight` | `{}`; metadata-only generated population rehearsal |

Each `examples` item uses B03's validated `{asset_id,event,context,selection}` original
recipe input; provenance/uncertainty and all-parent exclusion rules are in
[QUERIES.md](QUERIES.md). `GET /api/revision/<id>` returns the exact `revision`,
resolved `materialization` when ready (otherwise null), and immutable `version`.
Creating a new materialization is an explicit charged job, never a side effect of
that GET. Save/rename conflicts are errors, not last-writer-wins edits.

GET `/api/bootstrap`, `/api/job/<id>`, `/api/result/<id>`, `/api/revision/<id>` and
`/api/waveform/<id>` are read-only. POST `/api/cancel` and `/api/resume` take job ID
and stable control request ID. States include pending/running/in_progress, cancelled,
interrupted, blocked, failed and complete; cancellation stays pending while owned
work continues. Closing/reloading a tab keeps the immutable request and accounting.
Reopening a completed result is separate from submitting a fresh validation search.
During an owned operation, import/query/selection/policy controls are disabled and
waveform drags are ignored. Cancel/status remain available; this preserves the
active job binding and prevents a second preview/import from replacing it. Controls
reopen when the bounded operation reaches a terminal state.
The completed-search selector also works in a fresh browser: bootstrap lists at most
64 complete search/validation jobs with their resolved revision, materialization and
policy. Selecting one validates and reads that publication without a worker or pool
write. It remains available when the finite allowance cannot admit another search.
Resume acknowledges a protected durable pending state before returning HTTP 202,
so the next poll cannot mistake the previous terminal state for the resumed outcome.

`d01-result-1` binds job/query/selection/policy/snapshot/arms/cards/chain/resource owner.
Groups use a bounded lossless `d01-packed-group-1` storage codec behind `Context.get`;
decoded numerical values/order are identical to the existing C04 algorithm. Media
uses `d01-media-1`, semantic source PCM/bytes/native crop keys, exact PCM16 verification
and opaque `/media/<id>` preview routes. Result players use
`/result-media/<result-id>/<media-id>` and reject a clip outside that complete
query/arm/population/result, even if the clip exists in the semantic cache.
Both routes preserve range/MIME checks. The preserved verified C03
bundle is separately exposed at `/historical/`; it never substitutes for legacy cards.

Strict Host and Origin checks plus a local-session token protect every mutation.
Assets/media are allowlisted; traversal, symlink escapes, raw paths, directory listings,
cross-origin mutations and unsupported settings fail. Tokens never appear in public
evidence. A server restart rotates the token; refresh the page and explicitly resume
the saved job. Do not kill unrelated Python processes or remove old lock files.
Browser refresh/seek can close an idle HTTP connection on Windows. The request
boundary handles only peer abort/reset/broken-pipe exceptions as disconnected
clients; other I/O/domain failures remain explicit. This performs no job operation.

Deterministic isolated tests in `tests/test_application.py` expose ordinary exhaustion,
filesystem/publication failures, scalar/native ranking and media bindings, recipe
deduplication/optimistic conflicts, HTTP isolation and recovery fixtures. These can
drive D02 technical automation without claiming human sound-similarity truth.
D02 evaluation, D03 packaging and the first D04 listening review remain future work.
## D02 evaluation provider

The optional trusted Python `runtime` argument in the application API/server is
used by `sound_search_evaluation.runtime.Runtime` on 8775. HTTP clients cannot
select or supply a provider. `runtime=None` retains the historical application
owner, inputs and port-8774 launch route. D02 supplies genuine generated source,
index, query and membership records; [ASSESSMENT.md](ASSESSMENT.md) owns that finite
population, its pool and commands.

The exact scoped D02 source declaration accepts only its pinned five application
seams and inherited numerical hash. Historical producer/consumer declarations are
retained; unknown source drift still fails. `/api/result` and result-bound media
continue to require the exact complete query/arm/population publication. The D02
report has a separate immutable own-root allowlist at `/evaluation/` and cannot
serve arbitrary workspace paths or substitute C03 for controlled results.
