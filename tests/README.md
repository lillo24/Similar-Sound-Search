# Runtime and catalogue correctness tests

These offline tests own runtime/catalogue and A04 harness correctness. They do not measure an acoustic matcher or perceptual quality. Run `python -m unittest discover -s tests -v` in the installed project environment.

- `helpers.py` builds independent PCM fixtures and temporary project roots, copied resource limits, and the unchanged missing-reference manifest.
- `test_evaluation.py` checks independent big-endian AIFF samples/limits, unique rating masks/zeros, signed nontrivial/tied ranks, procedural mechanisms/levels/tails, active-interval mixing, output/recipe/tool invalidation, durable counters, read-only catalogue consumption, split leakage, candidate/refined omissions, duplicate/wrong-asset/boundary hits, absence/missing/non-finite outputs, held-out gating and a complete offline procedural suite/oracle run.
- `test_inputs.py` checks hashes/known measurements, all accepted container/encoding combinations, corrupt/unsupported/silent/non-finite data, bounded inventory, and incomplete context.
- `test_preparation.py` checks channels, sample rounding, independent event timing, all three source-time cases, composed maps/padding, immutability/reuse/invalidation, and allocation/write failure recovery.
- `test_boundaries.py` runs the delivered CLI and worker, including missing-reference smoke, hard timeout, process locking, report containment/atomicity, and invalid profiles.
- `test_catalogue.py` exercises deterministic localhost transfers, retry/redirect/truncation/timeout and durable byte/time limits; shared local/network ingestion, atomic readiness/recovery and corruption/version invalidation; independent PCM identity and MP3 delay/padding fixtures; source selection/licence aliases and explicit unknown-offset snippet declarations, duplicate grouping, locked disk accounting, private import, and batch progress beyond the first bounded invocation. Generated test audio is not real catalogue acquisition evidence.

Fixtures are made in disposable temporary directories. Tests neither contact live providers/download models nor change the real reference record. [RUNTIME.md](../docs/RUNTIME.md#validation) and [CATALOGUE.md](../docs/CATALOGUE.md#validation) give formatting/static/test/smoke commands. Live acquisition/resumption is separately recorded in the A03 evidence report. OGG replaces MP3 in A02's unsupported-extension test because A03 intentionally adds MP3 Layer III, with dedicated sequential timing/truncation checks.

`test_matchers.py` owns A05 independent grid/random/control calculations, source/truth isolation, fixed scaling and finite distances, waveform timing, cache identity/corruption/failure charges, prospective protocol transaction, frozen selection, explicit held-out/network refusal, bounded coordinator failures and a small real acoustic pipeline. No network/model download or pretrained import is needed; actual pretrained smoke/comparison is an explicit integration command.

`test_search.py` owns A06 native-rate/tail/union answers, independent brute-force
sharded ranking, unordered/deduplicated queries, parent/PCM/group exclusion versus
artist independence/self diagnostics, partial/resumable index work, source/shard/clip
corruption and containment, known-note pitch/abstention/off behavior, safe HTML/URLs,
original stereo crop conversion, finite retained charges and the provenance-bound
final guard. A synthetic coordinator interruption/resume/reuse test never invokes
pretrained inference or consumes the delivery final run. A small actual acoustic
query/index/rank/playback path uses only disposable generated data.

The A06 execution-repair tests additionally verify four-record rank workers, exact result/reuse identities, preserved original function syntax, and refusal of unaudited source drift.

`test_events.py` checks independent attack/release/overlap/slow/noise/silence/cancellation
and quiet-event samples, exact native/excerpt/composed maps, explicit selection and
unsupported durations/stale originals. `test_events_boundary.py` checks explicit
accounting isolation, retained interruption cost, unordered repeated-PCM invariance
with all parents retained, independent distances, historical guard rejection,
unrelated/relevant code drift, read-only legacy source/shard verification and linked
HTML integrity. `test_events_comparison.py` runs a complete disposable development
batch with a fake adapter, then resumes without a second inference or legacy writes.
These do not use delivery ledgers, private catalogue audio or pretrained weights.

`test_event_truth.py` independently checks nonzero/multiple insertion positions,
full releases beyond a region edge, target absence within the selected region and
target/geometry drift. The event-report test resumes a WAV-only interrupted copy
with its immutable conversion receipt before playing/reusing the same crop.

## B02 coverage

`test_separation.py` uses independent signals and disposable roots for native identity,
zero-delay/edge/seam reconstruction, stereo cancellation, actual cue dependence,
cue resampling, silence/invalid inputs, transformed/excerpt/composed maps, corruption,
cue-dependent invalidation, interrupted output reuse, retained caps, parent union
before PCM dedup and truthful playback labels. It downloads nothing and does not
consume delivery ledgers. Shared original-index/guard/server regression tests remain.
