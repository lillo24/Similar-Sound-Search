"""Immutable crop/channel/resample derivatives, validated reuse, and composed lineage."""

import math
import os
import platform
import shutil
import tempfile
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from pathlib import Path

import numpy as np
import scipy
import soundfile as sf
from scipy.io.wavfile import write as write_wav
from scipy.signal import resample_poly

from . import __version__
from .inputs import decode, measure, probe
from .records import candidate, compose_mapping, validate_context
from .storage import (
    InputError,
    atomic_json,
    contained,
    digest,
    is_link,
    local_path,
    read_json,
    sha256,
)

PIPELINE = "a02-preparation-3"
METADATA_RESERVE = 1024 * 1024


def versions():
    return {
        "pipeline": PIPELINE,
        "package": __version__,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "soundfile": sf.__version__,
        "libsndfile": sf.__libsndfile_version__,
    }


def crop_frames(start, end, frames, rate):
    if start is None and end is None:
        return 0, frames
    if start is None or end is None:
        raise InputError("crop: --start and --end must be supplied together in input-file seconds")
    try:
        left, right = Decimal(str(start)), Decimal(str(end))
    except InvalidOperation as exc:
        raise InputError("crop: expected finite decimal seconds") from exc
    if (
        not left.is_finite()
        or not right.is_finite()
        or not Decimal(0) <= left < right
        or right * rate > frames
    ):
        raise InputError(f"crop: require 0 <= start < end <= {frames}/{rate}s; no clamping")
    first = int((left * rate).to_integral_value(rounding=ROUND_FLOOR))
    last = int((right * rate).to_integral_value(rounding=ROUND_CEILING))
    if not 0 <= first < last <= frames:
        raise InputError("crop: rounded interval has invalid source sample bounds")
    return first, last


def channel_policy(policy, channels):
    if policy == "preserve":
        return channels, None
    if policy == "mean":
        return 1, None
    if isinstance(policy, str) and policy.startswith("channel:"):
        value = policy.removeprefix("channel:")
        if value.isascii() and value.isdecimal() and 0 <= int(value) < channels:
            return 1, int(value)
    raise InputError(
        f"channels {policy!r}: use preserve, mean, or channel:N (zero-based, <{channels})"
    )


def _parent(record, path, metadata, budget):
    try:
        if record["schema_version"] != "0.2" or record["kind"] != "prepared":
            raise InputError("parent record: expected A02 schema 0.2 prepared bundle")
        if record.get("record_hash") != digest(
            {k: v for k, v in record.items() if k != "record_hash"}
        ):
            raise InputError("parent record: record integrity hash mismatch")
        artifact = record["artifact"]
        expected = (
            artifact["sha256"],
            artifact["sample_count"],
            artifact["sample_rate_hz"],
            artifact["channels"],
        )
        actual = (
            metadata["sha256"],
            metadata["sample_count"],
            metadata["sample_rate_hz"],
            metadata["channels"],
        )
        if expected != actual:
            raise InputError(
                f"parent record {path}: hash/sample metadata do not match the supplied input"
            )
        root_source = record["source"]
        source_path = Path(root_source["local_path"])
        source_path = source_path if source_path.is_absolute() else budget.root / source_path
        budget.input_file(source_path)
        if sha256(source_path, budget) != root_source["sha256"]:
            raise InputError(f"parent record: original source changed: {source_path}")
        if (
            not isinstance(record["processing_history"], list)
            or len(record["processing_history"]) > 32
        ):
            raise InputError("parent record: expected at most 32 A02 processing operations")
        if (
            record["timestamp_mapping"]["asset_id"] != artifact["asset_id"]
            or artifact["asset_id"] != "sha256:" + metadata["sha256"]
            or root_source["asset_id"] != "sha256:" + root_source["sha256"]
        ):
            raise InputError("parent record: mapping/asset identity mismatch")
        validate_context(
            {
                "schema_version": "a02-input-1",
                "kind": root_source["kind"],
                "recording": record["recording"],
                "provenance": root_source["provenance"],
                "original_recording_offset_seconds": record["timestamp_mapping"][
                    "original_recording_offset_seconds"
                ],
                "offset_evidence": record["timestamp_mapping"]["offset_evidence"],
            }
        )
    except (KeyError, TypeError) as exc:
        raise InputError(f"parent record {path}: incomplete A02 lineage ({exc})") from exc
    return record


def _reuse(bundle, key, budget):
    if is_link(bundle) or not bundle.is_dir():
        raise InputError(f"reuse {bundle}: expected a complete regular bundle directory")
    record_path, audio_path = bundle / "record.json", bundle / "audio.wav"
    if is_link(record_path) or is_link(audio_path):
        raise InputError(f"reuse {bundle}: symlink artifacts are invalid")
    record = read_json(record_path)
    try:
        artifact = record["artifact"]
        if record.get("record_hash") != digest(
            {k: v for k, v in record.items() if k != "record_hash"}
        ):
            raise InputError(f"reuse {bundle}: record integrity hash mismatch")
        if record["preparation_key"] != key or digest(record["preparation_identity"]) != key:
            raise InputError(
                f"reuse {bundle}: preparation identity mismatch; preserve for inspection"
            )
        info = sf.info(str(audio_path))
        if (
            artifact["sha256"] != sha256(audio_path, budget, "max_output_bytes")
            or info.frames != artifact["sample_count"]
            or info.samplerate != artifact["sample_rate_hz"]
            or info.channels != artifact["channels"]
        ):
            raise InputError(
                f"reuse {bundle}: corrupt/stale derivative; preserve it and remove explicitly"
            )
    except (KeyError, TypeError, sf.SoundFileError) as exc:
        raise InputError(f"reuse {bundle}: incomplete/corrupt record or audio ({exc})") from exc
    return {
        "status": "ok",
        "reused": True,
        "bundle": local_path(bundle, budget.root),
        "record": record,
    }


def prepare(path, budget, rate, channels, start=None, end=None, context=None, parent_record=None):
    path = Path(path).absolute()
    info = probe(path, budget)
    if isinstance(rate, bool) or not isinstance(rate, int) or rate <= 0:
        raise InputError("resample rate: expected a positive integer in Hz")
    budget.cap("max_sample_rate_hz", rate, "output rate")
    count_channels, selected = channel_policy(channels, info.channels)
    first, last = crop_frames(start, end, info.frames, info.samplerate)
    factor = math.gcd(rate, info.samplerate)
    up, down = rate // factor, info.samplerate // factor
    budget.cap("max_resample_factor", max(up, down), "resample ratio")
    output_frames = ((last - first) * up + down - 1) // down
    output_bytes = output_frames * count_channels * 4 + 4096
    working = (
        info.frames * info.channels * 16 + output_frames * count_channels * 32 + 32 * 1024 * 1024
    )
    budget.reserve(output_bytes + METADATA_RESERVE, working)
    samples, metadata = decode(path, budget, output_bytes + METADATA_RESERVE, working)
    if parent_record is not None and context is not None:
        raise InputError("prepare: use parent lineage or new context, never both")
    parent = (
        _parent(parent_record, path, metadata, budget)
        if parent_record is not None
        else candidate(path, metadata, context, budget.root)
    )
    parameters = {
        "channel_policy": channels,
        "crop_start_frame": first,
        "crop_end_frame": last,
        "requested_start_seconds": None if start is None else str(start),
        "requested_end_seconds": None if end is None else str(end),
        "crop_rounding": "floor_start_ceil_end",
        "input_sample_rate_hz": info.samplerate,
        "output_sample_rate_hz": rate,
        "resample_up": up,
        "resample_down": down,
        "resample_window": ["kaiser", 5.0],
        "resample_padtype": "constant_zero",
        "output_format": "WAV/FLOAT",
        "output_writer": "scipy.io.wavfile.write (no clock-dependent PEAK chunk)",
    }
    identity = {
        "input_sha256": metadata["sha256"],
        "parent_record_id": parent["record_id"],
        "parent_contract_hash": digest(parent),
        "parameters": parameters,
        "tools": versions(),
    }
    key = digest(identity)
    directory = contained(budget.root / "data/audio/prepared", budget.root)
    bundle = directory / key
    if bundle.exists():
        return _reuse(bundle, key, budget)
    # Establish the map before processing or publishing any derivative.
    mapping = compose_mapping(
        parent, first / info.samplerate, last / info.samplerate, output_frames / rate, "pending"
    )
    cropped = samples[first:last]
    if channels == "mean":
        cropped = np.mean(cropped, axis=1, dtype=np.float32, keepdims=True)
    elif selected is not None:
        cropped = cropped[:, selected : selected + 1]
    if measure(cropped)["silent"]:
        raise InputError(
            "prepare: selected interval/channel policy is silent; no usable derivative"
        )
    output = (
        cropped.copy()
        if up == down
        else resample_poly(cropped, up, down, axis=0, window=("kaiser", 5.0), padtype="constant")
    )
    budget.check_time("resample", path)
    if output.shape != (output_frames, count_channels) or not np.isfinite(output).all():
        raise InputError("resample: unexpected sample count/channel count or non-finite output")
    measurement = measure(output)
    if measurement["silent"]:
        raise InputError("resample: output is silent; no usable derivative")
    # Recheck disk immediately before the write; preflight is an estimate, not a reservation.
    budget.reserve(output_bytes + METADATA_RESERVE, working)
    directory.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".a02-partial-", dir=directory))
    try:
        audio_path = staging / "audio.wav"
        # libsndfile's floating WAV writer adds a clock-dependent PEAK chunk.
        # SciPy's public writer emits deterministic fmt/fact/data chunks instead.
        write_wav(str(audio_path), rate, output.astype(np.float32, copy=False))
        with audio_path.open("r+b") as stream:
            os.fsync(stream.fileno())
        output_hash = sha256(audio_path, budget, "max_output_bytes")
        output_id = "sha256:" + output_hash
        mapping["asset_id"] = output_id
        artifact = {
            "asset_id": output_id,
            "local_path": local_path(bundle / "audio.wav", budget.root),
            "sha256": output_hash,
            "file_bytes": audio_path.stat().st_size,
            "sample_count": output_frames,
            "sample_rate_hz": rate,
            "channels": count_channels,
            "duration_seconds": output_frames / rate,
            "format": "WAV",
            "subtype": "FLOAT",
            "measurement": measurement,
        }
        operation = {
            "operation_id": key,
            "type": "crop_channel_resample",
            "input_asset_id": "sha256:" + metadata["sha256"],
            "input_path": local_path(path, budget.root),
            "input_sha256": metadata["sha256"],
            "output_asset_id": output_id,
            "output_sha256": output_hash,
            "output_path": artifact["local_path"],
            "tools": identity["tools"],
            "parameters": parameters,
            "config_hash": digest(parameters),
            "time_map": mapping,
        }
        record = {
            **parent,
            "record_id": "prepared-" + key,
            "kind": "prepared",
            "preparation_key": key,
            "preparation_identity": identity,
            "artifact": artifact,
            "processing_history": [*parent["processing_history"], operation],
            "timestamp_mapping": mapping,
            "verified_interval": {
                "basis": "file",
                "asset_id": parent["source"]["asset_id"],
                "start_seconds": mapping["segments"][0]["source_start_seconds"],
                "end_seconds": (
                    mapping["segments"][0]["source_start_seconds"]
                    + mapping["segments"][0]["asset_end_seconds"]
                ),
                "status": "verified_bounds",
                "note": "Technical source bounds only; target/reference association unverified",
            },
        }
        record["record_hash"] = digest({k: v for k, v in record.items() if k != "record_hash"})
        atomic_json(staging / "record.json", record)
        if (staging / "record.json").stat().st_size > METADATA_RESERVE:
            raise InputError("prepare: record exceeds 1 MiB metadata limit; not publishing")
        actual = sum(p.stat().st_size for p in staging.iterdir())
        if actual > output_bytes + METADATA_RESERVE:
            raise InputError("prepare: written bundle exceeds preflight allocation; not publishing")
        budget.check_time("publish", bundle)
        if sha256(path, budget) != metadata["sha256"]:
            raise InputError(f"prepare {path}: source changed before publish")
        # A project lock prevents races; rename refuses an already existing unrelated bundle.
        staging.rename(bundle)
    finally:
        if staging.exists():
            contained(staging, directory)
            shutil.rmtree(staging)
    return {
        "status": "ok",
        "reused": False,
        "bundle": local_path(bundle, budget.root),
        "record": record,
    }
