# Evaluation subsystem

This folder owns A04 benchmark inputs, construction truth, frozen splits and scorers. It shares bounded decoding/preparation/storage and the catalogue transport, while keeping its artifacts and durable allowances separate. A05 representations live in the separate `matchers/` subsystem; no retrieval index is implemented here.

| File | Responsibility |
| --- | --- |
| `__init__.py` | Evaluation artifact semantics version included in reuse identity |
| `artifacts.py` | Recipe/tool-addressed audio, deterministic atomic writes, full decode/hash reuse, bounded records and conservative construction charges |
| `published.py` | Pinned Grey1977 inspection, explicit stimulus order, raw matrix/mask preservation, unique-pair extraction and quarantine |
| `rendering.py` | Four procedural mechanisms, balanced performances/pitches and insertion/active-interval mixing algebra |
| `protocol.py` | Family assignment before rendering; A03 duplicate/artist ancestry; frozen conditions, metrics, K and revised A05 selection rule; validates the authoritative atomic comparison pair |
| `suite.py` | Render/mixture orchestration, read-only real-background consumption, independent emitted-audio audit and A02 mapping diagnostics |
| `scoring.py` | Signed average-rank correlation, prediction validation, separate candidate/refined lists, one-to-one event coverage and known-answer runs |
| `job.py` | Finite policy, one locked hard-deadline worker, separate durable A04 transfer/time/construction accounting and CLI dispatch |

The parent CLI holds `.a02.lock`; children hold `.a04-worker.lock`. `catalogue.ingestion.validate_local_ready` validates the four consumed local backgrounds without opening or writing the exhausted A03 acquisition ledger. `catalogue.transfer.fetch` keeps its Archive-only default and exposes one explicit pinned raw-GitHub policy for benchmark inspection.

See [commands and protocol](../../../docs/EVALUATION.md#a04-delivered-commands-and-protocol), [records](../../../docs/RECORDS.md#a04-evaluation-records), and [measured evidence](../../../reports/A04_BENCHMARKS.md).
