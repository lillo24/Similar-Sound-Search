# A06 local passage search

A06 uses the unchanged A05 representation and separate `config/search.json` search policy.
Original recordings are decoded serially; 2.4-second windows advance by 0.25 seconds
with one unique end-aligned tail. Compact immutable shards hold at most 512 vectors.
A development-only 64-window cost pilot will confirm this batch size before the final
configuration is frozen. No catalogue rankings or held-out scores inform that decision.

The fixed A06 accounting owner is `data/runs/search/`; there are no alternative job names.
Its lifetime ceilings are 7,200 worker seconds, 512 workers, 60,000 catalogue window
attempts, 160,000 processed window seconds, 180,000 sequential-read audio seconds,
256 MiB feature allocation, 24 query jobs, 64 MiB query preparation, one resumable
final evaluation (2,000 window attempts), 64 pilot windows, and 64 playback clips
within 128 MiB. Charges precede work and uncertain interrupted work is retained.
Transfer allowance is zero: restore the already pinned checkpoint/inputs explicitly.
Existing A03/A04/A05 allowances and the starter per-worker/input/disk ceilings stay fixed.

The full catalogue sizing estimate is 44,025 MN04 vectors (67,622,400 float32 bytes).
The new allowances cover one full index, validation/reuse, the final check and a small
playable demonstration with conservative interruption headroom. They do not authorize
new acquisition, another development comparison, paid compute or deployment.
Installation, inference, validation, indexing and report costs are recorded separately.
Commands and measured evidence will be completed in this document and A06's report.
