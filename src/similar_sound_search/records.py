"""A02 candidate context and source-time maps (an additive 0.2 record contract)."""

import math

from .storage import InputError, digest, local_path

SCHEMA = "0.2"
CONTEXT_FIELDS = {
    "schema_version",
    "kind",
    "recording",
    "provenance",
    "reference_record_id",
    "requested_interval",
    "original_recording_offset_seconds",
    "offset_evidence",
}
RECORDING_FIELDS = {
    "recording_id",
    "artist",
    "title",
    "version",
    "external_ids",
    "identity_status",
    "identity_evidence",
}
PROVENANCE_FIELDS = {"origin_url", "acquired_at", "permitted_use", "notes"}


def finite_number(value):
    try:
        return (
            not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
        )
    except OverflowError:
        return False


def _optional_text(value, label):
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise InputError(f"context {label}: expected nonempty text or null")


def validate_context(context):
    """Supplied evidence is retained, never inferred from a filename or request."""
    if context is None:
        context = {"schema_version": "a02-input-1", "kind": "unknown"}
    if not isinstance(context, dict) or set(context) - CONTEXT_FIELDS:
        raise InputError("context: expected object with documented a02-input-1 fields")
    if context.get("schema_version") != "a02-input-1":
        raise InputError("context: schema_version must be a02-input-1")
    kind = context.get("kind")
    if kind not in {"unknown", "full_track", "excerpt"}:
        raise InputError("context kind: expected unknown, full_track, or excerpt")
    supplied = context.get("recording", {})
    if not isinstance(supplied, dict) or set(supplied) - RECORDING_FIELDS:
        raise InputError("context recording: unsupported fields or non-object")
    recording = dict.fromkeys(RECORDING_FIELDS)
    recording.update(supplied)
    recording["identity_status"] = supplied.get("identity_status", "unverified")
    if recording["identity_status"] not in {"unverified", "verified"}:
        raise InputError("context recording.identity_status: expected unverified or verified")
    for field in RECORDING_FIELDS - {"external_ids", "identity_status"}:
        _optional_text(recording[field], f"recording.{field}")
    if recording["external_ids"] is not None and not isinstance(recording["external_ids"], dict):
        raise InputError("context recording.external_ids: expected object or null")
    if recording["identity_status"] == "verified" and not all(
        recording[key] for key in ("recording_id", "version", "identity_evidence")
    ):
        raise InputError(
            "verified recording identity requires recording_id, version, identity_evidence"
        )
    supplied = context.get("provenance", {})
    if not isinstance(supplied, dict) or set(supplied) - PROVENANCE_FIELDS:
        raise InputError("context provenance: unsupported fields or non-object")
    provenance = dict.fromkeys(PROVENANCE_FIELDS)
    provenance.update(supplied)
    for field, value in provenance.items():
        _optional_text(value, f"provenance.{field}")
    offset = context.get("original_recording_offset_seconds")
    evidence = context.get("offset_evidence")
    _optional_text(evidence, "offset_evidence")
    if offset is not None:
        if not finite_number(offset) or offset < 0:
            raise InputError("context original offset: expected finite nonnegative seconds or null")
        if kind == "unknown" or not evidence or recording["identity_status"] != "verified":
            raise InputError(
                "original offset requires known kind, verified identity and offset_evidence"
            )
        if kind == "full_track" and offset != 0:
            raise InputError(
                "full_track original offset must be zero; use excerpt for nonzero offsets"
            )
    elif evidence is not None:
        raise InputError("context offset_evidence requires an explicit original offset")
    reference = context.get("reference_record_id")
    _optional_text(reference, "reference_record_id")
    requested = context.get("requested_interval")
    if requested is not None:
        if not isinstance(requested, dict) or requested.get("basis") != "claimed_recording":
            raise InputError(
                "requested_interval: only unverified claimed_recording requests accepted"
            )
        start, end = requested.get("start_seconds"), requested.get("end_seconds")
        if not finite_number(start) or not finite_number(end) or not 0 <= start < end:
            raise InputError("requested_interval: expected finite 0 <= start < end")
        if requested.get("status") not in {"approximate", "unverified"}:
            raise InputError("requested_interval: status must be approximate or unverified")
    return {
        "schema_version": "a02-input-1",
        "kind": kind,
        "recording": recording,
        "provenance": provenance,
        "reference_record_id": reference,
        "requested_interval": requested,
        "original_recording_offset_seconds": offset,
        "offset_evidence": evidence,
    }


def candidate(path, metadata, context, root):
    context = validate_context(context)
    asset_id = "sha256:" + metadata["sha256"]
    duration = metadata["duration_seconds"]
    source = {
        "asset_id": asset_id,
        "availability": "available",
        "local_path": local_path(path, root),
        "sha256": metadata["sha256"],
        "kind": context["kind"],
        "duration_seconds": duration,
        "sample_count": metadata["sample_count"],
        "sample_rate_hz": metadata["sample_rate_hz"],
        "channels": metadata["channels"],
        "provenance": context["provenance"],
    }
    offset = context["original_recording_offset_seconds"]
    basis = (
        "recording" if offset is not None else "excerpt" if source["kind"] == "excerpt" else "file"
    )
    unknowns = ["Target event selection and reference association have not been verified in A02."]
    if context["recording"]["identity_status"] != "verified":
        unknowns.append(
            "Recording identity/version unverified; technical decoding is separate evidence."
        )
    if offset is None:
        unknowns.append("Original-recording offset unknown; no recording-time claim is made.")
    if source["kind"] == "unknown":
        unknowns.append("Full-track/excerpt kind unknown; filenames and duration are not evidence.")
    if source["provenance"]["permitted_use"] is None:
        unknowns.append(
            "Permitted use unknown; registration does not authorize acquisition or sharing."
        )
    return {
        "schema_version": SCHEMA,
        "record_id": "input-" + digest({"hash": metadata["sha256"], "context": context}),
        "kind": "input",
        "validation_status": "unverified",
        "technical_metadata_status": "verified",
        "technical_metadata": metadata,
        "recording": context["recording"],
        "source": source,
        "reference_record_id": context["reference_record_id"],
        "requested_interval": context["requested_interval"],
        "verified_interval": None,
        "selected_events": [],
        "processing_history": [],
        "timestamp_mapping": {
            "asset_id": asset_id,
            "status": "verified_file_mapping",
            "basis": basis,
            "original_recording_offset_seconds": offset,
            "offset_evidence": context["offset_evidence"],
            "segments": [
                {
                    "asset_start_seconds": 0,
                    "asset_end_seconds": duration,
                    "source_start_seconds": 0,
                    "source_seconds_per_asset_second": 1,
                }
            ],
            "unmapped_tail_seconds": 0,
        },
        "unknowns": unknowns,
    }


def compose_mapping(parent, crop_start, crop_end, output_duration, asset_id):
    """Compose only this pipeline's contiguous unit-speed maps; offset stays at root."""
    mapping = parent["timestamp_mapping"]
    segments = mapping.get("segments")
    if not isinstance(segments, list) or len(segments) != 1:
        raise InputError("parent mapping: A02 requires one contiguous segment")
    segment = segments[0]
    fields = ("asset_start_seconds", "asset_end_seconds", "source_start_seconds")
    if (
        any(not finite_number(segment.get(key)) for key in fields)
        or segment.get("source_seconds_per_asset_second") != 1
        or segment["asset_start_seconds"] != 0
        or segment["source_start_seconds"] < 0
        or not 0 < segment["asset_end_seconds"]
    ):
        raise InputError("parent mapping: invalid contiguous unit-speed segment")
    # A ceil-rounded resample can have a fractional output bin beyond valid source time.
    # Never claim that padded tail maps to real original audio.
    if crop_start >= segment["asset_end_seconds"]:
        raise InputError("crop lies entirely in parent resampler padding; no original source span")
    source_start = segment["source_start_seconds"] + crop_start
    span = min(crop_end, segment["asset_end_seconds"]) - crop_start
    if source_start + span > parent["source"]["duration_seconds"] + 1e-12:
        raise InputError("composed map exceeds original available source duration")
    return {
        **mapping,
        "asset_id": asset_id,
        "segments": [
            {
                "asset_start_seconds": 0,
                "asset_end_seconds": min(span, output_duration),
                "source_start_seconds": source_start,
                "source_seconds_per_asset_second": 1,
            }
        ],
        "unmapped_tail_seconds": max(0, output_duration - span),
    }


def map_time(record, seconds):
    """Map a valid sample time to source and optional original-recording seconds."""
    mapping = record["timestamp_mapping"]
    segment = mapping["segments"][0]
    if not finite_number(seconds) or not 0 <= seconds < segment["asset_end_seconds"]:
        raise InputError(f"map time {seconds}: outside verified mapping span")
    source = segment["source_start_seconds"] + seconds
    offset = mapping["original_recording_offset_seconds"]
    return {
        "source_seconds": source,
        "recording_seconds": None if offset is None else source + offset,
    }
