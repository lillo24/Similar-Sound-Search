"""Audited, read-only B01 consumer of one completed historical A06 index."""

import hashlib
from pathlib import Path

from ..evaluation.artifacts import record, write_record
from ..search import sources
from ..search.contracts import (
    PROTECTED,
    code_identity,
    configuration,
    frozen,
    function_identity,
    grid,
    load_array,
    source_function_identity,
)
from ..search.index import shard_identity
from ..storage import InputError, contained, digest, is_link, sha256

INDEX = "d027f2cd5ca817bc320542df16a540346325403bcb967fd248216c8c466731e2"
INDEX_RECORD = "f12be0c64a196039260e40847f079fcb1f10937344f6f44b94e3ed8039c4d58f"
REPAIR = "c0ac65c2de386e2aee70aa80a30965217ebd58174bba4cffef0182045ba5916a"
DECLARATION = "5885ce947f3a4bae9a21c129f19e091bb2778903781b5a6875c75fefe16258b2"
IMMUTABLE = (
    "inputs.py",
    "preparation.py",
    "records.py",
    "catalogue/ingestion.py",
    "matchers/acoustic.py",
    "matchers/efficientat.py",
    "matchers/efficientat_model.py",
    "matchers/models.py",
    "matchers/windows.py",
    "evaluation/scoring.py",
    "evaluation/rendering.py",
    "search/final.py",
    "search/pitch.py",
)
SHARED_FUNCTIONS = {
    "storage.py": ("contained", "digest", "read_json", "sha256"),
    "search/query.py": ("parents",),
    "search/sources.py": ("catalogue", "public_source"),
    "search/report.py": ("pcm16", "stamp", "link", "page", "byte_range"),
}


def audit(root):
    repair = record(root / "manifests/search/execution-repair.json")
    declaration = record(root / "manifests/search/final-check.json")
    integration = record(root / "manifests/events/integration.json")
    if (
        repair["record_hash"] != REPAIR
        or declaration["record_hash"] != DECLARATION
        or repair["before"] != declaration["binding"]["code"]
        or repair["declaration_hash"] != DECLARATION
        or integration["legacy_repair_hash"] != REPAIR
        or integration["legacy_commit"] != "63b51dd42fcb31c314179dadd4369d164011002d"
    ):
        raise InputError("B01 compatibility: historical provenance changed")
    before, after = repair["before"], repair["after"]
    if set(before) != set(after) or {k for k in before if before[k] != after[k]} - set(PROTECTED):
        raise InputError("B01 compatibility: original execution repair is not bounded")
    base = Path(__file__).resolve().parents[1]
    current = code_identity()
    for relative in IMMUTABLE:
        if current.get(relative) != after[relative]:
            raise InputError(
                "B01 compatibility: frozen preprocessing/model/scorer changed: " + relative
            )
    proofs = {**repair["original_sources"], **integration["original_shared_sources"]}
    functions = {**PROTECTED, **SHARED_FUNCTIONS}
    for relative, names in functions.items():
        original = proofs[relative]
        expected_hash = before[relative] if relative in PROTECTED else after[relative]
        if hashlib.sha256(original.encode()).hexdigest() != expected_hash:
            raise InputError("B01 compatibility: original function proof corrupt: " + relative)
        if function_identity(base / relative, names) != source_function_identity(original, names):
            raise InputError("B01 compatibility: feature/math boundary changed: " + relative)
    return {
        "version": "b01-read-only-a06-1",
        "legacy_repair_hash": REPAIR,
        "legacy_declaration_hash": DECLARATION,
        "integration_hash": integration["record_hash"],
        "current_consumer_code": current,
    }


def snapshot(budget, path):
    root = budget.root
    path = contained(path, root / "data/indexes/a06")
    value = record(path)
    if (
        value["index_id"] != INDEX
        or digest(value["identity"]) != INDEX
        or value["record_hash"] != INDEX_RECORD
        or value["state"] != "complete"
    ):
        raise InputError("B01 compatibility: expected the completed frozen A06 index; no rebuild")
    guard = audit(root)
    repair = record(root / "manifests/search/execution-repair.json")
    cfg = configuration(root)
    _, _, _, _, desc = frozen(budget, "efficientat")
    population, groups = sources.catalogue(root)
    if (
        value["identity"]["code"] != repair["before"]
        or value["identity"]["configuration"] != cfg
        or value["identity"]["representation"] != desc
        or value["identity"]["sources"] != [[v["entry_id"], v["record_hash"]] for v in population]
        or value["identity"]["groups_hash"] != groups["record_hash"]
        or len(value["entries"]) != len(population)
    ):
        raise InputError("B01 compatibility: legacy grid/representation/source groups differ")
    nodes = {}
    for original in population:
        key = original["entry_id"]
        progress = record(path.parent / "entries" / (key + ".json"))
        source = sources.public_source(original, groups["entry_groups"][key])
        if (
            progress["source"] != source
            or progress["state"] != "complete"
            or value["entries"].get(key) != "complete"
        ):
            raise InputError("B01 compatibility: completed original identity changed: " + key)
        meta = source["source"]
        bounds = grid(meta["sample_count"], meta["sample_rate_hz"], cfg)
        chunks = [
            bounds[i : i + cfg["windows_per_shard"]]
            for i in range(0, len(bounds), cfg["windows_per_shard"])
        ]
        shards = {}
        for chunk in chunks:
            identity = shard_identity(source, chunk, desc, cfg)
            shard = digest(identity)
            directory = path.parent / "shards" / shard
            saved = record(directory / "record.json")
            if (
                saved["identity"] != identity
                or saved["shape"] != [len(chunk), desc["dimension"]]
                or saved["dtype"] != "float32"
                or is_link(directory)
            ):
                raise InputError("B01 compatibility: shard feature schema changed: " + shard)
            if (
                not (directory / "features.npy").is_file()
                or (directory / "features.npy").stat().st_size != saved["bytes"]
            ):
                raise InputError("B01 compatibility: shard missing/changed size: " + shard)
            shards[shard] = {
                "record_hash": saved["record_hash"],
                "sha256": saved["sha256"],
                "bytes": saved["bytes"],
            }
        if set(progress["shards"]) != set(shards) or len(progress["shards"]) != len(shards):
            raise InputError("B01 compatibility: shard set/grid changed")
        nodes[key] = {
            "entry_record_hash": progress["record_hash"],
            "source_hash": digest(source),
            "shards": shards,
        }
    return (
        value,
        desc,
        cfg,
        {
            "index_id": INDEX,
            "index_record_hash": INDEX_RECORD,
            "legacy_feature_identity": value["identity"],
            "nodes": nodes,
            "audit": guard,
        },
    )


def step(request, budget, context):
    path = Path(request.get("index") or budget.root / "data/indexes/a06" / INDEX / "index.json")
    value, _, _, identity = snapshot(budget, path)
    key = digest(identity)
    directory = context.directory / "compatibility"
    progress_path = directory / (key + ".progress.json")
    receipt_path = directory / (key + ".json")
    state = (
        record(progress_path) if progress_path.exists() else {"identity": identity, "validated": []}
    )
    if state["identity"] != identity:
        raise InputError("B01 compatibility: progress identity changed")
    keys = sorted(value["entries"])
    # One genuine verification/reuse pass; retries retain already validated units.
    for entry in [k for k in keys if k not in state["validated"]][:4]:
        original = record(path.parent / "entries" / (entry + ".json"))["source"]
        metadata = original["source"]
        context.charge(budget, read_audio_seconds=metadata["duration_seconds"])
        source_path = contained(
            budget.root / metadata["local_path"], budget.root / "data/audio/catalogue/originals"
        )
        if sha256(source_path, budget) != metadata["sha256"]:
            raise InputError("B01 compatibility: original bytes changed: " + entry)
        for shard in identity["nodes"][entry]["shards"]:
            directory_shard = path.parent / "shards" / shard
            load_array(directory_shard, record(directory_shard / "record.json")["identity"], budget)
        state["validated"].append(entry)
        write_record(progress_path, state, budget)
    if len(state["validated"]) < len(keys):
        return {
            "status": "ok",
            "state": "in_progress",
            "validated_recordings": len(state["validated"]),
            "cursor": len(state["validated"]),
        }
    receipt = {
        "schema_version": "b01-a06-consumer-1",
        "identity": identity,
        "validated_recordings": len(keys),
        "feature_recomputed": False,
        "source_validation": (
            "original byte hash plus pinned decoder/PCM metadata; search revalidates full decode"
        ),
        "index_path": path.relative_to(budget.root).as_posix(),
    }
    if receipt_path.exists():
        if record(receipt_path)["identity"] != identity:
            raise InputError("B01 compatibility receipt changed")
    else:
        write_record(receipt_path, receipt, budget)
    return {
        "status": "ok",
        "receipt": receipt_path.relative_to(budget.root).as_posix(),
        "recordings": len(keys),
        "shards": sum(len(n["shards"]) for n in identity["nodes"].values()),
        "new_features": 0,
    }


def validate_receipt(budget, path, value, desc, cfg, receipt):
    current, representation, configuration_now, expected = snapshot(budget, path)
    if (
        receipt.get("schema_version") != "b01-a06-consumer-1"
        or receipt["identity"] != expected
        or receipt["validated_recordings"] != len(current["entries"])
        or current != value
        or representation != desc
        or configuration_now != cfg
    ):
        raise InputError(
            "B01 compatibility receipt stale; verify a new receipt, never re-embed legacy features"
        )
