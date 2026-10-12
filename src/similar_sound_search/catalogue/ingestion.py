"""One ingestion path for explicit local files and provider downloads; immutable originals."""

import hashlib
import os
from pathlib import Path

from ..inputs import decode
from ..preparation import _reuse, prepare, versions
from ..records import validate_context
from ..storage import InputError, bounded_json, contained, digest, is_link, read_json, sha256
from . import PIPELINE
from .transfer import fetch, utc_now


def entry_key(descriptor):
    return digest(
        [descriptor["provider"], descriptor["provider_recording_id"], descriptor["origin_url"]]
    )


def context_for(descriptor, acquired_at):
    if descriptor["provider"] == "local":
        return validate_context(descriptor["context"])
    return validate_context(
        {
            "schema_version": "a02-input-1",
            "kind": descriptor["kind"],
            "recording": {
                "recording_id": descriptor["provider_recording_id"],
                "artist": descriptor["artist"],
                "title": descriptor["title"],
                "version": descriptor["version"],
                "identity_status": "verified",
                "identity_evidence": (
                    "Provider file/track association in SHA256-pinned metadata snapshot"
                ),
                "external_ids": {"internet_archive": descriptor["provider_recording_id"]},
            },
            "provenance": {
                "origin_url": descriptor["origin_url"],
                "acquired_at": acquired_at,
                "permitted_use": descriptor["rights"]["permitted_use"],
                "notes": descriptor["time_evidence"],
            },
            "original_recording_offset_seconds": descriptor["original_recording_offset_seconds"],
            "offset_evidence": descriptor["offset_evidence"],
        }
    )


def local_descriptor(path, context, data_role="real_recording_discovery"):
    path = Path(path).absolute()
    context = validate_context(context)
    if not context["provenance"]["permitted_use"]:
        raise InputError("catalogue import: context.provenance.permitted_use is required")
    if data_role not in {"real_recording_discovery", "engineering"}:
        raise InputError("catalogue import: unsupported data role")
    return {
        "provider": "local",
        "data_role": data_role,
        "provider_recording_id": context["recording"]["recording_id"]
        or "explicit-" + digest(str(path)),
        "origin_url": None,
        "source_item_id": None,
        "source_page": None,
        "file_name": "explicit" + path.suffix.lower(),
        "expected_bytes": None,
        "expected_md5": None,
        "title": context["recording"]["title"],
        "artist": context["recording"]["artist"],
        "album": None,
        "version": context["recording"]["version"],
        "genre": None,
        "known_family_id": None,
        "source_snapshot": None,
        "available_aliases": [],
        "context": context,
        "rights": {
            "audio_licence_url": None,
            "audio_licence": None,
            "permitted_use": "Explicit user-authorised local import; evidence retained privately",
            "attribution": None,
            "evidence_url": None,
            "metadata_licence": None,
        },
    }


def copy_local(path, staging, budget):
    budget.input_file(path)
    budget.reserve(Path(path).stat().st_size + 65536)
    before = sha256(path, budget)
    total = 0
    if hasattr(budget, "track_file"):
        budget.track_file(staging)
    with Path(path).open("rb") as source, staging.open("wb") as target:
        if hasattr(budget, "account_file"):
            budget.account_file(staging, 0)
        while chunk := source.read(65536):
            budget.check_time("local import", path)
            total += len(chunk)
            budget.cap("max_input_bytes", total, path)
            target.write(chunk)
            if hasattr(budget, "account_file"):
                budget.account_file(staging, total)
        target.flush()
        os.fsync(target.fileno())
    if sha256(staging, budget) != before or sha256(path, budget) != before:
        raise InputError("local import: explicit source changed during copy")


def ingest(
    descriptor,
    directory,
    ledger,
    public_directory,
    local_input=None,
    refresh=False,
    allow_local_http=False,
):
    """A ready state commits only after original validation and A02 derivative publication."""
    budget = ledger.budget
    root = budget.root

    def publish(path, value):
        bounded_json(path, value, budget)

    key = entry_key(descriptor)
    state_path = directory / "entries" / (key + ".json")
    public_path = public_directory / "entries" / (key + ".json")
    identity = digest(
        {
            "descriptor": descriptor,
            "policy": ledger.policy,
            "tools": versions(),
            "pipeline": PIPELINE,
        }
    )
    previous = read_json(state_path) if state_path.exists() else None
    if previous and previous.get("refresh_required") and not refresh:
        raise InputError(
            "catalogue: prior refresh failed; repeat --refresh; "
            "cached audio cannot mask that failure"
        )
    record = previous.get("record") if previous else None
    acquired_at = previous["acquired_at"] if previous else utc_now()
    source_path = None
    if record:
        source_path = contained(
            root / record["source_asset"]["local_path"], root / "data/audio/catalogue/originals"
        )
        try:
            if record.get("record_hash") != digest(
                {k: v for k, v in record.items() if k != "record_hash"}
            ):
                raise InputError("catalogue cached record integrity failed")
            budget.input_file(source_path)
            if sha256(source_path, budget) != record["source_asset"]["sha256"]:
                raise InputError(
                    "cached original byte identity changed; use --refresh to reacquire"
                )
            if (
                local_input is not None
                and sha256(local_input, budget) != record["source_asset"]["sha256"]
            ):
                source_path = None
            elif previous["identity"] == identity and not refresh and previous["state"] == "ready":
                derivative = record["analysis_derivative"]
                bundle = contained(
                    root / Path(derivative["local_path"]).parent, root / "data/audio/prepared"
                )
                reused = _reuse(bundle, record["preparation_key"], budget)
                if reused["record"]["record_hash"] != record["prepared_record_hash"]:
                    raise InputError("cached preparation metadata changed")
                if not public_path.exists() or read_json(public_path) != record:
                    budget.reserve(65536)
                    publish(public_path, record)
                return {"status": "ok", "state": "ready", "entry_id": key, "reused": True}
        except (InputError, OSError) as exc:
            if not refresh:
                # Invalidate the public ready state as well as private lifecycle evidence.
                failure = {
                    "schema_version": "0.3",
                    "entry_id": key,
                    "state": "invalidated",
                    "reason": "cached_asset_validation_failed",
                }
                publish(public_path, failure)
                previous.update({"state": "invalidated", "error": str(exc)})
                publish(state_path, previous)
                raise
            source_path = None
    elif previous and previous.get("validated_source") and not refresh:
        validated = previous["validated_source"]
        source_path = contained(
            root / validated["local_path"], root / "data/audio/catalogue/originals"
        )
        budget.input_file(source_path)
        if sha256(source_path, budget) != validated["sha256"]:
            raise InputError("catalogue validated original changed during interrupted preparation")
    state = {
        "schema_version": "a03-entry-state-1",
        "entry_id": key,
        "identity": identity,
        "state": "discovered",
        "acquired_at": acquired_at,
        "record": record,
        "refresh_required": refresh,
    }
    if previous and previous.get("validated_source"):
        state["validated_source"] = previous["validated_source"]
    budget.reserve(131072)
    publish(state_path, state)
    staging = directory / "staging" / (key + Path(descriptor["file_name"]).suffix.lower())
    staging.parent.mkdir(parents=True, exist_ok=True)
    try:
        if source_path is None or refresh:
            if local_input is not None:
                copy_local(local_input, staging, budget)
            else:
                fetch(
                    descriptor["origin_url"],
                    staging,
                    ledger,
                    ledger.policy["max_audio_bytes"],
                    descriptor["expected_bytes"],
                    allow_local_http,
                )
            state["state"] = "downloaded" if local_input is None else "copied"
            publish(state_path, state)
            if descriptor["expected_md5"]:
                result = hashlib.md5(usedforsecurity=False)
                with staging.open("rb") as stream:
                    while chunk := stream.read(65536):
                        budget.check_time("provider checksum", key)
                        result.update(chunk)
                if result.hexdigest() != descriptor["expected_md5"]:
                    raise InputError("provider checksum mismatch: changed/truncated remote payload")
            _, metadata = decode(staging, budget, extra_output_bytes=131072)
            if metadata["measurement"]["silent"]:
                raise InputError("catalogue: silent audio is not eligible")
            originals = contained(root / "data/audio/catalogue/originals", root)
            originals.mkdir(parents=True, exist_ok=True)
            source_path = originals / (metadata["sha256"] + staging.suffix)
            if source_path.exists():
                if is_link(source_path) or sha256(source_path, budget) != metadata["sha256"]:
                    raise InputError(
                        "content-addressed original is corrupt; "
                        "preserve and remove explicitly before retry"
                    )
                staging.unlink()
            else:
                staging.rename(source_path)
            state["state"] = "validated"
            state["validated_source"] = {
                **metadata,
                "local_path": source_path.relative_to(root).as_posix(),
            }
            publish(state_path, state)
        else:
            _, metadata = decode(source_path, budget, extra_output_bytes=131072)
        context = context_for(descriptor, acquired_at)
        duration = metadata["duration_seconds"]
        # Explicit coverage policy: centred <=30s excerpt, original mixture channels retained.
        start = max(0, int((duration - ledger.policy["analysis_seconds"]) / 2))
        end = min(int(duration), start + ledger.policy["analysis_seconds"])
        if end <= start:
            start_arg = end_arg = None
        else:
            start_arg, end_arg = str(start), str(end)
        if hasattr(budget, "refresh_disk"):
            budget.refresh_disk()
        prepared = prepare(
            source_path,
            budget,
            ledger.policy["analysis_rate_hz"],
            ledger.policy["analysis_channels"],
            start_arg,
            end_arg,
            context,
        )
        prepared_record = prepared["record"]
        if hasattr(budget, "refresh_disk"):
            budget.refresh_disk()
        record = {
            "schema_version": "0.3",
            "kind": "catalogue_asset",
            "entry_id": key,
            "state": "ready",
            "data_role": descriptor.get("data_role", "real_recording_discovery"),
            "recording": {
                k: descriptor[k]
                for k in (
                    "provider_recording_id",
                    "title",
                    "artist",
                    "album",
                    "version",
                    "source_item_id",
                    "known_family_id",
                )
            },
            "provider": descriptor["provider"],
            "acquisition": {
                "origin_url": descriptor["origin_url"],
                "source_page": descriptor["source_page"],
                "acquired_at": acquired_at,
                "snapshot": descriptor["source_snapshot"],
                "rights": descriptor["rights"],
                "expected_md5": descriptor["expected_md5"],
                "remote_freshness": (
                    "Pinned metadata/file snapshot; --refresh checks payload; "
                    "unchanged resumes do not poll remote"
                ),
                "available_aliases": descriptor["available_aliases"],
            },
            "source_asset": {
                **metadata,
                "asset_id": "sha256:" + metadata["sha256"],
                "local_path": source_path.relative_to(root).as_posix(),
                "kind": context["kind"],
            },
            "analysis_derivative": prepared_record["artifact"],
            "timestamp_mapping": prepared_record["timestamp_mapping"],
            "processing_history": prepared_record["processing_history"],
            "preparation_key": prepared_record["preparation_key"],
            "prepared_record_hash": prepared_record["record_hash"],
            "prepared_record_path": prepared["bundle"] + "/record.json",
            "ingestion_identity": identity,
            "tools": versions(),
            "duplicate_group_ref": "../groups.json#/entry_groups/" + key,
            "unknowns": [
                "No timbre/relevance label; no A04 split; "
                "unknown alternate encodings/near-duplicates remain undetected"
            ],
        }
        record["recording"].update(
            {
                "identity_status": context["recording"]["identity_status"],
                "identity_evidence": context["recording"]["identity_evidence"],
                "external_ids": context["recording"]["external_ids"],
            }
        )
        record["record_hash"] = digest(record)
        budget.reserve(131072)
        publish(public_path, record)
        state.update({"state": "ready", "record": record, "refresh_required": False})
        publish(state_path, state)
        return {"status": "ok", "state": "ready", "entry_id": key, "reused": False}
    except (InputError, OSError, ValueError) as exc:
        state.update({"state": "rejected", "error_type": type(exc).__name__, "error": str(exc)})
        publish(state_path, state)
        publish(
            public_path,
            {
                "schema_version": "0.3",
                "entry_id": key,
                "state": "rejected",
                "reason": type(exc).__name__,
            },
        )
        # Preserve bounded partials for diagnosis; they are never eligible/ready and count on disk.
        raise


def duplicate_groups(records):
    """Established equality/provider relationships only; no title-based or fuzzy merging."""
    parents = {record["entry_id"]: record["entry_id"] for record in records}

    def root(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    seen = {}
    edges = []
    for record in sorted(records, key=lambda r: r["entry_id"]):
        key = record["entry_id"]
        source = record["source_asset"]
        recording = record["recording"]
        identities = {
            "byte_sha256": source["sha256"],
            "decoded_pcm_sha256": source["canonical_pcm"]["sha256"],
            "provider_recording_id": (
                record["provider"] + ":" + recording["provider_recording_id"]
                if record["provider"] != "local" or recording.get("identity_status") == "verified"
                else None
            ),
            "provider_declared_family": recording["known_family_id"],
        }
        for kind, identity in identities.items():
            if identity is None:
                continue
            lookup = (kind, identity)
            if lookup in seen:
                other = seen[lookup]
                a, b = sorted((root(key), root(other)))
                parents[b] = a
                edges.append(
                    {
                        "entries": [other, key],
                        "evidence": kind,
                        "confidence": "exact_samples"
                        if kind == "decoded_pcm_sha256"
                        else "exact_bytes"
                        if kind == "byte_sha256"
                        else "provider_declared",
                    }
                )
            else:
                seen[lookup] = key
    groups = {}
    for key in sorted(parents):
        groups.setdefault("family-" + root(key), []).append(key)
    return {
        "schema_version": "a03-groups-1",
        "groups": groups,
        "edges": edges,
        "entry_groups": {key: group for group, members in groups.items() for key in members},
        "coverage": (
            "Exact bytes/decoded float32 samples, repeated provider IDs and supplied provider "
            "recording-family IDs. Lossy re-encodings, edits, and unknown near-duplicates not "
            "detected; titles never establish equality."
        ),
    }


def validate_local_ready(record, budget, job="starter"):
    """Read-only consumer validation; never opens an acquisition ledger or changes state.

    Public readiness alone is insufficient. Require matching private registration, full
    sequential original decoding and canonical identity, plus the immutable A02 bundle.
    The caller owns its independent processing deadline, lock and accounting.
    """
    key = record["entry_id"]
    if record.get("state") != "ready" or record.get("record_hash") != digest(
        {k: v for k, v in record.items() if k != "record_hash"}
    ):
        raise InputError(f"catalogue consumer {key}: invalid public ready record")
    private = contained(
        budget.root / "data/runs/catalogue" / job / "entries" / (key + ".json"),
        budget.root / "data/runs/catalogue",
    )
    if not private.is_file():
        raise InputError(f"catalogue consumer {key}: private local registration missing")
    registration = read_json(private)
    if registration.get("state") != "ready" or registration.get("record") != record:
        raise InputError(f"catalogue consumer {key}: private/public registration differs")
    original = contained(
        budget.root / record["source_asset"]["local_path"],
        budget.root / "data/audio/catalogue/originals",
    )
    _, metadata = decode(original, budget)
    for field in ("sha256", "canonical_pcm", "sample_count", "sample_rate_hz", "channels"):
        if metadata[field] != record["source_asset"][field]:
            raise InputError(f"catalogue consumer {key}: original {field} changed")
    bundle = contained(
        budget.root / Path(record["analysis_derivative"]["local_path"]).parent,
        budget.root / "data/audio/prepared",
    )
    prepared = _reuse(bundle, record["preparation_key"], budget)["record"]
    if prepared["record_hash"] != record["prepared_record_hash"]:
        raise InputError(f"catalogue consumer {key}: preparation record changed")
    samples, derivative = decode(bundle / "audio.wav", budget)
    if derivative["sha256"] != record["analysis_derivative"]["sha256"]:
        raise InputError(f"catalogue consumer {key}: analysis bytes changed")
    return samples, prepared
