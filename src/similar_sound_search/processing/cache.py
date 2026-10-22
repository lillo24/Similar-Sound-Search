"""Compact bundle memberships resolve individual semantic rows across all packing."""

import hashlib

import numpy as np

from ..evaluation.artifacts import record
from ..matchers.acoustic import checked
from ..search.contracts import load_array, save_array
from ..storage import InputError, contained, digest
from .contracts import row_key, source_key


def vector_hash(row):
    return hashlib.sha256(np.asarray(row, dtype="<f4").tobytes()).hexdigest()


def lookup(owner, source, desc, budget=None):
    """Metadata-only without budget; with budget reopens every referenced array."""
    result = {}
    for path in sorted((owner.directory / "cache" / source_key(source)).glob("*.json")):
        value = record(path)
        if value.get("schema_version") != "c04-row-bundle-1" or value["source_key"] != source_key(
            source
        ):
            raise InputError("C04 row cache: schema/source identity differs")
        if value["representation"] != desc:
            continue
        array = None
        if budget is not None:
            target = contained(owner.root / value["array_path"], owner.root)
            array, meta = load_array(target, value["array_identity"], budget)
            if meta != value["array_record"]:
                raise InputError("C04 row cache: immutable array receipt changed")
        for item in value["rows"]:
            key = row_key(source, item["native_bounds"], desc)
            if key != item["key"] or not 0 <= item["row"] < value["array_record"]["shape"][0]:
                raise InputError("C04 row cache: semantic native membership differs")
            if array is not None and vector_hash(array[item["row"]]) != item["vector_sha256"]:
                raise InputError("C04 row cache: conflicting feature bytes")
            ref = {
                **item,
                "bundle": value["record_hash"],
                "source_key": source_key(source),
            }
            if key in result and result[key]["vector_sha256"] != ref["vector_sha256"]:
                raise InputError("C04 conflicting bytes for one semantic identity: " + key)
            result.setdefault(key, ref)
    return result


def register(budget, owner, source, desc, bounds, array, path, meta, producer):
    # One metadata record per bundle, never one file per feature vector.
    rows = [
        dict(
            key=row_key(source, b, desc),
            native_bounds=list(b),
            row=i,
            vector_sha256=vector_hash(array[i]),
        )
        for i, b in enumerate(bounds)
    ]
    value = dict(
        schema_version="c04-row-bundle-1",
        source_key=source_key(source),
        representation=desc,
        array_path=path.relative_to(owner.root).as_posix(),
        array_identity=meta["identity"],
        array_record=meta,
        rows=rows,
        producer=producer,
    )
    ref = owner.put(budget, "cache/" + source_key(source), value)
    return rows, ref


def vectors(budget, owner, refs):
    bundles = {}
    output = []
    for ref in refs:
        witness = ref["bundle"]
        if witness not in bundles:
            path = contained(
                owner.directory / "cache" / ref["source_key"] / (witness + ".json"),
                owner.directory / "cache",
            )
            value = record(path)
            if value["record_hash"] != witness or value["source_key"] != ref["source_key"]:
                raise InputError("C04 row bundle reference changed")
            arr, meta = load_array(
                contained(owner.root / value["array_path"], owner.root),
                value["array_identity"],
                budget,
            )
            if meta != value["array_record"]:
                raise InputError("C04 feature producer receipt changed")
            bundles[witness] = value, arr
        value, arr = bundles[witness]
        original = next((r for r in value["rows"] if r["key"] == ref["key"]), None)
        if original != {k: v for k, v in ref.items() if k not in {"bundle", "source_key"}}:
            raise InputError("C04 row reference differs from immutable membership")
        row = arr[ref["row"]]
        if vector_hash(row) != ref["vector_sha256"]:
            raise InputError("C04 row bytes differ")
        output.append(row)
    return np.stack(output) if output else np.empty((0, 0), dtype=np.float32)


def encode(budget, owner, source, desc, samples, bounds, producer, fault=lambda _: None):
    identity = dict(
        version="c04-array-1",
        dimension=desc["dimension"],
        keys=[row_key(source, b, desc) for b in bounds],
    )
    target = owner.features / digest(identity)
    proof_path = owner.directory / "array-producers" / (digest(identity) + ".json")
    if not proof_path.exists():
        if target.exists():
            raise InputError("C04 orphan array lacks a pre-encoding producer proof")
        owner.publish(
            budget, proof_path, dict(identity=identity, producer=producer), immutable=True
        )
    proof = record(proof_path)
    if proof["identity"] != identity:
        raise InputError("C04 feature producer/native identity differs")
    if target.exists():
        arr, meta = load_array(target, identity, budget)
        new = 0
    else:
        owner.charge(
            budget,
            feature_windows=len(bounds),
            processed_window_seconds=sum(b - a for a, b in bounds)
            / source["source"]["sample_rate_hz"],
            feature_bytes=len(bounds) * desc["dimension"] * 4 + 65536,
        )
        fault("reservation")
        budget.reserve(
            len(bounds) * desc["dimension"] * 4 + 65536, 768 * 1024**2 + samples.nbytes * 3
        )
        model = owner.model(budget, desc)
        rate = source["source"]["sample_rate_hz"]
        arr = np.stack(
            [checked(model.encode(samples[a:b], rate), desc["dimension"]) for a, b in bounds]
        )
        fault("temporary")
        meta = save_array(owner.features, identity, arr, budget)
        fault("array")
        new = len(bounds)
    # A valid orphan is adopted only after complete array/identity/hash validation.
    register(budget, owner, source, desc, bounds, arr, target, meta, proof["producer"])
    fault("membership")
    return new
