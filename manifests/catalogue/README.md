# Discovery catalogue records

This folder owns sanitized source selection, provenance, identities and duplicate relationships for real discovery audio. Audio and private access/runtime state are excluded from Git.

Each job folder has `selection.json` (ordered source descriptors and coverage policy), `sources/` (one bounded source descriptor per entry), `entries/` (validated asset records or explicit rejected states), `groups.json` (established family relationships), and `summary.json` (sanitized measured status). `selection-history/` retains explicitly revised pilot selections. Ready records describe validation at publication; use the CLI to resolve and verify actual local audio.

The ignored `data/runs/catalogue/JOB` owns the cumulative transfer/time ledger, request receipts, raw provider snapshots, batch cursor, private registration and staging. Originals are content-addressed under ignored `data/audio/catalogue/originals`; analysis derivatives use A02 `data/audio/prepared` bundles. Explicit local imports remain in ignored `manifests/private/catalogue`, and engineering material has a separate data role.

See [commands](../../docs/CATALOGUE.md), [schema 0.3](../../docs/RECORDS.md#a03-catalogue-records-version-03), and [actual acquisition evidence](../../reports/A03_CATALOGUE.md). No evaluation split or relevance score is defined here.
