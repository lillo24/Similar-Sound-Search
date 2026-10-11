# Reference and result records

A01 reference/result design contract, version **0.1-draft**, plus the additive **0.2 A02 input/prepared contract** below. JSON is the manifest format. A02 validates the context and lineage it uses; full reference/result validation and retrieval remain deferred. The [Loulou manifest](../manifests/references/loulou.json) remains an unchanged 0.1-draft unverified reference, not an available audio asset. Examples below are arithmetic illustrations, not search results.

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
