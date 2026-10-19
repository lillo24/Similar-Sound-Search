# Sound-event selection

This subsystem owns B01 proposals, explicit selection and native original-event crops,
plus the development comparison and minimal local event report. It supplies an explicit
B01 accounting/compatibility context to A06's shared query/ranking/playback primitives.
A02 owns decoding/preparation/maps, A03 validates originals, A04 owns renderer truth and
scoring, and A05 owns the unchanged representation. Nothing here separates a layer.

| File | Responsibility |
| --- | --- |
| `__init__.py` | B01 event semantics version |
| `context.py` | Fixed finite B01 accounting, output roots and explicit search handoff |
| `compatibility.py` | Audited read-only A06 feature consumer and immutable receipts |
| `detector.py` | Truth-independent phase-safe onset/envelope proposals and uncertainty |
| `selection.py` | Explicit source/region records, selection, A02 extraction and query input |
| `comparison.py` | Prospectively frozen development cases, note matching and fixed matcher comparison |
| `report.py` | Original event/context media and contained links to both search reports |
| `job.py` | One persistent offline B01 ledger, bounded serial workers and dispatch |

See [contracts, limits and commands](../../../docs/EVENTS.md). Full A06 rebuilding and
held-out inference are deliberately absent from this dispatcher.
