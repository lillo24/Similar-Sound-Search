"""Compact immutable per-original shards and atomically resumable exact coverage."""

import time

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..matchers.acoustic import checked
from ..matchers.models import adapter
from ..matchers.runner import memory_check
from ..storage import InputError, contained, digest
from . import sources
from .contracts import (
    compatible_code,
    configuration,
    frozen,
    grid,
    load_array,
    recipe_code,
    save_array,
    union_frames,
)
from .job import charge


def initialize(budget, method, engineering=None):
    cfg = configuration(budget.root)
    _, _, _, _, desc = frozen(budget, method)
    if engineering:
        population = sources.engineering(budget, engineering)
        groups_hash = None
    else:
        records, groups = sources.catalogue(budget.root)
        population = [
            sources.public_source(v, groups["entry_groups"][v["entry_id"]]) for v in records
        ]
        groups_hash = groups["record_hash"]
    identity = {
        "version": "a06-index-1",
        "configuration": cfg,
        "representation": desc,
        "code": recipe_code(budget.root),
        "groups_hash": groups_hash,
        "sources": [[v["recording_id"], v["record_hash"]] for v in population],
    }
    key = digest(identity)
    base = contained(budget.root / "data/indexes/a06" / key, budget.root)
    path = base / "index.json"
    if path.exists():
        value = record(path)
        if value["identity"] != identity:
            raise InputError("index identity differs")
    else:
        value = {
            "schema_version": "a06-index-1",
            "index_id": key,
            "identity": identity,
            "state": "partial",
            "entries": {},
            "exclusions": [],
            "expected_recordings": len(population),
            "expected_original_seconds": sum(v["source"]["duration_seconds"] for v in population),
        }
        write_record(path, value, budget)
    return base, value, population, desc, cfg


def shard_identity(source, bounds, desc, cfg):
    return {
        "version": "a06-features-1",
        "source_id": source["recording_id"],
        "source_record_hash": source["record_hash"],
        "sha256": source["source"]["sha256"],
        "pcm": source["source"]["canonical_pcm"],
        "bounds": [list(b) for b in bounds],
        "rate": source["source"]["sample_rate_hz"],
        "representation_hash": digest(desc),
        "dimension": desc["dimension"],
        "search_policy_hash": digest(cfg),
    }


def step(request, budget):
    method = request.get("method") or "efficientat"
    base, manifest, population, desc, cfg = initialize(budget, method, request.get("engineering"))
    cursor = request["cursor"]
    if cursor >= len(population):
        totals = coverage(base, manifest)
        manifest.update(state="complete", coverage=totals, exclusions=[])
        write_record(base / "index.json", manifest, budget)
        return {
            "status": "ok",
            "state": "complete",
            "index": (base / "index.json").relative_to(budget.root).as_posix(),
            **totals,
            "method": method,
        }
    source = population[cursor]
    meta = source["source"]
    # Model + full input/measurement workspace + one bounded feature/frontend shard.
    working = 512 * 1024**2 + meta["sample_count"] * meta["channels"] * 12 + 32 * 1024**2
    budget.reserve(cfg["windows_per_shard"] * desc["dimension"] * 4 + 65536, working)
    started = time.perf_counter()
    try:
        samples = sources.load(budget, source)
    except (InputError, OSError) as exc:
        manifest.update(
            state="partial",
            exclusions=[
                {
                    "recording_id": source["recording_id"],
                    "step": "validate original",
                    "reason": str(exc),
                }
            ],
        )
        write_record(base / "index.json", manifest, budget)
        raise
    validation_seconds = time.perf_counter() - started
    bounds = grid(meta["sample_count"], meta["sample_rate_hz"], cfg)
    chunks = [
        bounds[s : s + cfg["windows_per_shard"]]
        for s in range(0, len(bounds), cfg["windows_per_shard"])
    ]
    path = base / "entries" / (source["recording_id"] + ".json")
    progress = (
        record(path)
        if path.exists()
        else {
            "source": source,
            "shards": [],
            "state": "partial",
            "validation_seconds": 0,
            "extraction_seconds": 0,
            "load_seconds": 0,
            "peak_working_bytes": 0,
        }
    )
    if progress["source"] != source:
        raise InputError("index source metadata changed")
    progress["validation_seconds"] += validation_seconds
    missing = []
    for chunk in chunks:
        identity = shard_identity(source, chunk, desc, cfg)
        key = digest(identity)
        directory = base / "shards" / key
        if directory.exists():
            _, saved = load_array(directory, identity, budget)
            if key not in progress["shards"]:
                progress["shards"].append(key)
        elif key in progress["shards"]:
            raise InputError("index completed shard missing; preserve affected evidence")
        else:
            missing.append((identity, key, chunk))
    if missing:
        identity, key, chunk = missing[0]
        charge(
            budget,
            indexed_windows=len(chunk),
            processed_window_seconds=sum((b - a) / meta["sample_rate_hz"] for a, b in chunk),
            feature_bytes=len(chunk) * desc["dimension"] * 4 + 65536,
        )
        obj, seconds = adapter(budget, method, desc)
        progress["load_seconds"] += seconds
        started = time.perf_counter()
        array = np.stack(
            [
                checked(obj.encode(samples[a:b], meta["sample_rate_hz"]), desc["dimension"])
                for a, b in chunk
            ]
        )
        progress["extraction_seconds"] += time.perf_counter() - started
        progress["peak_working_bytes"] = max(progress["peak_working_bytes"], memory_check(budget))
        save_array(base / "shards", identity, array, budget)
        progress["shards"].append(key)
    complete = len(progress["shards"]) == len(chunks)
    progress.update(
        state="complete" if complete else "partial",
        windows=len(bounds),
        indexed_union_frames=union_frames(bounds),
        processed_window_seconds=sum((b - a) / meta["sample_rate_hz"] for a, b in bounds),
    )
    write_record(path, progress, budget)
    manifest["entries"][source["recording_id"]] = progress["state"]
    write_record(base / "index.json", manifest, budget)
    return {
        "status": "ok",
        "state": "in_progress",
        "cursor": cursor + int(complete),
        "recording": source["recording_id"],
        "completed_shards": len(progress["shards"]),
        "expected_shards": len(chunks),
    }


def coverage(base, manifest):
    result = {
        "expected_recordings": manifest["expected_recordings"],
        "expected_original_seconds": manifest["expected_original_seconds"],
        "recordings": 0,
        "windows": 0,
        "original_seconds": 0,
        "indexed_unique_seconds": 0,
        "processed_window_seconds": 0,
        "feature_bytes": 0,
        "extraction_seconds": 0,
        "load_seconds": 0,
        "validation_seconds": 0,
        "peak_working_bytes": 0,
    }
    for key, state in manifest["entries"].items():
        v = record(base / "entries" / (key + ".json"))
        meta = v["source"]["source"]
        result["original_seconds"] += meta["duration_seconds"]
        actual_bounds = []
        for shard in v["shards"]:
            s = record(base / "shards" / shard / "record.json")
            actual_bounds.extend(s["identity"]["bounds"])
            result["feature_bytes"] += s["bytes"]
            result["windows"] += len(s["identity"]["bounds"])
        result["indexed_unique_seconds"] += union_frames(actual_bounds) / meta["sample_rate_hz"]
        result["processed_window_seconds"] += sum(
            (b - a) / meta["sample_rate_hz"] for a, b in actual_bounds
        )
        result["recordings"] += state == "complete"
        for field in ("extraction_seconds", "load_seconds", "validation_seconds"):
            result[field] += v[field]
        result["peak_working_bytes"] = max(result["peak_working_bytes"], v["peak_working_bytes"])
    return result


def open_index(budget, path, allow_partial=False):
    path = contained(path, budget.root / "data/indexes/a06")
    value = record(path)
    if value["index_id"] != digest(value["identity"]):
        raise InputError("index: identity corrupt")
    cfg = configuration(budget.root)
    method = value["identity"]["representation"]["method"]
    _, _, _, _, desc = frozen(budget, method)
    if (
        value["identity"]["configuration"] != cfg
        or value["identity"]["representation"] != desc
        or not compatible_code(budget.root, value["identity"]["code"])
    ):
        raise InputError(
            "index: stale search recipe/code/representation; preserve original evidence"
        )
    if value["identity"]["groups_hash"] is not None:
        population, groups = sources.catalogue(budget.root)
        if [[v["entry_id"], v["record_hash"]] for v in population] != value["identity"][
            "sources"
        ] or groups["record_hash"] != value["identity"]["groups_hash"]:
            raise InputError("index: catalogue population/duplicate groups changed")
    if value["state"] != "complete" and not allow_partial:
        raise InputError(
            "index: partial coverage; resume search index or explicitly --allow-partial"
        )
    return path.parent, value, desc, cfg
