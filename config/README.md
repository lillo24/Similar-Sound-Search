# Runtime configuration

This folder owns reusable input, resource and finite catalogue contracts, without private paths or credentials.

- `resource_limits.json` supplies required numeric smoke/starter tiers to `resources.py`. [RUNTIME.md](../docs/RUNTIME.md#resource-policy) describes enforcement and estimates. A03 enforces the download allowance at the network boundary; only the future model shortlist awaits its consumer. Missing fields fail; there are no hidden tier defaults.
- `catalogue.json` supplies the one-provider source/selection, analysis coverage, request/retry and lifetime/invocation bounds to the catalogue subsystem. [CATALOGUE.md](../docs/CATALOGUE.md) defines exact defaults, frozen resumption/reselection, private local import, and cumulative accounting. It does not raise the tier ceilings.
- `input_context.example.json` illustrates an **unverified candidate excerpt**, keeping the requested 218–240 seconds separate from unknown file identity and offset. Copy it to ignored `config/local/` and replace assumptions with supplied evidence. `records.py` validates the A02 fields; a context is not an audio asset or automatic verification.

Local overrides require the explicit CLI `--profile` or `--context` flag. Nothing in `config/local/` is loaded automatically. Do not put private audio/source details in versioned configuration.
