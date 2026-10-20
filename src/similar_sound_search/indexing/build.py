"""Crash-safe bounded bank publication and one explicit charged reuse pass."""

import time

import numpy as np

from ..evaluation.artifacts import record
from ..matchers.acoustic import checked
from ..matchers.runner import memory_check
from ..search import sources
from ..search.contracts import load_array, save_array
from ..storage import InputError, digest
from . import banks


def progress_path(owner, plan):
    return owner.directory / "build" / (plan["record_hash"] + ".json")


def progress(owner, plan):
    path = progress_path(owner, plan)
    value = (
        record(path)
        if path.exists()
        else {
            "plan_hash": plan["record_hash"],
            "committed": {},
            "attempts": [],
            "failures": {},
        }
    )
    if value["plan_hash"] != plan["record_hash"] or set(value["committed"]) - {
        u["unit_id"] for u in banks.units(plan)
    }:
        raise InputError("C01 build progress: conflicting plan/membership")
    return value


def array_path(owner, unit):
    return owner.features / "banks" / unit["unit_id"]


def committed_units(owner, state):
    values = []
    for key, ref in state["committed"].items():
        from ..storage import contained

        value = record(contained(owner.root / ref["path"], owner.directory / "membership"))
        if value["record_hash"] != ref["record_hash"] or value["unit_id"] != key:
            raise InputError("C01 membership: immutable unit reference changed")
        values.append({k: v for k, v in value.items() if k != "record_hash"})
    return values


def load_signal(budget, owner, signal):
    if signal["kind"] == "original":
        a = signal["audio"]
        # Matches the A06 native decode + model allocation estimate. MP3 is fully
        # decoded/hashed per unit; no claim of cheap random compressed seeking.
        budget.reserve(0, 512 * 1024**2 + a["sample_count"] * a["channels"] * 12 + 32 * 1024**2)
        return sources.load(budget, signal["original"], context=owner)
    from .components import load_component

    return load_component(budget, owner, signal)


def selected_units(owner, plan, scope):
    all_units = banks.units(plan)
    if scope == "full":
        if plan["scope"] == "discovery" and plan["bank"]["identity"]["variant"] == "original":
            decision = record(owner.directory / "admission.json")
            if decision.get("admitted_plan") != plan["record_hash"]:
                raise InputError("C01 full build requires the prospective admission decision")
        return all_units
    if scope != "pilot" or plan["bank"]["identity"]["variant"] != "original":
        raise InputError("C01 pilot scope requires an original candidate bank")
    selected = []
    for source_id in owner.protocol["real_pilot"]["source_ids"]:
        these = [u for u in all_units if u["signal_id"] == source_id]
        if not these:
            raise InputError("C01 pilot: declared source missing from plan: " + source_id)
        selected.extend({u["unit_id"]: u for u in (these[0], these[-1])}.values())
    return selected


def step(budget, owner, plan_path, scope):
    plan = banks.validate_plan(owner, plan_path, producing=True)
    state = progress(owner, plan)
    target = selected_units(owner, plan, scope)
    todo = [u for u in target if u["unit_id"] not in state["committed"]]
    if not todo:
        return {
            "status": "ok",
            "state": "complete",
            "new_windows": 0,
            "note": "membership committed; use verify for a charged source/array reuse pass",
            "coverage": banks.coverage(plan, committed_units(owner, state), state["failures"]),
        }
    unit = todo[0]
    signal = plan["signals"][unit["signal_id"]]
    started = time.perf_counter()
    state["attempts"].append({"unit_id": unit["unit_id"], "state": "pending", "scope": scope})
    owner.publish(
        budget, progress_path(owner, plan), {k: v for k, v in state.items() if k != "record_hash"}
    )
    try:
        samples = load_signal(budget, owner, signal)
        path = array_path(owner, unit)
        recovered = path.exists()
        if recovered:
            _, meta = load_array(path, unit["identity"], budget)
        else:
            bounds = unit["identity"]["bounds"]
            rate = signal["audio"]["sample_rate_hz"]
            n = len(bounds)
            owner.charge(
                budget,
                feature_windows=n,
                feature_bytes=n * unit["identity"]["dimension"] * 4 + 65536,
                processed_window_seconds=sum(b - a for a, b in bounds) / rate,
                **({"pilot_windows": n} if scope == "pilot" or plan["pilot"] else {}),
                **({"component_windows": n} if signal["kind"] == "component" else {}),
            )
            model = owner.model(budget, plan["bank"]["identity"]["representation"])
            array = np.stack(
                [
                    checked(model.encode(samples[a:b], rate), unit["identity"]["dimension"])
                    for a, b in bounds
                ]
            )
            meta = save_array(owner.features / "banks", unit["identity"], array, budget)
        # The validated array becomes visible before its membership. An interrupted
        # publication can recover exactly this bundle without running the model.
        committed = {**unit, "path": path.relative_to(owner.root).as_posix(), "array": meta}
        membership = (
            owner.directory / "membership" / plan["record_hash"] / (unit["unit_id"] + ".json")
        )
        saved = owner.publish(budget, membership, committed, immutable=True)
        state["committed"][unit["unit_id"]] = {
            "path": membership.relative_to(owner.root).as_posix(),
            "record_hash": saved["record_hash"],
        }
        state["attempts"][-1].update(
            state="committed", recovered_array=recovered, wall_seconds=time.perf_counter() - started
        )
        owner.publish(
            budget,
            progress_path(owner, plan),
            {k: v for k, v in state.items() if k != "record_hash"},
        )
    except (InputError, OSError, ValueError, RuntimeError, MemoryError) as exc:
        state["attempts"][-1].update(state="failed", error_type=type(exc).__name__, error=str(exc))
        state["failures"].setdefault(unit["signal_id"], []).append(
            {"unit_id": unit["unit_id"], "error_type": type(exc).__name__, "error": str(exc)}
        )
        owner.publish(
            budget,
            progress_path(owner, plan),
            {k: v for k, v in state.items() if k != "record_hash"},
        )
        raise
    memory_check(budget)
    remaining = len(todo) - 1
    return {
        "status": "ok",
        "state": "in_progress" if remaining else "complete",
        "unit": unit["unit_id"],
        "units_remaining": remaining,
        "new_windows": 0 if recovered else len(unit["identity"]["bounds"]),
        "recovered_array": recovered,
    }


def bank_snapshot(budget, owner, plan_path):
    plan = banks.validate_plan(owner, plan_path)
    state = progress(owner, plan)
    committed = committed_units(owner, state)
    expected = {u["unit_id"]: u for u in banks.units(plan)}
    for unit in committed:
        base = expected[unit["unit_id"]]
        if (
            any(unit[k] != base[k] for k in base)
            or unit["path"] != array_path(owner, unit).relative_to(owner.root).as_posix()
        ):
            raise InputError("C01 snapshot: row membership/order differs from native plan")
        _, meta = load_array(array_path(owner, unit), unit["identity"], budget)
        if meta != unit["array"]:
            raise InputError("C01 snapshot: committed array receipt changed")
    value = {
        "schema_version": "c01-bank-snapshot-1",
        "plan": plan_path.relative_to(owner.root).as_posix(),
        "plan_hash": plan["record_hash"],
        "bank": plan["bank"],
        "committed": sorted(committed, key=lambda u: (u["signal_id"], u["identity"]["bounds"][0])),
        "coverage": banks.coverage(plan, committed, state["failures"]),
        "failures": state["failures"],
    }
    path = owner.indexes / "banks" / (digest(value) + ".json")
    owner.publish(budget, path, value, immutable=True)
    return path, record(path)


def verify(budget, owner, plan_path, scope):
    plan = banks.validate_plan(owner, plan_path)
    state = progress(owner, plan)
    target = selected_units(owner, plan, scope)
    if any(u["unit_id"] not in state["committed"] for u in target):
        raise InputError("C01 reuse: requested membership is incomplete; build/resume first")
    identity = {
        "plan_hash": plan["record_hash"],
        "scope": scope,
        "units": [u["unit_id"] for u in target],
    }
    path = owner.directory / "reuse" / (digest(identity) + ".json")
    current = (
        record(path)
        if path.exists()
        else {"identity": identity, "validated": [], "state": "in_progress"}
    )
    if current["identity"] != identity:
        raise InputError("C01 reuse: conflicting membership")
    if current["state"] == "complete":
        raise InputError("C01 declared reuse pass already complete; no implicit free repeat")
    keys = sorted({u["signal_id"] for u in target})
    for key in [k for k in keys if k not in current["validated"]][:4]:
        load_signal(budget, owner, plan["signals"][key])
        for unit in [u for u in target if u["signal_id"] == key]:
            _, meta = load_array(array_path(owner, unit), unit["identity"], budget)
            ref = state["committed"][unit["unit_id"]]
            if meta != record(owner.root / ref["path"])["array"]:
                raise InputError("C01 reuse: array identity/hash changed")
        current["validated"].append(key)
        current["state"] = "complete" if len(current["validated"]) == len(keys) else "in_progress"
        owner.publish(budget, path, {k: v for k, v in current.items() if k != "record_hash"})
    return {
        "status": "ok",
        "state": current["state"],
        "new_windows": 0,
        "validated_signals": len(current["validated"]),
        "reuse": path.relative_to(owner.root).as_posix(),
    }
