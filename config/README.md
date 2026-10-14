# Runtime configuration

This folder owns reusable input, resource and finite catalogue contracts, without private paths or credentials.

- `resource_limits.json` supplies required numeric smoke/starter tiers to `resources.py`. [RUNTIME.md](../docs/RUNTIME.md#resource-policy) describes enforcement and estimates. A03 enforces the download allowance at the network boundary; A05 additionally enforces the model shortlist cap. Missing fields fail; there are no hidden tier defaults.
- `catalogue.json` supplies the one-provider source/selection, analysis coverage, request/retry and lifetime/invocation bounds to the catalogue subsystem. [CATALOGUE.md](../docs/CATALOGUE.md) defines exact defaults, frozen resumption/reselection, private local import, and cumulative accounting. It does not raise the tier ceilings.
- `evaluation.json` supplies separate finite A04 transfer/attempt/time and conservative construction ceilings. It retains the existing per-worker/memory/disk caps; resumption never replenishes ledgers. [EVALUATION.md](../docs/EVALUATION.md#a04-delivered-commands-and-protocol) defines commands, accounting and recovery.
- `published_benchmark.json` pins Grey1977's revision, individual Git blob checksums/lengths and explicit upstream loader order. Unresolved rights/original row mapping keep it quarantined; editing `scoring_eligible` cannot bypass the adapter. Its hash is frozen in the evaluation protocol.
- `input_context.example.json` illustrates an **unverified candidate excerpt**, keeping the requested 218–240 seconds separate from unknown file identity and offset. Copy it to ignored `config/local/` and replace assumptions with supplied evidence. `records.py` validates the A02 fields; a context is not an audio asset or automatic verification.

Local overrides require the explicit CLI `--profile` or `--context` flag. Nothing in `config/local/` is loaded automatically. Do not put private audio/source details in versioned configuration.

- `matchers.json` supplies fixed separate A05 transfer/attempt/worker/run/window/storage/smoke allowances. Existing per-worker/memory/disk caps remain unchanged; no alternate job names replenish allowances.
- `matcher_methods.json` freezes the two-method shortlist and pinned official EfficientAT checkpoint identity/checksum, with CIR/CLAP exclusions. [MATCHERS.md](../docs/MATCHERS.md) defines optional CPU setup, representations, inference, reuse and choice.
- `search.json` owns A06's separate native-window/shard/query/display/pitch policy and finite lifetime time/read/window/storage/query/final/clip caps. [SEARCH.md](../docs/SEARCH.md) specifies exact commands, accounting, defaults, original playback and recovery. It never changes the A05 representation descriptor or prior allowances.
