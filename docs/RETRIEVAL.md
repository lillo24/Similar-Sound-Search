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

C03 imports metadata with `retrieval.engine.read_shortlist(owner, execution_ref,
arm="event-multi")`; omitting the arm selects the unchanged `legacy-mean` default.
It verifies immutable group/support/source references, rank order and policy binding.
The `c02-c03-shortlist-1` execution contains complete groups, the twenty-group
shortlist and ten displayed groups separately. Each `c02-c03-group-1` points to
source descriptors and complete bounded per-event/bank support. Representatives
retain bank/row/shard identities, actual scored native bounds, per-example distances,
original context, event/variant credits and unscored envelopes. Reopening metadata
is not a fresh audio/array audit: C03 must declare its own allowance and validated
consumer, then use those immutable references without reopening C01/C02 workers.

Passage coverage means at least one actual retained representative covers at least
half a known event's native frames. Full containment, IoU and boundary errors are
separate. Group hit@K and recall of all eligible positive groups are separate.
Excluded/absent positives have no success denominator; silence fails explicitly.
Loss decomposition preserves native-grid availability, mean/top16 support selection,
anchored grouping and the final twenty-group cut. Familiar procedural families are
inspected development, not human sound truth or a fresh holdout.

The C01 report's Python-variable command block is corrected only by adding
`-m similar_sound_search` before CLI flags. Its standalone verification-script
invocation, historical results and closed allowance are preserved.

Development feature progress uses immutable array-metadata references below the
shared 1 MiB record limit. The first inline progress attempt failed visibly after
572 windows; its arrays, pending receipts and charges remain. The pre-comparison
metadata integration proof pins the consuming code and unchanged audio/encoder/
grid/identity statements, so resume validates existing arrays without relabelling
or re-embedding them. Development support records reference the same immutable
encoded membership for row/native maps instead of repeating source descriptors.
