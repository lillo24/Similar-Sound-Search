"""Semantic bank/row identities, immutable plans and original-sample mappings."""

from fractions import Fraction

from ..evaluation.artifacts import record
from ..search import sources
from ..search.contracts import code_identity, grid, union_frames
from ..storage import InputError, digest

ROUNDING = "duration ceil; hop nearest half-up; one unique end-aligned tail; short support unpadded"


def bank(variant, desc, cfg):
    identity = {
        "version": "c01-bank-1",
        "variant": variant,
        "representation": desc,
        "grid": cfg,
        "rounding": ROUNDING,
    }
    return {
        "bank_id": digest(identity),
        "identity": identity,
        "status": "default" if variant == "legacy-original" else "experimental",
    }


def original_signal(source):
    return {
        "signal_id": source["recording_id"],
        "original": source,
        "audio": source["source"],
        "kind": "original",
        "mapping": None,
    }


def sample_identity(signal):
    """Only dependencies that change analyzed samples, not labels/coordinator hashes."""
    a = signal["audio"]
    result = {
        k: a[k]
        for k in (
            "sha256",
            "canonical_pcm",
            "sample_count",
            "sample_rate_hz",
            "channels",
            "decoder",
        )
    }
    if signal["kind"] == "component":
        t = signal["transformation"]
        result["transformation"] = {
            "mode": t["identity"]["mode"],
            "configuration": t["identity"]["configuration"],
            "tools": t["identity"]["tools"],
            "dsp_code": t["identity"]["dsp_code"],
            "source_pcm": t["identity"]["source"]["audio"]["canonical_pcm"],
            "region": t["identity"]["spec"]["region"],
            "processing": t["processing"],
            "component": signal["component"],
            "mapping": signal["mapping"],
        }
        # Broad HPSS consumes no cue. The complete receipt (including an unused
        # recorded cue) remains in the plan, not in the samples-affecting key.
    return result


def original_bounds(signal, bounds):
    if signal["kind"] == "original":
        return list(bounds)
    mapping = signal["mapping"]
    segs = mapping["segments"]
    a = signal["audio"]
    if mapping["basis"] != "file" or len(segs) != 1 or mapping["unmapped_tail_seconds"]:
        raise InputError("C01 component: discontinuous/non-file/unmapped support unsupported")
    seg = segs[0]
    if (
        seg["asset_start_seconds"] != 0
        or abs(seg["asset_end_seconds"] - a["duration_seconds"]) > 1e-8
    ):
        raise InputError("C01 component: mapping does not cover actual native output")
    offset = Fraction(str(seg["source_start_seconds"]))
    scale = Fraction(str(seg["source_seconds_per_asset_second"]))
    if scale <= 0:
        raise InputError("C01 component: non-positive mapping scale")
    rate = signal["original"]["source"]["sample_rate_hz"]
    lo, hi = [(offset + Fraction(v, a["sample_rate_hz"]) * scale) * rate for v in bounds]
    result = [lo.numerator // lo.denominator, -(-hi.numerator // hi.denominator)]
    if not 0 <= result[0] < result[1] <= signal["original"]["source"]["sample_count"]:
        raise InputError("C01 component: output maps outside original recording")
    return result


def units(plan):
    result = []
    for key, signal in sorted(plan["signals"].items()):
        a = signal["audio"]
        windows = grid(a["sample_count"], a["sample_rate_hz"], plan["bank"]["identity"]["grid"])
        for first in range(0, len(windows), plan["rows_per_shard"]):
            bounds = [list(v) for v in windows[first : first + plan["rows_per_shard"]]]
            identity = {
                "version": "c01-shard-1",
                "bank_id": plan["bank"]["bank_id"],
                "recording_id": signal["original"]["recording_id"],
                "signal": sample_identity(signal),
                "bounds": bounds,
                "dimension": plan["bank"]["identity"]["representation"]["dimension"],
            }
            result.append({"unit_id": digest(identity), "signal_id": key, "identity": identity})
    return result


def passage(plan, unit, row):
    signal = plan["signals"][unit["signal_id"]]
    bounds = unit["identity"]["bounds"][row]
    identity = {
        "bank_id": plan["bank"]["bank_id"],
        "recording_id": signal["original"]["recording_id"],
        "signal": sample_identity(signal),
        "native_bounds": bounds,
        "original_bounds": original_bounds(signal, bounds),
    }
    return {
        "row_id": digest(identity),
        "bank_id": plan["bank"]["bank_id"],
        "signal_id": unit["signal_id"],
        "shard": unit["unit_id"],
        "row": row,
        "signal_bounds": bounds,
        "original_bounds": identity["original_bounds"],
        "padding_is_support": False,
    }


def create_plan(budget, owner, label, variant, desc, cfg, signals, scope="discovery", pilot=False):
    value = {
        "schema_version": "c01-bank-plan-1",
        "label": label,
        "bank": bank(variant, desc, cfg),
        "signals": signals,
        "scope": scope,
        "rows_per_shard": owner.cfg["rows_per_shard"],
        "pilot": pilot,
        "configuration": owner.cfg,
        "protocol_hash": digest(owner.protocol),
        "producer": code_identity(),
    }
    path = owner.indexes / "plans" / (digest(value) + ".json")
    owner.publish(budget, path, value, immutable=True)
    return path, record(path)


def validate_plan(owner, path, producing=False):
    from ..storage import contained

    path = contained(path, owner.indexes / "plans")
    value = record(path)
    if (
        value["schema_version"] != "c01-bank-plan-1"
        or digest({k: v for k, v in value.items() if k != "record_hash"}) != path.stem
        or value["configuration"] != owner.cfg
        or value["protocol_hash"] != digest(owner.protocol)
    ):
        raise InputError("C01 plan: schema/configuration/protocol/identity changed")
    b = value["bank"]
    if b != bank(b["identity"]["variant"], b["identity"]["representation"], b["identity"]["grid"]):
        raise InputError("C01 plan: bank identity differs")
    if producing and value["producer"] != code_identity():
        raise InputError("C01 producer changed; retain old plan and explicitly declare a new one")
    return value


def population(root):
    values, groups = sources.catalogue(root)
    return {
        v["entry_id"]: original_signal(
            sources.public_source(v, groups["entry_groups"][v["entry_id"]])
        )
        for v in values
    }


def coverage(plan, committed, failures=None):
    ready = {v["unit_id"]: v for v in committed}
    expected = units(plan)
    rows, per, encoded, raw_bytes = 0, {}, 0.0, 0
    for key, signal in sorted(plan["signals"].items()):
        these = [u for u in expected if u["signal_id"] == key]
        bounds = [b for u in these if u["unit_id"] in ready for b in u["identity"]["bounds"]]
        original = [original_bounds(signal, b) for b in bounds]
        merged, end = [], 0
        for lo, hi in sorted(original):
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(hi, merged[-1][1])
            else:
                merged.append([lo, hi])
        gaps = []
        for lo, hi in merged:
            if lo > end:
                gaps.append([end, lo])
            end = hi
        total = signal["original"]["source"]["sample_count"]
        if end < total:
            gaps.append([end, total])
        seconds = sum(b - a for a, b in bounds) / signal["audio"]["sample_rate_hz"]
        n = sum(len(u["identity"]["bounds"]) for u in these)
        per[key] = {
            "recording_id": signal["original"]["recording_id"],
            "group": signal["original"]["group"],
            "expected_windows": n,
            "ready_windows": len(bounds),
            "state": "complete" if len(bounds) == n else "partial",
            "original_intervals": merged,
            "unindexed_original_gaps": gaps,
            "unique_seconds": union_frames(original)
            / signal["original"]["source"]["sample_rate_hz"],
            "encoded_seconds": seconds,
            "failures": (failures or {}).get(key, []),
        }
        rows += len(bounds)
        encoded += seconds
        raw_bytes += len(bounds) * plan["bank"]["identity"]["representation"]["dimension"] * 4
    return {
        "state": "complete" if len(ready) == len(expected) else "partial",
        "scope": plan["scope"],
        "experimental": True,
        "expected_signals": len(per),
        "ready_signals": sum(bool(v["ready_windows"]) for v in per.values()),
        "complete_signals": sum(v["state"] == "complete" for v in per.values()),
        "expected_windows": sum(v["expected_windows"] for v in per.values()),
        "windows": rows,
        "shards": len(ready),
        "vector_bytes": raw_bytes,
        "array_file_bytes": sum(v["array"]["bytes"] for v in committed),
        "unique_seconds": sum(v["unique_seconds"] for v in per.values()),
        "encoded_seconds": encoded,
        "sources": per,
    }
