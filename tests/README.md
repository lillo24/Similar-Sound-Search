# A02 correctness tests

These small offline tests own engineering correctness, not A04 retrieval/perceptual benchmarks. Run `python -m unittest discover -s tests -v` in the installed project environment.

- `helpers.py` builds independent PCM fixtures and temporary project roots, copied resource limits, and the unchanged missing-reference manifest.
- `test_inputs.py` checks hashes/known measurements, all accepted container/encoding combinations, corrupt/unsupported/silent/non-finite data, bounded inventory, and incomplete context.
- `test_preparation.py` checks channels, sample rounding, independent event timing, all three source-time cases, composed maps/padding, immutability/reuse/invalidation, and allocation/write failure recovery.
- `test_boundaries.py` runs the delivered CLI and worker, including missing-reference smoke, hard timeout, process locking, report containment/atomicity, and invalid profiles.

Fixtures are made in disposable temporary directories. Tests neither download audio/models nor change the real reference record. [RUNTIME.md](../docs/RUNTIME.md#validation) gives the complete formatting/static/test/smoke commands.
