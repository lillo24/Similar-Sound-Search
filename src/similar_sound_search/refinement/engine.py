"""Bounded original crops, compact feature bundles and atomic C04 group commits."""

from pathlib import Path

import numpy as np

from ..evaluation.artifacts import record
from ..events import compatibility
from ..matchers.acoustic import checked
from ..search import sources
from ..search.contracts import code_identity, load_array, save_array
from ..storage import InputError, digest
from . import geometry, importing


def local(budget, owner, source, samples, anchor, features, variants, events, desc, lookup):
    original = anchor["original_bounds"]
    bounds = geometry.positions(
        original, len(samples), source["source"]["sample_rate_hz"], owner.cfg["offset_milliseconds"]
    )
    obj = geometry.objective(anchor, variants, events)
    missing = [b for b in bounds if (source["recording_id"], tuple(b)) not in lookup]
    bundle_ref = None
    if missing:
        identity = {
            "semantic": geometry.semantic(source, missing, desc),
            "dimension": desc["dimension"],
            "version": "c03-native-bundle-1",
        }
        target = owner.features / digest(identity)
        if not target.exists():
            owner.charge(
                budget,
                feature_windows=len(missing),
                processed_window_seconds=sum(b - a for a, b in missing)
                / source["source"]["sample_rate_hz"],
                feature_bytes=len(missing) * desc["dimension"] * 4 + 65536,
            )
            budget.reserve(
                len(missing) * desc["dimension"] * 4 + 65536, 768 * 1024**2 + samples.nbytes * 3
            )
            model = owner.model(budget, desc)
            arr = np.stack(
                [
                    checked(
                        model.encode(samples[a:b], source["source"]["sample_rate_hz"]),
                        desc["dimension"],
                    )
                    for a, b in missing
                ]
            )
            save_array(owner.features, identity, arr, budget)
        arr, meta = load_array(target, identity, budget)
        bundle_ref = {
            "path": target.relative_to(owner.root).as_posix(),
            "record_hash": meta["record_hash"],
        }
        for i, b in enumerate(missing):
            lookup[source["recording_id"], tuple(b)] = {
                "vector": arr[i],
                "reference": {
                    "bundle": bundle_ref,
                    "row": i,
                    "semantic_key": digest(geometry.semantic(source, b, desc)),
                    "native_bounds": b,
                },
            }
    vectors = np.stack([lookup[source["recording_id"], tuple(b)]["vector"] for b in bounds])
    per, values = geometry.scores(features, vectors, obj, variants)
    control = bounds.index(original)
    if not np.allclose(per[:, control], anchor["per_example_distances"], rtol=0, atol=2e-15):
        raise InputError("C03 zero-offset historical control failed")
    if abs(float(values[control]) - anchor["distance"]) > 2e-15:
        raise InputError("C03 zero-offset objective failed")
    choice = geometry.choose(bounds, values, original)
    rows = []
    rate = source["source"]["sample_rate_hz"]
    for i, b in enumerate(bounds):
        rows.append(
            {
                "row_id": digest(geometry.semantic(source, b, desc)),
                "recording_id": source["recording_id"],
                "group": source["group"],
                "rate": rate,
                "original_bounds": b,
                "original_context": [max(0, b[0] - rate), min(len(samples), b[1] + rate)],
                "distance": float(values[i]),
                "per_example_distances": per[:, i].tolist(),
                "feature": lookup[source["recording_id"], tuple(b)]["reference"],
                "original_mixture_verified": True,
                "padding_is_support": False,
            }
        )
    return {
        "schema_version": "c03-anchor-1",
        "input": anchor,
        "objective": obj,
        "grid": bounds,
        "rows": rows,
        "selected": rows[choice],
        "control": rows[control],
        "changed": bounds[choice] != original,
        "state": "refined" if bounds[choice] != original else "unchanged",
        "original_retained_alternate": anchor,
        "feature_bundle": bundle_ref,
        "presence": "forced original-mixture comparison; no calibrated presence claim",
    }


def identity(owner, execution, receipt):
    return {
        "version": "c03-refinement-1",
        "input_execution": owner.protocol["execution"],
        "input_arm": owner.protocol["arm"],
        "query_hash": execution["identity"]["query_hash"],
        "policy": owner.cfg,
        "protocol_hash": digest(owner.protocol),
        "consumer_code": code_identity(),
        "fresh_audit": record(Path(receipt))["record_hash"],
        "consumer_proof": compatibility.audit(owner.root),
    }


def step(request, budget, owner):
    env = importing.environment(
        budget, owner, Path(request["receipt"]), request["execution_ref"], request["arm"]
    )
    old, execution, groups, view, banks, _, _, query, features = env
    ident = identity(owner, execution, request["receipt"])
    progress = owner.directory / "progress.json"
    if progress.exists():
        state = record(progress)
        if state["identity"] != ident:
            raise InputError("C03 retained run inputs/consumer changed; no automatic invalidation")
        if state["state"] == "complete":
            raise InputError("C03 refinement complete; use one explicit reuse pass")
    else:
        owner.charge(budget, query_jobs=1)
        state = {"identity": ident, "state": "pending", "groups": {}, "failed_attempts": []}
        owner.publish(budget, progress, state)
    for g in [g for g in groups if g["group"] not in state["groups"]][:1]:
        try:
            target_sources, _, lookup = importing.group_rows(
                budget, owner, old, g, view, banks, query, features
            )
            anchors = g["passages"][: owner.cfg["anchors_per_group"]]
            decoded = {}
            output = []
            for p in anchors:
                a = p["representative"]
                rid = a["recording_id"]
                source = target_sources[rid]
                if rid not in decoded:
                    decoded[rid] = sources.load(budget, source, context=owner)
                answer = local(
                    budget,
                    owner,
                    source,
                    decoded[rid],
                    a,
                    features,
                    [v["example_id"] for v in query["examples"]],
                    execution["event_map"],
                    query["identity"]["representation"],
                    lookup,
                )
                answer["lineage"] = geometry.lineage(source, query)
                output.append(answer)
            result = {
                "schema_version": "c03-c04-group-1",
                "group": g["group"],
                "rank": g["rank"],
                "input_ref": execution["arms"][request["arm"]]["shortlist"][g["rank"] - 1],
                "input": g,
                "state": "refined" if any(a["changed"] for a in output) else "unchanged",
                "anchors": geometry.deduplicate(output),
                "unprocessed_anchor_count": len(g["passages"]) - len(output),
                "original_rank": g["rank"],
                "ranking_changed": False,
                "unrefined_evidence_retained": True,
                "original_verified": True,
            }
            state["groups"][g["group"]] = owner.put(budget, "groups", result)
        except (InputError, OSError) as exc:
            state["failed_attempts"].append(
                {"group": g["group"], "error": str(exc), "state": "failed"}
            )
            owner.publish(budget, progress, state)
            raise
        owner.publish(budget, progress, state)
    if len(state["groups"]) < len(groups):
        return {"status": "ok", "state": "in_progress", "groups": len(state["groups"])}
    refs = [state["groups"][g["group"]] for g in groups]
    result = {
        "schema_version": "c03-c04-refinement-1",
        "identity": ident,
        "state": "complete",
        "groups": refs,
        "display": refs[:10],
        "input_order": [g["group"] for g in groups],
        "all_input_groups": 20,
        "refined_group_count": sum(owner.get(r, "groups")["state"] == "refined" for r in refs),
        "failures": state["failed_attempts"],
        "rank_policy": "C02 order unchanged; original controls retained",
        "dependency_graph": {
            "c02_execution": owner.protocol["execution"],
            "query": execution["query_ref"],
            "snapshot": owner.protocol["snapshot"],
            "banks": owner.protocol["primary_banks"],
            "fresh_legacy_receipt": str(
                Path(request["receipt"]).relative_to(owner.root).as_posix()
            ),
            "semantic_features": (
                "source PCM/bytes + native bounds + frozen representation; labels excluded"
            ),
            "producer": "identity.consumer_code",
            "consumer": "fresh_legacy_receipt and original row verification",
            "commit_boundary": (
                "immutable feature bundle -> immutable group -> atomic progress pointer "
                "-> execution"
            ),
            "new_work_on": (
                "changed source/native bounds/query/objective/representation; "
                "explicit new stage allowance required"
            ),
            "resume": "same refinement refine --execution PATH --arm event-multi --receipt RECEIPT",
            "C04": "not implemented; no automatic invalidation or cleanup",
        },
    }
    ref = owner.put(budget, "executions", result)
    owner.publish(budget, owner.directory / "execution.json", {"execution": ref})
    state["state"] = "complete"
    owner.publish(budget, progress, state)
    return {
        "status": "ok",
        "state": "complete",
        "execution": ref,
        "groups": 20,
        "refined_groups": result["refined_group_count"],
    }


def reuse(request, budget, owner):
    ref = record(owner.directory / "execution.json")["execution"]
    result = owner.get(ref, "executions")
    env = importing.environment(
        budget, owner, Path(request["receipt"]), request["execution_ref"], request["arm"]
    )
    old, execution, groups, view, banks, _, _, query, features = env
    if result["identity"] != identity(owner, execution, request["receipt"]):
        raise InputError("C03 reuse consumer or dependencies changed")
    p = owner.directory / "reuse.json"
    if p.exists():
        state = record(p)
        if state["state"] == "complete":
            raise InputError("C03 one required reuse already complete")
        if state["execution"] != ref:
            raise InputError("C03 reuse execution changed")
    else:
        owner.charge(budget, query_jobs=1)
        state = {"execution": ref, "state": "pending", "validated": []}
        owner.publish(budget, p, state)
    for g in [g for g in groups if g["group"] not in state["validated"]][:2]:
        source_map, _, lookup = importing.group_rows(
            budget, owner, old, g, view, banks, query, features
        )
        current = owner.get(result["groups"][g["rank"] - 1], "groups")
        for source in source_map.values():
            sources.load(budget, source, context=owner)
        for a in current["anchors"]:
            for r in a["rows"]:
                f = r["feature"]
                if "bundle" in f:
                    path = owner.root / f["bundle"]["path"]
                    meta = record(path / "record.json")
                    arr, meta = load_array(path, meta["identity"], budget)
                    if meta["record_hash"] != f["bundle"]["record_hash"]:
                        raise InputError("C03 reuse feature metadata changed")
                    v = arr[f["row"]]
                else:
                    v = lookup[r["recording_id"], tuple(r["original_bounds"])]["vector"]
                per, values = geometry.scores(
                    features, v[None], a["objective"], [e["example_id"] for e in query["examples"]]
                )
                if not np.allclose(per[:, 0], r["per_example_distances"], rtol=0, atol=2e-15):
                    raise InputError("C03 reused original distances differ")
        state["validated"].append(g["group"])
        owner.publish(budget, p, state)
    state["state"] = "complete" if len(state["validated"]) == 20 else "pending"
    owner.publish(budget, p, state)
    return {
        "status": "ok",
        "state": "complete" if state["state"] == "complete" else "in_progress",
        "groups": len(state["validated"]),
        "new_features": 0,
    }
