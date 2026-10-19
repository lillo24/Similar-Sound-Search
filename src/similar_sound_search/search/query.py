"""Explicit whole-event A02 query preparation, unordered examples and frozen features."""

import time
from pathlib import Path

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..inputs import decode, probe
from ..matchers.acoustic import checked
from ..matchers.models import adapter
from ..matchers.runner import memory_check
from ..preparation import crop_frames, prepare
from ..storage import InputError, contained, digest, read_json
from . import sources
from .contracts import configuration, frozen, load_array, save_array
from .job import charge, read_charge
from .pitch import estimate


def parents(root, prepared, pcm):
    records, groups = sources.catalogue(root)
    source = prepared["source"]
    result = set()
    for v in records:
        if (
            v["source_asset"]["sha256"] == source["sha256"]
            or v["source_asset"]["canonical_pcm"]["sha256"] == pcm["sha256"]
            or v["analysis_derivative"]["sha256"]
            == prepared["preparation_identity"]["input_sha256"]
        ):
            result.add(groups["entry_groups"][v["entry_id"]])
    return sorted(result)


def prepare_query(budget, spec_path, method, context=None):
    cfg = configuration(budget.root)
    _, _, _, _, desc = frozen(budget, method)
    spec = read_json(spec_path)
    if (
        spec.get("schema_version") != "a06-query-input-1"
        or not isinstance(spec.get("examples"), list)
        or not 1 <= len(spec["examples"]) <= cfg["max_query_examples"]
    ):
        raise InputError("query: requires 1..8 explicit examples in a06-query-input-1")
    examples, excluded = {}, set()
    for item in spec["examples"]:
        if set(item) - {"path", "start", "end", "context", "parent_record"}:
            raise InputError("query example: unsupported fields; event/layer inference is deferred")
        path = Path(item["path"])
        path = path if path.is_absolute() else budget.root / path
        info = probe(path, budget)
        first, last = crop_frames(item.get("start"), item.get("end"), info.frames, info.samplerate)
        if (last - first) / info.samplerate > cfg["max_query_seconds"]:
            raise InputError("query: selected content exceeds 30 seconds; choose explicit bounds")
        input_context = read_json(budget.root / item["context"]) if item.get("context") else None
        parent = record(budget.root / item["parent_record"]) if item.get("parent_record") else None
        # Full sequential source/selected derivative reads remain cumulatively visible.
        read_charge(budget, {"duration_seconds": info.frames / info.samplerate}, context=context)
        if context is not None and parent is not None:
            # A02 validates the root original's byte hash as well as decoding the
            # current crop. B01 explicitly accounts that additional source read.
            read_charge(budget, parent["source"], context=context)
        charge(
            budget,
            context=context,
            query_preparation_bytes=(last - first) * info.channels * 4 + 65536,
        )
        result = prepare(
            path,
            budget,
            info.samplerate,
            "preserve",
            item.get("start"),
            item.get("end"),
            input_context,
            parent,
        )
        budget.refresh_disk()
        prepared = result["record"]
        read_charge(budget, prepared["artifact"], context=context)
        x, metadata = decode(budget.root / prepared["artifact"]["local_path"], budget)
        original_meta = prepared["technical_metadata"]
        excluded.update(parents(budget.root, prepared, original_meta["canonical_pcm"]))
        # Equal selected samples cannot silently reweight the same intended sound.
        identity = metadata["canonical_pcm"]["sha256"]
        example = {
            "example_id": identity,
            "prepared": prepared,
            "audio": metadata,
            "pitch": estimate(x, info.samplerate),
        }
        if identity in examples:
            continue
        examples[identity] = example
    ordered = [examples[k] for k in sorted(examples)]
    identity = {
        "version": "a06-query-1",
        "examples": [v["example_id"] for v in ordered],
        "representation": desc,
        "rule": "mean per-example distance; unordered unique PCM",
        "excluded_groups": sorted(excluded),
    }
    if context is not None:
        identity["consumer"] = context.query_binding(spec)
    key = digest(identity)
    directory = (
        context.queries if context is not None else budget.root / "data/runs/search/queries"
    ) / key
    path = directory / "query.json"
    if path.exists():
        saved = record(path)
        if saved["identity"] != identity:
            raise InputError("query identity changed")
        load_array(
            directory / "features" / digest({**identity, "dimension": desc["dimension"]}),
            {**identity, "dimension": desc["dimension"]},
            budget,
        )
        return {
            "status": "ok",
            "query": path.relative_to(budget.root).as_posix(),
            "query_id": key,
            "examples": len(ordered),
            "reused": True,
        }
    charge(
        budget,
        context=context,
        query_jobs=1,
        feature_bytes=len(ordered) * desc["dimension"] * 4 + 65536,
        processed_window_seconds=sum(v["audio"]["duration_seconds"] for v in ordered),
    )
    if context is not None:
        context.charge(budget, feature_windows=len(ordered))
    largest = max(v["audio"]["sample_count"] * v["audio"]["channels"] * 4 for v in ordered)
    budget.reserve(len(ordered) * desc["dimension"] * 4 + 65536, 768 * 1024**2 + largest * 3)
    obj, seconds = adapter(budget, method, desc)
    features = []
    extraction_seconds = 0
    for v in ordered:
        read_charge(budget, v["audio"], context=context)
        x, _ = decode(budget.root / v["prepared"]["artifact"]["local_path"], budget)
        started = time.perf_counter()
        features.append(checked(obj.encode(x, v["audio"]["sample_rate_hz"]), desc["dimension"]))
        extraction_seconds += time.perf_counter() - started
    feat_identity = {**identity, "dimension": desc["dimension"]}
    saved = save_array(directory / "features", feat_identity, np.stack(features), budget)
    value = {
        "schema_version": "a06-query-1",
        "query_id": key,
        "identity": identity,
        "examples": ordered,
        "label": spec.get("label", "Explicit selected sound"),
        "feature_key": digest(feat_identity),
        "feature_hash": saved["record_hash"],
        "adapter_load_seconds": seconds,
        "extraction_seconds": extraction_seconds,
        "peak_working_bytes": memory_check(budget),
    }
    write_record(path, value, budget)
    return {
        "status": "ok",
        "query": path.relative_to(budget.root).as_posix(),
        "query_id": key,
        "examples": len(ordered),
        "reused": False,
    }


def load_query(budget, path, desc, context=None):
    path = contained(
        path, context.queries if context is not None else budget.root / "data/runs/search/queries"
    )
    value = record(path)
    if (
        value["query_id"] != digest(value["identity"])
        or value["identity"]["representation"] != desc
    ):
        raise InputError("search query: stale representation/identity")
    if context is not None:
        context.validate_query(value)
    for v in value["examples"]:
        prepared = v["prepared"]
        original = Path(prepared["source"]["local_path"])
        original = original if original.is_absolute() else budget.root / original
        read_charge(budget, prepared["source"], context=context)
        _, meta = decode(original, budget)
        if meta["sha256"] != prepared["source"]["sha256"]:
            raise InputError("query original changed or missing")
        read_charge(budget, v["audio"], context=context)
        _, current = decode(budget.root / prepared["artifact"]["local_path"], budget)
        if current != v["audio"]:
            raise InputError("query selected audio changed")
    identity = {**value["identity"], "dimension": desc["dimension"]}
    array, meta = load_array(path.parent / "features" / value["feature_key"], identity, budget)
    if meta["record_hash"] != value["feature_hash"]:
        raise InputError("query feature metadata changed")
    return value, array
