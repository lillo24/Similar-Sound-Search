# Reference and result records

A01 design contract, version **0.1-draft**. JSON is the initial manifest format; executable validation, storage, and retrieval are deferred. The [Loulou manifest](../manifests/references/loulou.json) is an actual unverified reference record, not an available audio asset. Examples below are arithmetic illustrations, not search results.

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
