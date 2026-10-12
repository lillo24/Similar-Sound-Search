"""Immutable recipe-addressed evaluation audio, integrity and construction accounting."""

import os
import tempfile
from pathlib import Path

import numpy as np
from scipy.io.wavfile import write as write_wav

from ..inputs import decode
from ..preparation import versions
from ..storage import InputError, ResourceError, bounded_json, contained, digest, read_json
from . import VERSION


def write_record(path, value, budget):
    value = {k: v for k, v in value.items() if k != "record_hash"}
    bounded_json(path, {**value, "record_hash": digest(value)}, budget)


def record(path):
    value = read_json(path)
    if not isinstance(value, dict) or value.get("record_hash") != digest(
        {k: v for k, v in value.items() if k != "record_hash"}
    ):
        raise InputError(f"evaluation record {Path(path).name}: integrity mismatch")
    return value


def asset_paths(root, key):
    if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise InputError("evaluation asset: expected recipe SHA256 identifier")
    return (
        contained(root / "data/audio/evaluation/generated" / (key + ".wav"), root),
        contained(root / "manifests/evaluation/assets" / (key + ".json"), root),
    )


def load_asset(root, key, budget):
    path, manifest = asset_paths(root, key)
    value = record(manifest)
    if value.get("asset_id") != key or digest(value["identity"]) != key:
        raise InputError(f"evaluation asset {key}: recipe identity differs")
    samples, metadata = decode(path, budget)
    if metadata != value["audio"]:
        raise InputError(f"evaluation asset {key}: corrupt/stale audio; preserve and inspect it")
    if value["identity"]["tools"] != versions() or value["identity"]["version"] != VERSION:
        raise InputError(f"evaluation asset {key}: renderer/tool version changed; regenerate suite")
    return samples, value


def charge_generation(directory, budget, policy, size, seconds):
    path = directory / "construction.json"
    old = (
        record(path)
        if path.exists()
        else {
            "bytes": 0,
            "seconds": 0,
            "items": 0,
            "ceilings": {k: policy[k] for k in policy if k.startswith("max_generation_")},
        }
    )
    for key in old["ceilings"]:
        old["ceilings"][key] = min(old["ceilings"][key], policy[key])
    for key, amount in (("bytes", size), ("seconds", seconds), ("items", 1)):
        limit = old["ceilings"]["max_generation_" + key]
        if old[key] + amount > limit:
            raise ResourceError(
                f"A04 construction {key}: lifetime allowance exhausted; inspect ledger"
            )
        old[key] += amount
    # Charge before rendering/writing. Crash reservations are never refunded.
    write_record(path, old, budget)


def publish(recipe, render, budget, policy, directory):
    identity = {"version": VERSION, "tools": versions(), "recipe": recipe}
    key = digest(identity)
    path, manifest = asset_paths(budget.root, key)
    if manifest.exists():
        _, value = load_asset(budget.root, key, budget)
        return value, True
    if path.exists():
        raise InputError(f"evaluation {key}: uncommitted audio; inspect/remove this owned file")
    frames, rate = recipe["frames"], recipe["rate"]
    size = frames * 4 + 4096
    budget.cap("max_duration_seconds", frames / rate, key)
    budget.cap("max_sample_rate_hz", rate, key)
    budget.cap("max_decoded_bytes", frames * 4, key)
    budget.reserve(size + 65536, frames * 64 + 32 * 1024 * 1024)
    charge_generation(directory, budget, policy, size, frames / rate)
    samples, details = render()
    samples = np.asarray(samples, dtype=np.float32).reshape(-1, 1)
    if len(samples) != frames or not np.isfinite(samples).all():
        raise InputError(f"render {key}: non-finite audio or incorrect frame count")
    if not 1e-12 < np.max(np.abs(samples)) <= 0.901:
        raise InputError(f"render {key}: silent or clipped output")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".a04-partial-", suffix=".wav", dir=path.parent)
    os.close(fd)
    staging = Path(name)
    try:
        write_wav(str(staging), rate, samples)
        with staging.open("r+b") as stream:
            os.fsync(stream.fileno())
        _, metadata = decode(staging, budget)
        staging.rename(path)
    finally:
        staging.unlink(missing_ok=True)
    budget.refresh_disk()
    value = {
        "schema_version": "a04-asset-1",
        "asset_id": key,
        "identity": identity,
        "data_role": "generated_engineering",
        "audio": metadata,
        "local_path": path.relative_to(budget.root).as_posix(),
        **details,
    }
    write_record(manifest, value, budget)
    return record(manifest), False
