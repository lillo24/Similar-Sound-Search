# B01 sound-event selection

B01 adds bounded event proposals and explicit selection to the existing original-audio
preparation/search path. It does not isolate an instrument or establish the intended
sound layer. Automatic proposals remain experimental unless the prospectively frozen
development rule supports them. Separation is B02; query-library management and further
pitch work are B03. The first required listening review remains D04.

## Integration boundary and prospective limits

The first implementation sub-step explicitly separates a B01 search accounting context
from the unchanged default A06 context. New artifacts belong to `data/runs/events/`,
`data/features/events/`, `reports/local/b01/` and `manifests/events/`. A06 commands must
continue using their original closed ledger and final-check authorization. No caught
exhaustion error redirects work into B01.

The B01 consumer will validate the historical A06 index/recipe and original execution
repair, frozen representation/checkpoint/preprocessing, grid, sources/groups and shard
identities before read-only use. Current consumer audit identity stays separate from
historical feature identity. The old whole-tree A06 final-run guard is not relaxed.
An unrelated module may require a fresh consumer receipt, never feature recomputation.
Implementation and tests must demonstrate this boundary before event comparisons run.

Numeric limits in `config/events.json` are committed before audio processing, including
the pilot. The one persistent B01 allowance is 3,600 worker seconds, 256 dispatches,
4,096 new feature events/windows, 12,000 processed feature-audio seconds, 90,000 decoded
source seconds, 64 MiB feature allocation, 16 query/rank jobs, 64 MiB query preparation,
128 clips/128 MiB playback, 32 proposal inputs/1,024 proposed events, 128 MiB event
preparation and 256 MiB total new managed output. Each proposal region is at most 30s,
with at most 32 events and three automatically selected examples. Existing starter
worker, memory, input/output, combined-disk and free-space ceilings remain unchanged.
No HTTP/download allowance exists. Interruptions retain charges. Old ledgers, audio,
features, declarations and results are immutable inputs, not new B01 work.

The initial detector shortlist has one deterministic envelope/flux configuration.
The development cases, decision rule, metrics/tolerances and stop rule will be committed
before comparison scores are inspected. Budget is reserved for both real-catalogue
queries, original playback and one necessary reuse check; optional repetitions stop
after sufficient verification. Installation, tests and preservation audits are reported
separately from the finite compute ledger.
