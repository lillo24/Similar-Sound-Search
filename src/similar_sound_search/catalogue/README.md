# Catalogue acquisition

This subsystem owns bounded discovery-audio acquisition and registration. It uses the existing input, preparation, storage and resource modules; it does not select sound events, score similarity, create benchmarks, or index features.

| File | Responsibility |
| --- | --- |
| `__init__.py` | Versioned ingestion semantics used in reuse identity |
| `transfer.py` | Verified HTTP(S), bounded streaming/retries/redirects, durable byte/attempt/time accounting and receipts; Archive-only default plus explicit pinned A04 GitHub rule |
| `source.py` | One Internet Archive adapter, frozen metadata/checksums/rights, deterministic genre/artist coverage selection |
| `ingestion.py` | Shared ingestion, immutable originals, A02 preparation, ready records and duplicates; read-only local-ready validation for bounded consumers |
| `job.py` | Validated finite policy, sequential bounded workers, resumable batch cursor, public/private manifest layout and summaries |

The CLI holds the project operation lock. Catalogue children also hold a worker lock, so an orphan child refuses a new operation before it can race the ledger. Each child uses the ordinary A02 hard deadline. Source selection and local ingestion feed the same decoder and derivative publisher. A catalogue job's ledger remains local and cumulative across invocations and explicit coverage revisions.

See [commands and recovery](../../../docs/CATALOGUE.md), [record contract](../../../docs/RECORDS.md#a03-catalogue-records-version-03), and [measured delivery](../../../reports/A03_CATALOGUE.md).
