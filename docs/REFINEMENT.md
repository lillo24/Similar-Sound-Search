# C03 original-mixture timing refinement

C03 imports the explicit immutable C02 `event-multi` twenty-group shortlist and
preserves its group order. Original retrieval, original audio and pitch off remain
defaults. The opt-in refinement processes at most the first two saved representative
anchors per group. Each anchor keeps its variant objective (or established mean),
all per-example distances and its bank duration. It tests -500..500 ms in 125 ms
steps, including the exact original crop. Native rounding is half away from zero;
start positions clamp to available support and deduplicate. No synthetic support,
duration sweep or claim of true sound boundaries follows.

After measuring two two-group pilot workers, development units process at most
four groups; delivery units process at most two, preserving the same per-anchor
opportunities. Native features reserve their vector bytes plus twice the compact
identity size and 8 KiB bundle overhead, rather than B03's per-vector 64 KiB cache
overhead. Earlier pilot reservations remain charged. Producer receipts are written
before encoding and kept separately from semantic sample keys and later consumers.

Every imported row is reopened against exact bank/shard/row/native membership and
its actual feature distances. The separate fresh C03 consumer receipt validates
legacy arrays under current code; historical C01/C02 receipts remain unchanged.
Original native samples are decoded and checked before crops are embedded. Matching
saved rows reuse only exact native sample/representation identities. New arrays
are bounded C03-owned bundles, never historical row IDs. Display labels are absent
from semantic keys. An original interval wins equal scores; otherwise lower cosine
distance, smaller displacement and earlier start break ties. Each original remains
an explicit retained alternate. Duplicate display suggestions are anchored; no
transitive merge erases event evidence. Context is always unscored.

Extraction is prospectively omitted: B02 failed promotion gates and the 22s Loulou
mixture has no verified clean cue. Candidate-source and conditioning-query roles
remain explicit; source/cue duplicate exclusions still apply. No processed score
can stand in for an original-mixture score or presence verification.

`config/refinement.json` and `manifests/refinement/protocol.json` fix one finite
allowance/batch. All inference, full repeated source reads, failures, report/native
QA and one reuse pass use C03 workers, CPU/offline/concurrency one, 120s per worker.
The `--pilot` flag executes one bounded worker and returns resumable progress for
cost inspection; it changes no policy or allowance. Run the same command without
it to continue. Tests/setup/preservation/HTTP/browser QA are reported separately.
No acquisition, separator input, dependency change or C04 scheduler is authorized.

Use `.venv/Scripts/python.exe -m similar_sound_search --tier starter refinement`
with `preflight`, `known-answer`, `geometry`, `compare`, `compatibility`, `refine`,
`verify`, `report`, `verify-native` or `serve`. Refinement and verification require
explicit `--execution PATH --arm event-multi --receipt FRESH_C03_RECEIPT`.
`execution.json` is a locator only; the declared immutable reference is pinned
before work. Missing derivatives use explicit `derive-query` through the existing
B03 recipe boundary and C03-owned publication; no mutable query head is selected.

New roots: `data/runs/refinement`, `data/features/refinement`,
`data/audio/refinement`, `manifests/refinement`, `reports/local/c03`. Summaries are
contained under `reports/local/c03`, including explicit `--report` paths. Start
verified local playback with `scripts/listen-refinement.ps1` on loopback 8772;
prior bundles/listeners remain untouched. Private media/model/query prerequisites
are required; public evidence does not supply them to a fresh clone.

The `c03-c04-refinement-1` export keeps twenty group states/ranks, complete C02
inputs, original/refined native row references, semantic feature dependencies,
producer/current consumer proof, lineage, original support/context, ledger ownership
and atomic commit boundaries. Its dependency graph names changes requiring new work.
No automatic invalidation, source refresh, garbage collection or C04 implementation
is included. Detailed paired outcomes, costs and Windows commands belong to
`reports/C03_REFINEMENT.md`.

Historical float64 distances are checked with zero relative tolerance and absolute tolerance 2e-15, accounting for final-bit BLAS rounding when reopening one row instead of a whole shard. Native intervals and reused feature bytes remain exact; recomputed values and untouched imported scores are both retained. This is a numerical validation tolerance, not a sound-presence threshold.
