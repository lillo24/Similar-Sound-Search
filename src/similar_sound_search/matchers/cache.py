"""Integrity-checked per-window feature reuse, atomically published after finite inference."""

import os
import tempfile
import time

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..storage import InputError, contained, digest, is_link, sha256
from .acoustic import checked
from .job import charge


def paths(budget, route, descriptor):
    identity = {"schema_version": "a05-feature-1", "route": route, "representation": descriptor}
    key = digest(identity)
    directory = budget.root / "data/features/matchers" / digest(descriptor)
    array, manifest = directory / (key + ".npy"), directory / (key + ".json")
    if is_link(array) or is_link(manifest):
        raise InputError("feature cache: linked internal artifacts refused")
    return (
        key,
        identity,
        contained(array, budget.root / "data/features/matchers"),
        contained(manifest, budget.root / "data/features/matchers"),
    )


def get(budget, route, descriptor):
    key, identity, audio, manifest = paths(budget, route, descriptor)
    if not manifest.exists():
        if audio.exists():
            raise InputError("feature cache " + key + ": orphan array; preserve/inspect owned file")
        return None
    value = record(manifest)
    if value["identity"] != identity or value["sha256"] != sha256(audio, budget):
        raise InputError("feature cache " + key + ": corrupt/stale identity or bytes")
    data = np.load(audio, allow_pickle=False)
    if data.dtype != np.dtype("float32"):
        raise InputError("feature cache: expected float32 precision")
    return checked(data, descriptor["dimension"]), value


def put(budget, policy, route, descriptor, adapter, samples):
    key, identity, path, manifest = paths(budget, route, descriptor)
    reserved = descriptor["dimension"] * 4 + 16384
    budget.reserve(
        reserved, 768 * 1024 * 1024 if descriptor["method"] == "efficientat" else 64 * 1024 * 1024
    )
    charge(budget, policy, processed_windows=1, feature_bytes=reserved)
    started = time.perf_counter()
    value = checked(adapter.encode(samples, route["sample_rate_hz"]), descriptor["dimension"])
    seconds = time.perf_counter() - started
    path.parent.mkdir(parents=True, exist_ok=True)
    # The A05 worker holds its exclusive project lock. Account this owned array
    # exactly, like bounded_json, instead of rescanning every unchanged input.
    budget.track_file(path)
    fd, name = tempfile.mkstemp(prefix=".a05-partial-", suffix=".npy", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            np.save(stream, value, allow_pickle=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        from pathlib import Path

        Path(name).unlink(missing_ok=True)
    budget.account_file(path, path.stat().st_size)
    metadata = {
        "identity": identity,
        "sha256": sha256(path, budget),
        "extraction_seconds": seconds,
        "audio_seconds": (route["end_frame"] - route["start_frame"]) / route["sample_rate_hz"],
        "bytes": path.stat().st_size,
    }
    write_record(manifest, metadata, budget)
    return value, record(manifest)
