"""Explicit C01 bank reader; the frozen A06 loader/containment remains unchanged."""

from pathlib import Path

from ..evaluation.artifacts import record
from ..events import compatibility
from ..search.contracts import load_array, union_frames
from ..search.index import coverage as legacy_coverage
from ..storage import InputError, contained, digest
from . import banks, build


def legacy(budget, owner, receipt_path):
    path = owner.root / "data/indexes/a06" / compatibility.INDEX / "index.json"
    value, desc, cfg, _ = compatibility.snapshot(budget, path)
    receipt = record(contained(Path(receipt_path), owner.directory / "compatibility"))
    compatibility.validate_receipt(budget, path, value, desc, cfg, receipt)
    b = banks.bank(
        "legacy-original", desc, {k: cfg[k] for k in ("window_milliseconds", "hop_milliseconds")}
    )
    signals, units = {}, []
    for entry in sorted(value["entries"]):
        state = record(path.parent / "entries" / (entry + ".json"))
        signals[entry] = banks.original_signal(state["source"])
        for key in state["shards"]:
            directory = path.parent / "shards" / key
            meta = record(directory / "record.json")
            units.append(
                {
                    "unit_id": key,
                    "signal_id": entry,
                    "path": directory.relative_to(owner.root).as_posix(),
                    "array_record_hash": meta["record_hash"],
                    "rows": meta["shape"][0],
                }
            )
    cov = legacy_coverage(path.parent, value)
    cov.update(
        state=value["state"],
        shards=len(units),
        expected_windows=cov["windows"],
        unique_seconds=cov["indexed_unique_seconds"],
        encoded_seconds=cov["processed_window_seconds"],
        vector_bytes=cov["windows"] * desc["dimension"] * 4,
        scope="discovery",
        experimental=False,
    )
    return {
        "schema_version": "c01-legacy-reference-1",
        "bank": b,
        "signals": signals,
        "committed": units,
        "legacy_index": value["index_id"],
        "legacy_index_hash": value["record_hash"],
        "receipt": str(Path(receipt_path).relative_to(owner.root).as_posix()),
        "receipt_hash": receipt["record_hash"],
        "coverage": cov,
        "scope": "discovery",
        "new_features": 0,
        "copied_features": 0,
    }


def read_bank(budget, owner, path, allow_partial=False):
    path = contained(Path(path), owner.indexes)
    value = record(path)
    if value.get("schema_version") == "c01-legacy-reference-1":
        expected = legacy(budget, owner, owner.root / value["receipt"])
        if {k: v for k, v in value.items() if k != "record_hash"} != expected:
            raise InputError("C01 legacy reference changed/stale")
        expanded = []
        for ref in value["committed"]:
            meta = record(owner.root / ref["path"] / "record.json")
            if meta["record_hash"] != ref["array_record_hash"] or meta["shape"][0] != ref["rows"]:
                raise InputError("C01 legacy reference: shard receipt/row count differs")
            expanded.append(
                {
                    "unit_id": ref["unit_id"],
                    "signal_id": ref["signal_id"],
                    "path": ref["path"],
                    "identity": meta["identity"],
                    "array": meta,
                }
            )
        return {**value, "committed": expanded}
    if value.get("schema_version") != "c01-bank-snapshot-1" or path.stem != digest(
        {k: v for k, v in value.items() if k != "record_hash"}
    ):
        raise InputError("C01 reader: invalid bank snapshot/schema")
    plan = banks.validate_plan(owner, owner.root / value["plan"])
    if value["plan_hash"] != plan["record_hash"] or value["bank"] != plan["bank"]:
        raise InputError("C01 reader: snapshot/plan bank differs")
    expected = {u["unit_id"]: u for u in banks.units(plan)}
    seen, expanded = set(), []
    for ref in value["committed"]:
        target = owner.directory / "membership" / plan["record_hash"] / (ref["unit_id"] + ".json")
        if (
            set(ref) != {"unit_id", "path", "record_hash"}
            or ref["path"] != target.relative_to(owner.root).as_posix()
        ):
            raise InputError("C01 reader: membership outside declared namespace")
        saved = record(target)
        if saved["record_hash"] != ref["record_hash"] or saved["unit_id"] != ref["unit_id"]:
            raise InputError("C01 reader: immutable membership receipt changed")
        unit = {k: v for k, v in saved.items() if k != "record_hash"}
        if unit["unit_id"] in seen or unit["unit_id"] not in expected:
            raise InputError("C01 reader: duplicate/unknown shard membership")
        seen.add(unit["unit_id"])
        if any(
            unit[k] != expected[unit["unit_id"]][k] for k in ("unit_id", "signal_id", "identity")
        ):
            raise InputError("C01 reader: row order/grid identity differs")
        if unit["path"] != build.array_path(owner, unit).relative_to(owner.root).as_posix():
            raise InputError("C01 reader: array outside declared namespace")
        expanded.append(unit)
    if value["coverage"] != banks.coverage(plan, expanded, value["failures"]):
        raise InputError("C01 reader: coverage/committed membership differs")
    if value["coverage"]["state"] != "complete" and not allow_partial:
        raise InputError("C01 reader: partial bank requires --allow-partial")
    return {
        **value,
        "committed": expanded,
        "signals": plan["signals"],
        "scope": plan["scope"],
        "plan_value": plan,
    }


def rows(budget, owner, value, unit):
    directory = contained(owner.root / unit["path"], owner.root)
    array, meta = load_array(directory, unit["identity"], budget)
    if meta != unit["array"]:
        raise InputError("C01 reader: committed feature receipt/hash differs")
    if value["schema_version"] == "c01-legacy-reference-1":
        signal = value["signals"][unit["signal_id"]]
        passages = []
        for i, bounds in enumerate(unit["identity"]["bounds"]):
            identity = {
                "bank_id": value["bank"]["bank_id"],
                "recording_id": signal["original"]["recording_id"],
                "signal": banks.sample_identity(signal),
                "native_bounds": list(bounds),
                "original_bounds": list(bounds),
            }
            passages.append(
                {
                    "row_id": digest(identity),
                    "bank_id": value["bank"]["bank_id"],
                    "signal_id": unit["signal_id"],
                    "shard": unit["unit_id"],
                    "row": i,
                    "signal_bounds": list(bounds),
                    "original_bounds": list(bounds),
                    "padding_is_support": False,
                }
            )
    else:
        passages = [banks.passage(value["plan_value"], unit, i) for i in range(len(array))]
    if len(passages) != len(array):
        raise InputError("C01 reader: feature rows and sample windows differ")
    return array, passages


def snapshot(budget, owner, receipt_path, plans):
    original = legacy(budget, owner, receipt_path)
    legacy_path = owner.indexes / "legacy" / (digest(original) + ".json")
    owner.publish(budget, legacy_path, original, immutable=True)
    refs = [
        {
            "path": legacy_path.relative_to(owner.root).as_posix(),
            "bank_id": original["bank"]["bank_id"],
            "record_hash": record(legacy_path)["record_hash"],
            "coverage": original["coverage"],
            "kind": "legacy-original",
            "grid": original["bank"]["identity"]["grid"],
        }
    ]
    engineering = []
    union = {}
    for key, signal in original["signals"].items():
        union[key] = {
            "rate": signal["audio"]["sample_rate_hz"],
            "group": signal["original"]["group"],
            "bounds": [[0, signal["audio"]["sample_count"]]],
        }
    for path in plans:
        p, value = build.bank_snapshot(budget, owner, path)
        ref = {
            "path": p.relative_to(owner.root).as_posix(),
            "bank_id": value["bank"]["bank_id"],
            "record_hash": value["record_hash"],
            "coverage": value["coverage"],
            "kind": value["bank"]["identity"]["variant"],
            "grid": value["bank"]["identity"]["grid"],
        }
        plan = banks.validate_plan(owner, path)
        (refs if plan["scope"] == "discovery" else engineering).append(ref)
        if plan["scope"] == "discovery":
            for item in value["coverage"]["sources"].values():
                key = item["recording_id"]
                if key not in union:
                    raise InputError("C01 snapshot component cannot add a new discovery recording")
                union[key]["bounds"].extend(item["original_intervals"])
    optional_partial = any(
        v["coverage"]["state"] != "complete" or isinstance(v["kind"], dict) for v in refs[1:]
    )
    result = {
        "schema_version": "c01-index-snapshot-1",
        "protocol_hash": digest(owner.protocol),
        "state": "partial-optional-banks" if optional_partial else "complete-declared-banks",
        "default_bank": original["bank"]["bank_id"],
        "banks": refs,
        "engineering_banks_outside_discovery": engineering,
        "component_declaration": record(owner.directory / "components.json")
        if (owner.directory / "components.json").exists()
        else None,
        "unique_original_recordings": len(union),
        "unique_groups": len({v["group"] for v in union.values()}),
        "unique_available_file_seconds": sum(
            union_frames(v["bounds"]) / v["rate"] for v in union.values()
        ),
        "query_audio_adds_discovery_recordings": False,
        "interpretation": "separate experimental banks; no combined score or quality promotion",
    }
    path = owner.indexes / "snapshots" / (digest(result) + ".json")
    owner.publish(budget, path, result, immutable=True)
    owner.publish(
        budget,
        owner.directory / "snapshot.json",
        {"snapshot": path.relative_to(owner.root).as_posix()},
    )
    return {
        "status": "ok",
        "snapshot": path.relative_to(owner.root).as_posix(),
        "state": result["state"],
        "banks": [{"path": v["path"], "kind": v["kind"]} for v in refs],
    }
