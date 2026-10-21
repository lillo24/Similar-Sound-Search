# C02 candidate retrieval

C02 owns exact streamed event supports, one experimental rank fusion, bounded
overlap consolidation and the twenty-group C03 shortlist. The legacy mean-example
baseline remains default; original audio and pitch off remain unchanged.

The prospective [protocol](../manifests/retrieval/protocol.json) separates events
from alternative representations. Each event/bank uses the maximum variant rank
credit, then complete original banks are averaged. Half the strongest event plus
half mean event credit rewards both a strong example and agreement. Credits are
rank scores, not probabilities. Different row opportunities and eligible groups
still affect ranks; this is not learned calibration. Partial banks are diagnostic.

All work uses `config/retrieval.json` and C02-owned `data/runs/retrieval`,
`data/features/retrieval`, `data/audio/retrieval`, `manifests/retrieval` and
`reports/local/c02`. Read-only historical views keep C01 configuration/membership
paths separate from C02 accounting. A fresh legacy receipt binds the final C02
consumer without altering C01's receipt/snapshot or copying original arrays.

Support selection retains sixteen rows per variant/bank/group, then representative
anchored overlap clusters. Intersection divided by shorter interval must be at
least .5, intersection positive and envelope at most eight seconds. Only the same
recording may cluster. An anchor never expands to admit a transitive chain.
Adjacent intervals are separate. Three final representatives must be non-overlapping.
Every cluster retains scored row references; its envelope/context is not scored.

Implementation, validation, measured costs, Windows commands, preserved playback
and the C03 contract will be recorded in `reports/C02_RETRIEVAL.md`. No new
discovery-bank features, model, dependency, acquisition, separation or deployment.
