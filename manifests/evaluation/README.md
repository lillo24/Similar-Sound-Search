# Frozen evaluation inputs

This folder connects A04 recipes, ancestry and ground truth to later A05 predictions and the A06 final check. These sanitized records do not establish local audio availability or measured matcher quality.

- `protocol.json` freezes dataset revision/IDs, source-family links, splits/seed, renderer conditions, limits, metrics and development-only model selection. Its self-hash is the protocol identity.
- `suite.json` lists asset IDs **and asset record hashes**, queries, candidate populations, target sample intervals and split coverage. Predictions must match its self-hash as well as the protocol.
- `assets/*.json` describe one deterministic engineering audio artifact each: recipe/tool identity, native metadata, byte/PCM hashes, source families, parents, event/mix truth and local relative path. Audio remains ignored.
- `published.json` records actual pinned Grey1977 download checks and the explicit rights/mapping exclusions. Its 120 observed matrix cells supply **zero eligible scoring pairs**. Raw matrix/audio/order records remain ignored under `data/`.
- `pilot.json` and `protocol-history/` retain pre-model pilot/construction history. They do not supersede the current protocol or authorise held-out model tuning.

Every JSON is individually bounded by the 1 MiB reader contract. On a fresh checkout, transfer the corresponding permitted local inputs/private A03 registration before using the frozen real backgrounds. Missing files must fail visibly; generating an independent procedural-only suite requires a separately documented protocol, while retaining existing lifetime ledgers.
