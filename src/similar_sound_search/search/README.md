# Local passage search

This folder owns A06 search policy, original-recording indexing, explicit unordered
queries, exact ranking, one final check and local original-mixture playback. A02 owns
decoding/preparation/maps, A03 validates ready originals read-only, A05 owns unchanged
representations, and A04 owns truth/scoring. No labels or source metadata enter encoding.

| File | Responsibility and relationship |
| --- | --- |
| `__init__.py` | Search semantics version |
| `contracts.py` | Numeric configuration, original A05 choice/checkpoint bindings, integer native grids, immutable arrays, source-code identity |
| `sources.py` | Serial read-only catalogue original validation and explicit generated diagnostic sources |
| `index.py` | Per-recording bounded shards, atomic progress, full-file interval unions and integrity-checked reuse |
| `query.py` | Explicit A02 crops/lineage, complete-content limits, identical-PCM deduplication, unordered examples and features |
| `ranking.py` | Blockwise exact per-example distances, aggregate mean, parent/group exclusion and one best scored passage per group |
| `pitch.py` | Optional conservative classical pitch estimate with abstention and separate bounded contribution |
| `report.py` | Verified original stereo PCM16 crops, safe local HTML, visible media errors and loopback allowlisted server |
| `final.py` | Immutable pre-inference A06 declaration, selected held-out coordinator and persisted-prediction scoring |
| `commands.py` | CLI operations, development-only cost pilot, predetermined substitute and known-target inputs |
| `job.py` | Fixed lifetime accounting, retained interrupted charges, hard workers and offline network guard |

The parent holds `.a02.lock`; children hold `.a06-worker.lock`. Index workers decode
one original and load one adapter for one bounded shard. Ranking retains only vectors
and one best interval per recording group. A scored window is never expanded into a
scored union. Playback context is a separately declared original crop. See
[commands and limits](../../../docs/SEARCH.md) and [records](../../../docs/RECORDS.md).
