# Local application owner (D01)

`api.py` owns the stable import/query/job/result product boundary. `server.py` exposes
explicit POST mutations and read-only GET/status/media over loopback. `__main__.py`
and `scripts/start-sound-search.ps1` provide foreground startup and cooperative stop.
`web/{index.html,style.css,app.js}` compose the responsive Import → Select → Search →
Listen workflow with native selection, saved revisions and job reconnect.

`context.py` owns the one finite pool, whole-request admission and protected attempt
bookkeeping. `locks.py` owns OS ownership/probes; `files.py` retains failed atomic
temporaries. `job.py` coordinates serial actual-PID workers, useful immutable unit
commits and idempotent terminal settlement independently of HTTP handling.

`history.py` validates the pinned C04 partial chain and query-independent C01 bank
reader. `pipeline.py` calls the existing C04 scoring/aggregation and C03 validators;
its capture adapter publishes groups in bounded chunks. `codec.py` losslessly stores
bounded group payloads, preserving float values/order and full support. No older
consumer guard, source file, pool or producer identity is replaced.

`queries.py` adapts B03 validators/library/materialization into D01 roots. Shared
immutable A02 preparation remains content addressed; new receipts/bytes are charged
to D01. `media.py` owns reduced native waveform previews and exact PCM16 crops,
using the unchanged conversion and channel/gain rules. Media GET never decodes a
song, encodes a vector or charges a processing worker.

`validation.py` independently verifies native samples/channel/gain/endpoints and
audits already committed query/array/score outputs before bounded finalization.
Completed-search navigation in `api.py` is a metadata read, independent of admission.
On Windows `LoopbackServer` uses `SO_EXCLUSIVEADDRUSE` and disables address reuse:
the platform's ordinary reusable HTTP socket can otherwise accept a duplicate live
bind. Port conflicts fail before startup; other platforms retain normal reuse.

See [APPLICATION.md](../../../docs/APPLICATION.md) for contracts and recovery.

D02 adds a trusted optional runtime provider to `api.py`/`server.py`; HTTP request
data cannot select it. The default remains the D01 population/pool on 8774.
`queries.py` shares one lazy model across query owners and optionally adds actual
parent ancestry supplied by the owner. `context.py` records actual job IDs when
several jobs use a prepaid stage. `history.py` permits only the exact before/after
D02 scoped proof; D01 declarations and numerical modules stay pinned. The
[D02 subsystem](../../sound_search_evaluation/README.md) owns the generated inputs,
separate pool and 8775 evaluation listener.
