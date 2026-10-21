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
- `events.json` owns B01's single envelope/flux setting, explicit event duration/count
  limits and one finite offline processing allowance. `manifests/events/development.json`
  freezes its comparison copy before scores; changing it invalidates derived artifacts.
  `event_source.example.json` is the explicit missing Loulou excerpt path (first 22
  available-file seconds), with unverified identity/offset retained. Match its bounds
  to an actually supplied excerpt; never use second 218 on a short file. See [EVENTS.md](../docs/EVENTS.md).

## B02 optional processing

`separation.json` fixes the offline DSP algorithms, native/context limits and one
finite B02 accounting namespace. See [SEPARATION.md](../docs/SEPARATION.md) for exact
equations, schemas, conservative default and commands. Changing configuration
invalidates transformation/query identity and cannot replenish retained ceilings.

`separation_source.example.json` is a strict B02 input template for a supplied Loulou
excerpt. Its illustrative native bounds assume 44.1 kHz; inspect actual metadata and
replace bounds, hashes and audio cue before use. Missing/placeholder identity fails;
no crop at second 218 or recording-offset claim is inferred for a short excerpt.

## B03 reusable queries

`queries.json` fixes one B03 offline allowance, eight-case/sixteen-arm development
batch and the sole optional .03 / twelve-semitone pitch policy. Off/original remain
defaults. [QUERIES.md](../docs/QUERIES.md) owns strict recipe/binding/revision schemas,
supported native geometry, materialization/reuse states, exports and commands.

## C01 passage banks

`indexing.json` fixes C01's separate offline ceilings, two candidate grids,
bounded shards and original/pitch-off defaults. [INDEXING.md](../docs/INDEXING.md)
owns bank identities, native maps, immutable snapshots, component limits,
predeclared admission, exact per-bank verification and charged resume/reuse.

## C02 candidate retrieval

`retrieval.json` fixes the independent C02 allowance, baseline default, experimental
event/rank fusion, raw support cap, overlap rule and shortlist/display limits.
[RETRIEVAL.md](../docs/RETRIEVAL.md) owns historical adapters, exact evidence,
event/variant semantics, native scored/context support and the C03 export.
