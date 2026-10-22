"""Explicit C03 commands; geometry/cost preflight before any expansion."""

from pathlib import Path

from ..events import compatibility
from ..indexing.commands import memory_status
from ..search.contracts import frozen
from ..storage import InputError, digest
from . import development, engine, importing


def preflight(budget, owner):
    frozen(budget)
    old, execution, groups = importing.shortlist(
        owner, owner.protocol["execution"], owner.protocol["arm"]
    )
    geometry = []
    largest = 0
    for g in groups:
        for p in g["passages"][:2]:
            a = p["representative"]
            source = old.get(g["sources"][a["recording_id"]], "sources")["source"]
            meta = source["source"]
            largest = max(largest, meta["sample_count"] * meta["channels"] * 4)
            grid = engine.geometry.positions(
                a["original_bounds"],
                meta["sample_count"],
                meta["sample_rate_hz"],
                owner.cfg["offset_milliseconds"],
            )
            geometry.append(
                {
                    "group": g["group"],
                    "rank": g["rank"],
                    "anchor": a["row_id"],
                    "bank": a["bank_hash"],
                    "original": a["original_bounds"],
                    "grid": grid,
                }
            )
    peak = 768 * 1024**2 + largest * 3
    budget.reserve(0, peak)
    memory = memory_status()
    if memory["available_commit_bytes"] is not None and memory["available_commit_bytes"] < peak:
        raise InputError("C03 Windows available commit below native/model allocation estimate")
    result = {
        "schema_version": "c03-preflight-1",
        "protocol_hash": digest(owner.protocol),
        "input_execution": owner.protocol["execution"],
        "arm": owner.protocol["arm"],
        "groups": 20,
        "geometry": geometry,
        "maximum_delivery_windows": sum(len(v["grid"]) for v in geometry),
        "worker_allocation_estimate": peak,
        "memory": memory,
        "configuration": owner.cfg,
        "reserve_delivery_seconds": 1500,
        "development_expansion": "only after first two completed cold/reuse units measured",
        "extraction": "omitted: no separator input, query cue or arbitrary Loulou truncation",
        "c01_staging": "inventoried and retained; denied deletion untouched",
        "namespaces": [
            "data/runs/refinement",
            "data/features/refinement",
            "data/audio/refinement",
            "manifests/refinement",
            "reports/local/c03",
        ],
    }
    owner.publish(budget, owner.directory / "preflight.json", result, immutable=True)
    return {"status": "ok", **result}


def dispatch(request, budget, owner):
    action = request["refinement_action"]
    if action == "preflight":
        return preflight(budget, owner)
    if action == "known-answer":
        from .validation import known_answer

        return known_answer()
    if action == "geometry":
        return development.native_geometry(budget, owner)
    if action == "compatibility":
        return compatibility.step(request, budget, owner)
    if action == "compare":
        return development.compare(budget, owner)
    if action == "derive-query":
        from ..retrieval.context import derive_query

        return derive_query(budget, owner, owner.protocol["delivery"]["revision"])
    if action in {"refine", "verify"}:
        if not request.get("execution") or not request.get("arm") or not request.get("receipt"):
            raise InputError("C03 requires explicit --execution, --arm and fresh --receipt")
        ref = owner.protocol["execution"]
        if Path(request["execution"]).resolve() != (owner.root / ref["path"]).resolve():
            raise InputError("C03 execution must match pinned immutable reference")
        return (engine.step if action == "refine" else engine.reuse)(
            {**request, "execution_ref": ref}, budget, owner
        )
    if action in {"report", "verify-native"}:
        from . import report

        return (report.build if action == "report" else report.verify_native)(budget, owner)
    raise InputError("Unknown C03 action: " + action)
