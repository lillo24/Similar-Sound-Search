# Development matcher subsystem

This folder owns A05 representations, finite checkpoint acquisition, development inference/reuse and provisional selection. Shared input tooling decodes audio; the evaluation subsystem owns ground truth and scoring. No held-out inference, catalogue search, production index, separation or UI is implemented here.

| File | Responsibility |
| --- | --- |
| `__init__.py` | Subsystem semantics version |
| `windows.py` | Truth-independent integer interval grid and opaque waveform routing |
| `correction.py` | Prospective geometry audit/control predictions and atomic paired comparison revision |
| `acoustic.py` | Fixed-scale spectral/cepstral/envelope baseline, shared deterministic channel/resampling boundary and validated distances |
| `efficientat_model.py` | Narrow MN04 channel-SE/MLP architecture adaptation, with strict local state loading delegated to the adapter |
| `efficientat.py` | Lazy optional CPU inference and native evaluation frontend; no TorchAudio extension, training or automatic downloads |
| `models.py` | Reviewed checkpoint identity/receipt, representation descriptors and pre-ranking shortlist freeze |
| `cache.py` | Per-window feature identity, finite inference charges, atomic array/metadata publication and integrity-checked reuse |
| `runner.py` | Read-only asset validation, resumable batches, genuine prediction publication before truth joining, smoke and measured memory evidence |
| `selection.py` | Existing-scorer integration, descriptive family reporting, frozen lexicographic selection and A05 choice record |
| `job.py` | Separate lifetime ledgers, hard-deadline workers, network refusal outside explicit acquisition and held-out refusal |
| `LICENSE-EfficientAT.md` | Upstream MIT copyright/licence for adapted inference architecture |

The parent retains the shared project lock; each child holds `.a05-worker.lock`. Numerical threads/concurrency remain one. `runner.py` passes only samples and sample rate into an adapter. Filenames, presets, families, insertion truth and conditions never reach feature computation. Predictions are persisted before `selection.py` joins truth through the existing scorer. See [commands/setup](../../../docs/MATCHERS.md), [evaluation policy](../../../docs/EVALUATION.md), and [evidence](../../../reports/A05_MATCHERS.md).

A06's [search owner](../search/README.md) reuses the adapters and split-parametrized
truth-independent routes through its own accounting/coordinator. A05 CLI/job refusal
of held-out work remains unchanged. A06 never calls A05 cache publication/charge.
