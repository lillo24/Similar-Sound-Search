# Optional processing owner

B02 compares original audio, broad HPSS components and explicit audio-cue extraction.
It composes existing preparation, frozen features, distances, index validation and
allowlisted playback; it owns transformed signals rather than changing old recipes.

| File | Responsibility |
| --- | --- |
| `context.py` | Fixed B02 roots/caps, receipt handoff, source/cue exclusion union |
| `job.py`, `commands.py` | Offline locked 120-second workers and explicit CLI routing |
| `dsp.py` | Pure centred STFT/overlap-add, stereo HPSS and fixed audio-template masks |
| `artifacts.py` | Source/cue/parent validation, immutable float outputs and time maps |
| `protocol.py`, `geometry.py` | Separate development constructions and independent pre-inference support checks |
| `features.py` | B02 feature cache using the unchanged EfficientAT adapter |
| `comparison.py`, `metrics.py` | One resumable paired batch; equal-support candidate diagnostic and evaluation-only truth |
| `validation.py` | Charged numerical feasibility/known answers |
| `report.py` | Distinguish original context, processed queries and original candidates |

`events.compatibility` is reused read-only with B02-owned receipts. No legacy ledger
or feature is rewritten. See [commands and equations](../../../docs/SEPARATION.md).
