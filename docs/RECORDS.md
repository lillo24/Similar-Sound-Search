# Reference and result records

A01 reference/result design contract, version **0.1-draft**, plus additive **0.2 input/prepared** and **0.3 catalogue** contracts below. JSON is the manifest format. Runtime context/lineage and catalogue identity are validated; full reference/result validation and retrieval remain deferred. The [Loulou manifest](../manifests/references/loulou.json) remains an unchanged 0.1-draft unverified reference, not an available audio asset. Examples below are arithmetic illustrations, not search results.

## Common conventions

- Use stable opaque record/asset IDs. A provisional recording ID must not imply a verified release/version. Recording metadata and exact file identity are separate: SHA-256 identifies file bytes, not the musical work or every re-encoding of it.
- Use `null` for unknown scalars/objects and a status/reason for missing evidence. An empty list means no entries have been recorded, not a successful empty search or a proof that no events exist. Never substitute zero for an unknown offset or an empty string for a missing hash.
- Store seconds as finite numbers and intervals as half-open `[start_seconds, end_seconds)`. Verified file/excerpt intervals require `0 <= start < end <= decoded asset duration`. A recording-time interval must map into the available source file's bounds; do not compare its absolute seconds directly with an excerpt's duration. Record sample rate and sample boundaries when available; derive displayed seconds from those coordinates.
- An interval carries `basis` and `asset_id`: `file` means time in that exact file; `recording` means verified original-recording time; `excerpt` means time relative to the available excerpt; `claimed_recording` is an unverified user request. A claimed interval cannot be used as a verified file crop.
- Keep local paths relative to the repository when practical. Public manifests must not contain private absolute paths, credentials, or signed access URLs. Keep sensitive acquisition details in `manifests/private/`.

## Shared source and lineage fields

| Field | Information and rules |
| --- | --- |
| `schema_version`, `record_id`, `kind` | Contract version, stable record ID, and `reference` or `result` |
| `validation_status` | `unverified`, `verified`, or `invalid`; verification requires supporting file/mapping evidence |
| `recording` | `recording_id`, `artist`, `title`, `version`, `external_ids`, and `identity_status`; unknown version stays null |
| `source` | Original available input file: `asset_id`, `availability`, `local_path`, `sha256`, `kind` (`full_track`, `excerpt`, or `unknown`), `duration_seconds`, `sample_rate_hz`, and `channels` |
| `source.provenance` | `origin_url`, `acquired_at`, `permitted_use`, and `notes`; unknown permission stays null and does not authorize acquisition/use |
| `processing_history` | Ordered operations: operation ID/type, input/output asset IDs, paths and hashes, tool/model version and checkpoint hash when relevant, parameters/config hash, run ID, and time-map changes; empty in A01 |
| `timestamp_mapping` | Analysed `asset_id`, mapping `status`, display `basis` (`recording`, `excerpt`, or `unknown`), `original_recording_offset_seconds`, and `segments`; defined below |
| `unknowns` | Explicit unresolved facts and why they matter; do not hide missing file/mapping evidence in free-text claims of success |

Hash the original file before processing and every derived asset used by a run. A later operation must not overwrite the original. Version/hash changes invalidate dependent features and indexes. Content hashes and duplicate/related-recording groups serve different purposes; both are needed later to exclude query copies and keep related examples together.

## Reference-specific fields

| Field | Information and rules |
| --- | --- |
| `requested_interval` | The supplied approximate interval, with basis, asset ID if known, verification status, and note; retain it even after a verified event is selected |
| `verified_interval` | Checked interval in the actual available source file (`basis: file`), or null until file and bounds are verified |
| `selected_events` | Event IDs and complete note/event intervals in identified assets, including attack and decay; store any event-to-source maps and selection rationale |
| `target_description` | User description and the uncertainty of instrument identity; descriptive wording is not a label verified from audio |
| `similarity_priorities` | Ordered priorities and separately recorded pitch preference/tolerance; unknown tolerance remains null |
| `context_sources` | Prompt/design context for the request; these links do not establish audio provenance |

The initial request is 218–240 seconds in an unidentified recording. `source.availability` is `missing`; path, hash, verified interval, mapping segments, and original offset remain null. No selected event or processing operation has been recorded. A02 must inspect an available file before treating this request as a usable query. It must not ask for similar-song labels to fill these fields.

## Timestamp mapping and playback

Each segment maps an analysed asset's seconds back to the unchanged available source file:

```text
source_time = source_start_seconds
            + (asset_time - asset_start_seconds) * source_seconds_per_asset_second
```

A segment records `asset_start_seconds`, `asset_end_seconds`, `source_start_seconds`, and `source_seconds_per_asset_second`. The covered range must be valid in both assets; scale must be positive. For a full-track input with verified identity/start, the original-recording offset is zero. For an excerpt with a verified original offset, add that offset once to source-file time to display recording time. For an excerpt with unknown offset, keep the offset null and display **excerpt-relative** source-file time. With no file, basis/status remain `unknown`/`unverified` and segments remain null.

| Illustrative input | Analysed time to source-file time | Displayed interval |
| --- | --- | --- |
| Full track, cropped at 218 seconds | Asset 0–22 maps to source 218–240; original offset 0 | Recording 218–240 |
| Existing excerpt starting at original second 218, offset verified | Asset 0–22 maps to source 0–22; original offset 218 | Recording 218–240 |
| Existing excerpt with unknown original offset | Asset 0–22 maps to source 0–22; original offset null | Excerpt 0–22; no claimed recording time |

The 22-second duration above is hypothetical; the real Loulou file duration is unknown. Do not crop an existing excerpt at second 218 just because the requested recording interval starts there, or add the requested start again after mapping a full-track crop.

Resampling changes sample coordinates, not elapsed seconds: map using the respective sample rates, normally with time scale 1. Trimming, time stretching, concatenation, and tool latency require explicit maps. Compose successive operations back to the original available source. Split a hit across noncontiguous segments into separate playback intervals; do not fabricate a continuous original passage. Unknown timing changes prevent a verified mapping claim.

## Result-specific fields

| Field | Information and rules |
| --- | --- |
| `query_record_id`, `run_id`, `rank` | Query/version and comparison run; rank is scoped to that run, not a global relevance rating |
| `matched_interval` | Interval in the analysed asset (`basis: file`) and its asset ID |
| `display_interval` | Mapped original-recording interval when verified, otherwise explicitly excerpt-relative; never a claimed interval presented as verified |
| `playback` | Original available input asset ID, hash, local path, and source-file interval; retain the original mixture even when a separated asset supplied features |
| `representation` | Feature/model identifier, version, checkpoint hash if applicable, preprocessing/config hash, and feature/index version |
| `ranking` | `score`, `metric`, `direction` (`higher_is_better` or `lower_is_better`), normalization, and score meaning; timbre and optional pitch contributions remain separately inspectable |
| `retrieval_lineage` | Candidate rank/score, refinement rank/score if run, and aggregation/deduplication decisions; a missing stage remains null |
| `duplicate_group_id`, `discovery_eligible` | Known recording/encoding/near-duplicate relationship to the query; reference copies are diagnostic results, excluded from discovery |

A result uses the common source, processing history, and time-map fields as well. An item with unavailable playback or unverified mapping cannot pass the technical acceptance contract. Report it as an incomplete diagnostic rather than a playable verified match. Similarity scores order candidates; they are **not calibrated probabilities** or independent evidence of perceived similarity. Calibration would require separate evidence and a versioned protocol.

No result manifest is created in A01: there has been no search. Store future sanitized result manifests with their run/protocol records, and keep private run output under `data/runs/` or `reports/local/`.

## A02 input and prepared records (version 0.2)

A02 adds `kind: input|prepared`, rather than changing the unimplemented reference/result contract or asserting that a decoded candidate is the intended reference. Inputs appear in private inspection reports; prepared records live next to their derivative in ignored `data/audio/prepared/KEY/record.json`. Public exports require privacy review. `source` always identifies the **original available file**; a prepared record's `artifact` identifies its current derivative.

| Field / extension | A02 meaning |
| --- | --- |
| `schema_version: "0.2"`, `record_id` | Content/context-derived input ID or preparation-key-derived prepared ID |
| `validation_status: "unverified"` | Target/reference association remains unverified, even when technical evidence succeeds |
| `technical_metadata_status: "verified"`, `technical_metadata` | Root file decoded, byte SHA-256, frames/rate/channels/duration, container/subtype, peak/RMS/silence measured; separate from recording identity |
| `source.sample_count` | Original available-file frame count; all channels share this count |
| `recording.identity_evidence` | Explicit supplied evidence; no filename-based verification |
| `reference_record_id` | Optional supplied candidate association, never an automatic reference-manifest update |
| `requested_interval` | Optional supplied approximate/unverified `claimed_recording` interval; never used as a crop |
| `verified_interval` | Null on inspection; on preparation, verified technical source-file bounds with `status: verified_bounds`, not target-event verification |
| `timestamp_mapping.status: "verified_file_mapping"` | Checked sample/time mapping back to the original available source; original-recording identity/offset is separate evidence |
| `timestamp_mapping.basis: "file"` | New display basis when a file is available but kind or original offset is unknown; excerpt with unknown offset still uses `excerpt` |
| `timestamp_mapping.offset_evidence` | Supplied basis for a non-null original offset, retained once across composition |
| `timestamp_mapping.unmapped_tail_seconds` | Fractional ceil-rounded resampler bin beyond real source duration, excluded from verified mapping/playback |
| `artifact` (prepared only) | Derivative asset ID/path/byte hash/size, frames/rate/channels/duration, output format and measurements |
| `preparation_key`, `preparation_identity` | Hash of input bytes, parent ID/contract hash, explicit processing parameters, and tools/versions |
| `record_hash` (prepared only) | SHA-256 of canonical sorted compact UTF-8 JSON excluding this field; detects record corruption before reuse/composition |
| `processing_history` | Ordered operations with input/output identity, paths/hashes, tools, parameters/config hash, operation key and composed time map |

Asset IDs are `sha256:HEX`; an input record also hashes supplied context so different identity/permission evidence cannot silently reuse an older association. Technical measurements stay with the root source; each derivative has its own `artifact` measurements. `selected_events` remains empty because B01 owns selection. The preparation key doubles as the deterministic operation/run identity; timestamps are omitted from canonical records so identical supported-environment inputs reproduce them. CLI reports retain measured wall time and actual environment separately.

Optional `a02-input-1` context has a required `schema_version` and `kind`. Missing optional fields are documented unknowns: null identity/provenance/offset/request/reference ID and `identity_status: unverified`. Allowed recording/provenance fields follow the tables above, plus `identity_evidence`. `original_recording_offset_seconds` and `offset_evidence` are at the context root. Verified identity requires nonempty recording ID, version and evidence; a known offset also requires known kind, verified identity and offset evidence. Full-track offsets must explicitly be zero. Invalid/incomplete assertions fail; supplied evidence is not independently authenticated. See [the candidate excerpt example](../config/input_context.example.json).

Runtime readers accept only their documented context or 0.2 prepared lineage; passing the 0.1 Loulou reference as a prepared parent is an explicit error. The smoke reads its reference ID/source availability/status without converting or verifying it. Preparation maps are contiguous, unit elapsed-time scale, and composable through at most 32 previous A02 operations. More general concatenation/stretching maps remain future work. [RUNTIME.md](RUNTIME.md#context-and-timestamps) specifies rounding, decoder/resampler timing, supported formats, and exact commands.

## A03 catalogue records (version 0.3)

A03 adds `kind: catalogue_asset`, without changing reference 0.1 or prepared 0.2 schemas. Catalogue ingestion uses the same 0.2 prepared record in the ignored bundle. `prepared_record_path` points to that record for subsequent `prepare --parent-record`; the outer 0.3 record is deliberately not accepted as an A02 parent. Source maps still compose to the original available file. [CATALOGUE.md](CATALOGUE.md) defines exact commands, layout, rights filters, resource accounting and recovery.

| Field | Contract |
| --- | --- |
| `schema_version: "0.3"`, `kind`, `entry_id`, `record_hash` | Catalogue asset, deterministic provider/recording/URL entry identity, canonical JSON self-hash excluding `record_hash` |
| `state` | `ready` only after validated original and complete derivative publication; rejected/invalidated records have explicit reasons. A versioned ready record documents past validation; local private registration and actual files are also required before use |
| `data_role` | `real_recording_discovery`, or explicitly `engineering` for local test imports. Neither is published human-rated evaluation data |
| `provider`, `recording` | Provider recording ID, source item, artist/title/album/version, optional known family ID and association identity status/evidence/external IDs. Nulls remain unknown. Provider file association does not verify an external master or the Loulou reference |
| `acquisition` | Public file/source URLs, acquisition UTC date, pinned raw metadata snapshot SHA-256/URL/date, provider MD5 and explicit freshness policy |
| `acquisition.rights` | Audio licence name/URL, source evidence URL/hash, allowed local-use scope, attribution; metadata licence kept separate and unknown unless established |
| `acquisition.available_aliases` | Other provider-linked eligible encodings and their URLs/checksums/sizes, retaining association/rights evidence through the parent recording record; not counted as extra recordings |
| `source_asset` | Immutable original byte asset ID/hash/size/relative path, source format/subtype, kind, decoded count/rate/channels/duration, acoustic measurements, canonical PCM identity and decoder/version/timing notes |
| `analysis_derivative` | A02 artifact identity/hash/path/sample metadata, generated under explicit centred <=30s, preserved-channel, 16 kHz policy |
| `processing_history`, `timestamp_mapping` | A02 lineage and map in sequentially decoded available-file coordinates; original offsets/evidence remain null unless supplied and validated |
| `preparation_key`, `prepared_record_hash`, `prepared_record_path`, `ingestion_identity`, `tools` | Verified derivative reuse and descriptor/permission/config/decoder/preparation identity; a changed relevant identity cannot inherit ready status silently |
| `duplicate_group_ref` | Relative `../groups.json#/entry_groups/ENTRY_ID` from the entry record; resolve against its catalogue job's group manifest |
| `unknowns` | Explicit lack of timbre labels, near-duplicate completeness, evaluation splits and relevance evidence |

Source technical metadata in existing 0.2 records gains additive `decoder` and `canonical_pcm` fields. **Canonical PCM `sss-pcm-f32le-1`** hashes the canonical sorted compact UTF-8 JSON header `{"schema_version":"sss-pcm-f32le-1","sample_rate_hz":RATE,"channels":CHANNELS,"sample_count":FRAMES}` followed by LF, then frame-major interleaved little-endian IEEE float32 samples in original channel order. Both signed zeros become positive zero. Non-finite values are refused. There is no gain/clip/dither/resample/channel operation. WAV/FLAC representing the same float32 samples have the same PCM hash; precision lost in float32 conversion is explicit. Decoder/version changes may change a lossy source's PCM identity. This is not a perceptual or near-duplicate hash.

`groups.json` connects exact file-byte hashes, exact canonical decoded PCM, repeated provider IDs, and explicit provider recording-family identifiers. Evidence confidence is `exact_bytes`, `exact_samples`, or `provider_declared`. Unverified local textual recording IDs do not establish equality. Group IDs use the lexicographically smallest entry ID in each connected component, making ordering/resumption deterministic; adding a newly established relationship can deliberately change the canonical group anchor, so consumers must use the current mapping. All alias entries retain provenance. Titles/artists alone never merge recordings. Unknown lossy re-encodings/edits/near-duplicates remain outside established coverage. These groups support later query-copy/leakage control; A03 creates no A04 split.

The layout is bounded per document: small selection header and ordered entry IDs/hashes, one sanitized source descriptor and one ready/failure record per asset, and bounded group/summary records. Raw provider metadata, request receipts, explicit local contexts/paths, cumulative ledger and batch cursor stay ignored. Public summaries omit private error paths; actionable full failures remain in the local CLI report. All asset references are repository-relative. Neither a committed manifest nor a metadata response constitutes locally acquired audio.

For MP3, sample/time coordinates refer to **full sequential decoder output**, with decoder-interpreted priming/padding and residual uncertainty recorded. Source bytes stay MP3 and analysis WAV stays a lossy-source derivative. Ordinary provider full-track files and explicitly labelled snippets have null master offsets unless independently evidenced; snippets are excerpt-kind records, and available-file timing remains usable. Known local full-track/known-excerpt/unknown-excerpt contexts retain their original A02 semantics, applying a verified offset once. No sample-exact MP3 random seek, reference association, or relevance result is inferred.

## A04 evaluation records

Evaluation uses its own versioned adapter, sharing the input/preparation tools without expanding catalogue import roles. Reference 0.1, prepared 0.2 and catalogue 0.3 remain intact. `a04-asset-1` records represent **generated engineering** audio; `a04-human-1` represents native published-study material in quarantine. Neither enters real discovery counts. AIFF follows the same bounded sequential decoder and canonical float32 PCM definition as other supported containers.

The [evaluation map](../manifests/evaluation/README.md) connects `a04-protocol-1`, `a04-suite-1`, per-asset records and published summaries. Each public JSON has a SHA256 `record_hash` over canonical content excluding that field, with the existing 1 MiB reader limit. Generated asset IDs are SHA256 of evaluation version, pinned tool versions and complete recipe, distinct from byte/PCM hashes. Recipes retain preset identity versus related family, phrase, pitch, seed, transformation, parent IDs and mixing/background lineage. Time spans use half-open integer sample bounds; sample rate/channels/count and coordinate basis stay explicit. Mixture source time is the constructed mixture file; a background's original-file offset is separate ancestry, never added to a target prediction.

Prediction files use `a04-predictions-1` and match **both** current protocol and suite self-hashes. Minimal shape (replace illustrative IDs/hashes with actual manifest values):

```json
{
  "schema_version": "a04-predictions-1",
  "protocol_hash": "PROTOCOL_SHA256",
  "suite_hash": "SUITE_SHA256",
  "run_id": "explicit-run-id",
  "method_id": "explicit-method-version",
  "configuration": {"representation": "explicit-version"},
  "config_hash": "SHA256_OF_CANONICAL_CONFIGURATION",
  "split": "development",
  "coordinate_basis": "decoded_available_file",
  "score_direction": "higher_better",
  "evidence_kind": "matcher",
  "cost": {
    "wall_seconds": 0,
    "processed_audio_seconds": 0,
    "storage_bytes": 0,
    "peak_working_bytes_estimate": 0
  },
  "human_predictions": [],
  "queries": [{
    "query_id": "QUERY_ID_FROM_SUITE",
    "candidate": [{"asset_id": "ASSET_ID", "start_frame": 0, "end_frame": 24000, "score": 0.5}],
    "refined": []
  }]
}
```

Costs in this schema are caller-reported measurements, with working bytes explicitly an estimate; zero in the illustration is not a measured model run. A04 harness examples process no audio with a matcher and report zero matcher cost, while scorer/worker wall time is measured separately. `evidence_kind` is `matcher`, `harness_oracle`, `harness_wrong`, `harness_missing` or A05's `harness_control`; every output/report retains the distinction. Direction is `higher_better` or `lower_better`. Each stage accepts at most 128 scored intervals per query; integers/finite scores, exact permitted IDs, bounds, config identity and stage ancestry are checked. Duplicate query IDs, stale protocol/suite hashes, unknown/cross-split assets and malformed results fail. Missing queries are explicit misses with original denominators, not deleted observations.

Ranking, duplicate/K behavior, one-to-one temporal rules, absence reporting and the A06 frozen-choice declaration are defined in [EVALUATION.md](EVALUATION.md#a04-delivered-commands-and-protocol) and the protocol. Human predictions are currently refused because the selected dataset is unavailable for scoring. A future reviewed human adapter must preserve original observations/masks and source-group split restrictions; it cannot quietly turn quarantined values into evidence. Raw dataset audio/matrix, absolute machine paths, worker ledgers and full score files remain under ignored `data/` or `reports/local/`.

## A05 development records

The [matcher record map](../manifests/matchers/README.md) connects the geometry correction, pinned checkpoint receipt, prospective shortlist, per-condition/per-family comparison and provisional choice. Every JSON is self-hashed and bounded to 1 MiB. `a05-comparison-1` atomically embeds a complete protocol and suite with individually verified self-hashes and binding; shared readers prefer it over canonical mirrors. Original A04 records remain in history.

Predictions retain `a04-predictions-1`, with genuine `evidence_kind: matcher`, the revised protocol/suite hashes, full configuration/code/checkpoint identity, all 80 development query records and empty refined lists. Only the scorer joins ground truth after prediction publication. `harness_control` labels constant/seeded-random geometry diagnostics; their zero model cost is not a measured model.

Feature identity binds audio byte/PCM identity, interval/rate, deterministic preparation/tool versions, representation source/checkpoint/layer/scaling, precision/device and versions. Ignored `a05-feature-1` records bind deterministic float32 arrays to hashes and actual original extraction duration. Reuse checks referenced source audio and array integrity and retains cold inference cost. Progress is explicit in-progress/complete; unsuccessful inference returns failure. The four lifetime run operations count complete reuse as well as original runs.

`a05-choice-1` records `stage: A05`, `selected_on: development`, method/config/protocol/suite/shortlist identities, full representation configuration, development criteria/costs, unavailable methods, control comparisons and limits. It cannot satisfy the existing A06 guard. A06 must explicitly initiate its final check with the exact frozen choice and correct stage; no A05 command enables held-out inference/scoring.

## A06 search and playback records

`a06-index-1` binds a separately versioned search policy, canonical source-code identity,
unchanged representation, current catalogue/group record hashes and explicit source
population. Per-original records retain native source metadata/provenance/mapping,
immutable shard keys and partial/complete progress. `a06-shard-1` validates content keys,
shared half-open native bounds, dimension/float32/finite values and array SHA256. Coverage
reports full-original seconds, union of indexed intervals and overlapping processed
window seconds separately; historical ready metadata is not local availability.

`a06-query-1` retains complete A02 records, source/selected byte/PCM hashes, lineage and
map/offset evidence for each unique example. Equal selected PCM cannot silently reweight
the unordered mean-distance query. `a06-result-1` binds the index/shard set and query,
metric/direction/representation, explicit pitch preference and diagnostic inclusion.
It retains per-example/aggregate timbre distances, optional pitch contribution,
duration mismatch, recording/group/source URLs and scored native intervals. The mismatch
is candidate duration minus each example's duration, in seconds. One best passage per
group suppresses overlapping alternatives; it never assigns a score to a
merged/unscored interval. Results are candidates without calibrated presence/probability.

`a06-playback-1` binds original crops, frame/rate/channel counts, clip-zero source offsets,
known/unknown master offsets, PCM16 conversion/gain, exact sample verification, byte
hashes and safe local HTML. Context and scored bounds remain distinct. Bundle allowlists
exclude all unrelated paths. Missing/corrupt source, shard or media fails visibly.

`a06-final-1` is declared before inference and embeds self-hashed unchanged A05 choice
and shortlist, their hashes, protocol/suite, exact checkpoint/config, frozen held-out
grid/split/no-pitch/refinement policy, committed implementation, code/environment and
one finite run identity. Original `choice.json` stays A05. A04's guard validates these
bindings, rejecting a free-form `stage:A06` object. Predictions retain A04's <=128 interval
contract and all eighty query denominators, and are published before scoring. The
catalogue's exact search has a separate sharded contract and no 128-window restriction.

## B01 events

`b01-proposals-1` binds the explicit source/parent/region, native byte/PCM metadata,
detector configuration/code and stable event IDs. Every interval is half-open native
frames with measured energy/novelty and explicit overlap/censoring warnings.
`b01-selection-1` separately binds explicit IDs/manual bounds or the fixed automatic
rule. `b01-extraction-1` retains verified native A02 crops and composed maps, actual
support/padding and single/multiple query handoffs. Unknown master offsets stay null.

Shared A06 query/result schemas add an explicit `consumer` binding only for B01.
Query bindings retain unordered selection provenance; result bindings retain the
`b01-a06-consumer-1` receipt. That receipt separates the frozen historical feature
identity from the current audited consumer, pins sources/groups/shards/checkpoint
and requires their validation. It does not authorize an A06 rebuild or final check.
`b01-playback-1` adds hash-allowlisted named HTML pages to the shared verified-media
bundle. See [EVENTS.md](EVENTS.md) for caps, invalidation, metrics and commands.
## B02 transformations

`b02-transform-1` owns waveform changes separately from A02 crop/channel/resample
records. It binds native source/parent/context/cue identities and bounds, method,
configuration/code/tools, explicit zero padding/trim/delay/gain, float32 output hashes,
source maps, low-output states and original/duplicate exclusions. A truthful A02 crop
of the transformed file is linked through the narrow B02 query context. Original and
cue ancestry is unioned before PCM dedup; no filename-based ancestry is accepted.
See [SEPARATION.md](SEPARATION.md) for schemas, equations and failure/reuse policy.

## B03 recipes, bindings and executions

`b03-revision-1` hashes a canonical `b03-query-recipe-1`, independently of labels/local
bindings. Sources retain native byte/PCM/decoder/context and optional A02 parent hashes;
examples retain full integer event/context bounds and selection uncertainty. Optional
components bind unchanged B02 transformation/source/cue/output/map/configuration receipts.
The cue is a conditioning dependency, not an implicit extra example. `b03-name-1` holds
display label, selected immutable revision and history with optimistic update checks.

`b03-binding-1` maps a dependency to an explicit validated project-relative file/receipt.
`b03-query-export-1` transports the recipe and hash inventory without media/binding paths.
Unresolved metadata is distinct from ready materialization. `b03-materialization-1`
binds an exact revision and validated shared A06 query/feature matrix; that query retains
all local binding snapshots even after a mutable name or binding changes. Underlying
PCM/representation feature blobs remain independent of pitch, display and provenance.

`b03-winners-1` preserves all eligible timbre-best original group passages before top-ten
truncation. `b03-execution-1` binds revision, materialization, current read-only index
receipt, complete winners and explicit versioned preference. Score is unchanged mean
timbre distance plus a separately inspectable bounded pitch term. Reuse checks source,
feature, mapping and complete candidate bindings; old predictions remain immutable.
`b03-playback-1` distinguishes provided original context/examples, explicit derived/cue
audio and original catalogue candidate clips, with native/player timestamps and gains.
See [QUERIES.md](QUERIES.md) for contracts, availability states and exact CLI syntax.
