"""Explicit compact C02 development import, independent geometry and one paired batch."""

import time

import numpy as np

from ..evaluation.artifacts import record
from ..inputs import decode
from ..retrieval import development as prior
from ..retrieval import engine as prior_engine
from ..retrieval import fusion
from ..storage import InputError, digest
from . import engine, geometry
from .context import Historical


def native_geometry(budget, owner):
    class GeometryView(Historical):
        def publish(self, budget, path, value, immutable=False):
            return self.owner.publish(
                budget, self.owner.directory / "development/geometry.json", value, immutable=True
            )

    # Reuse the independent sample reconstruction/FFT oracle, never its workers.
    return prior.geometry(budget, GeometryView(owner))


def inputs(owner):
    old = Historical(owner)
    fixtures = record(old.directory / "development/fixtures.json")
    encoded = record(old.directory / "development/encoded.json")
    comparison = record(old.directory / "development/comparison.json")
    if (
        encoded["state"] != "complete"
        or comparison["encoded_hash"] != encoded["record_hash"]
        or comparison["fixtures_hash"] != fixtures["record_hash"]
    ):
        raise InputError("C03 completed pinned development inputs required")
    return old, fixtures, encoded, comparison


def adapt(budget, owner, case_id):
    old, fixtures, encoded, comparison = inputs(owner)
    outcome = old.get(comparison["cases"][case_id], "development/outcomes")
    case = outcome["case"]
    if case_id == "silence":
        return case, None, None, None, None, None
    unique = {
        encoded["queries"][n]["example_id"]: encoded["queries"][n] for n in case["query_names"]
    }
    variants = sorted(unique)
    features = np.stack([prior.feature(budget, old, unique[v])[0] for v in variants])
    sources = {i["source"]["recording_id"]: i["source"] for i in fixtures["sources"]}
    arrays = {}
    representation = None
    for rid in sources:
        for ref in encoded["sources"][rid]:
            full = prior.encoding_record(old, ref)
            meta = full["metadata"]
            arr = prior.feature(budget, old, ref)
            arrays[rid, meta["identity"]["bank_hash"]] = (arr, meta, full["path"])
            representation = meta["identity"]["representation"]

    def expand(row, bh, variant=None):
        rid = row["recording_id"]
        arr, meta, path = arrays[rid, bh]
        n = row["row"]
        if n not in range(len(arr)):
            raise InputError("C03 development row index outside pinned array")
        b = meta["identity"]["bounds"][n]
        if row["row_id"] != digest([bh, rid, b]):
            raise InputError("C03 development native row identity differs")
        passage = {
            "row_id": row["row_id"],
            "bank_id": bh,
            "signal_id": rid,
            "shard": digest(meta["identity"]),
            "row": n,
            "signal_bounds": b,
            "original_bounds": b,
            "padding_is_support": False,
        }
        r = prior_engine.evidence(
            sources[rid], bh, passage, row["per_example_distances"], row["distance"]
        )
        per, _ = geometry.scores(features, arr[n : n + 1], {"kind": "mean"}, variants)
        if not np.allclose(per[:, 0], r["per_example_distances"], rtol=0, atol=2e-15):
            raise InputError("C03 compact development row distances differ")
        return r

    groups = {}
    banks = []
    for group, ref in outcome["complete_supports"].items():
        compact = old.get(ref, "development/group-supports")
        if (
            compact["schema_version"] != "c02-development-group-support-1"
            or compact["encoded_hash"] != encoded["record_hash"]
            or compact["fixtures_hash"] != fixtures["record_hash"]
        ):
            raise InputError("C03 compact development fixture/encoding membership differs")
        objs = {}
        for key, obj in compact["objectives"].items():
            bh, variant = key.split(":")
            if bh not in banks:
                banks.append(bh)
            objs[key] = {
                "count": obj["count"],
                "rows": [expand(r, bh, variant) for r in obj["rows"]],
            }
        base_rid = compact["baseline_row"]["recording_id"]
        legacy = prior.encoding_record(old, encoded["sources"][base_rid][0])["metadata"][
            "identity"
        ]["bank_hash"]
        groups[group] = {
            **compact,
            "objectives": objs,
            "baseline_row": expand(compact["baseline_row"], legacy),
        }
    rank = fusion.results(groups, outcome["events"], banks, old.cfg, "event-multi")
    if [g["group"] for g in rank] != outcome["arms"]["event-multi"]["complete_order"]:
        raise InputError("C03 saved development ranking does not reconstruct exactly")
    lookup = {}
    for (rid, bh), (arr, meta, path) in arrays.items():
        for i, b in enumerate(meta["identity"]["bounds"]):
            lookup[rid, tuple(b)] = {
                "vector": arr[i],
                "reference": {
                    "development_bundle": {"path": path, "record_hash": meta["record_hash"]},
                    "row": i,
                    "native_bounds": b,
                },
            }
    return case, rank[:20], features, variants, outcome["events"], (sources, lookup, representation)


def metrics(case, groups, ranked, rate):
    details = []
    all_truth = []
    for group, truths in case["positives"].items():
        for t in truths:
            for b in t["bounds"]:
                all_truth.append((group, t["recording_id"], b))
    for group, rid, b in all_truth:
        rows = [
            r for g in groups if g["group"] == group for r in g["rows"] if r["recording_id"] == rid
        ]
        candidates = [
            {**geometry.overlaps(r["original_bounds"], b), "scored": r["original_bounds"]}
            for r in rows
        ]
        best = max(
            candidates,
            key=lambda x: (x["overlap_frames"], -sum(x["boundary_error_frames"])),
            default=None,
        )
        details.append(
            {
                "group": group,
                "recording_id": rid,
                "truth": b,
                "best": best,
                "start_end_error_seconds": None
                if best is None
                else [v / rate for v in best["boundary_error_frames"]],
                "in_shortlist": group in ranked,
            }
        )
    found = [d for d in details if d["best"] and d["best"]["half_truth"]]
    conditional = [d for d in details if d["in_shortlist"]]
    return {
        "truth_events": len(details),
        "found_events": len(found),
        "all_event_recall": None if not details else len(found) / len(details),
        "at_least_one_event": None if not details else bool(found),
        "conditional_events": len(conditional),
        "conditional_found": sum(d in found for d in conditional),
        "hit": {
            str(k): None
            if not case["positives"]
            else bool(set(ranked[:k]) & set(case["positives"]))
            for k in (1, 5, 10, 20)
        },
        "localization": details,
    }


def compare(budget, owner):
    old, fixtures, encoded, comparison = inputs(owner)
    geom = record(owner.directory / "development/geometry.json")
    if not geom["passed"] or geom["fixtures_hash"] != fixtures["record_hash"]:
        raise InputError("C03 independent native checks required before predictions")
    p = owner.directory / "development/progress.json"
    binding = {
        "comparison": comparison["record_hash"],
        "fixtures": fixtures["record_hash"],
        "encoded": encoded["record_hash"],
        "policy": digest(owner.cfg),
        "protocol": digest(owner.protocol),
    }
    if p.exists():
        state = record(p)
        if state["binding"] != binding or state["state"] == "complete":
            raise InputError("C03 development inputs changed or batch closed")
    else:
        owner.charge(budget, comparison_batches=1, query_jobs=24, case_policy_evaluations=24)
        state = {"binding": binding, "state": "pending", "cases": {}, "active": None}
        owner.publish(budget, p, state)
    cid = next(c for c in owner.protocol["development"]["cases"] if c not in state["cases"])
    case, ranking, features, variants, events, data = adapt(budget, owner, cid)
    if cid == "silence":
        outcome = {
            "case": case,
            "state": "unsupported-silence",
            "arms": {
                a: {"state": "unsupported", "reason": "no nonzero query feature"}
                for a in ("unrefined", "original-local")
            },
        }
    else:
        sources, lookup, desc = data
        if state["active"] is None:
            state["active"] = {"id": cid, "groups": {}}
        if state["active"]["id"] != cid:
            raise InputError("C03 development pending case changed")
        for g in [g for g in ranking if g["group"] not in state["active"]["groups"]][:4]:
            results = []
            decoded = {}
            for psg in g["passages"][:2]:
                a = psg["representative"]
                rid = a["recording_id"]
                source = sources[rid]
                if rid not in decoded:
                    owner.charge(budget, read_audio_seconds=source["source"]["duration_seconds"])
                    x, meta = decode(owner.root / source["source"]["local_path"], budget)
                    if meta != {k: v for k, v in source["source"].items() if k != "local_path"}:
                        raise InputError("C03 development original changed")
                    decoded[rid] = x
                results.append(
                    engine.local(
                        budget,
                        owner,
                        source,
                        decoded[rid],
                        a,
                        features,
                        variants,
                        events,
                        desc,
                        lookup,
                    )
                )
            pilot_path = owner.directory / "pilot-reuse.json"
            if not pilot_path.exists():
                # One measured cold/reuse unit before expansion. Reopen the full source
                # and persistent feature bundle; no cache-backed success hides a decode.
                counts = record(owner.directory / "work.json")["counts"]
                owner.charge(
                    budget, query_jobs=1, read_audio_seconds=source["source"]["duration_seconds"]
                )
                started = time.monotonic()
                again_samples, again_meta = decode(
                    owner.root / source["source"]["local_path"], budget
                )
                if again_meta != {k: v for k, v in source["source"].items() if k != "local_path"}:
                    raise InputError("C03 pilot reuse original changed")
                base_lookup = {k: v for k, v in lookup.items() if "bundle" not in v["reference"]}
                again = engine.local(
                    budget,
                    owner,
                    source,
                    again_samples,
                    a,
                    features,
                    variants,
                    events,
                    desc,
                    base_lookup,
                )
                after = record(owner.directory / "work.json")["counts"]
                if again != results[-1] or after["feature_windows"] != counts["feature_windows"]:
                    raise InputError("C03 cold/reuse unit differs or re-embedded")
                owner.publish(
                    budget,
                    pilot_path,
                    {
                        "schema_version": "c03-pilot-reuse-1",
                        "case": cid,
                        "group": g["group"],
                        "cold_anchor": results[-1],
                        "reuse_seconds": time.monotonic() - started,
                        "new_reuse_features": 0,
                        "full_source_read": True,
                        "passed": True,
                    },
                    immutable=True,
                )
            # Full input evidence and every original representative remain retained.
            value = {
                "schema_version": "c03-development-group-1",
                "group": g["group"],
                "input": g,
                "anchors": geometry.deduplicate(results),
                "input_comparison": comparison["record_hash"],
            }
            state["active"]["groups"][g["group"]] = owner.put(budget, "development/groups", value)
            owner.publish(budget, p, state)
        if len(state["active"]["groups"]) < len(ranking):
            return {
                "status": "ok",
                "state": "in_progress",
                "case": cid,
                "groups": len(state["active"]["groups"]),
            }
        answers = [
            owner.get(state["active"]["groups"][g["group"]], "development/groups") for g in ranking
        ]
        before = [
            {"group": g["group"], "rows": [p["representative"] for p in g["passages"]]}
            for g in ranking
        ]
        selected = [
            {"group": g["group"], "rows": [a["selected"] for a in g["anchors"]]} for g in answers
        ]
        retained = [
            {
                "group": g["group"],
                "rows": [p["representative"] for p in g["input"]["passages"]]
                + [a["selected"] for a in g["anchors"]],
            }
            for g in answers
        ]
        order = [g["group"] for g in ranking]
        bm = metrics(case, before, order, fixtures["rate"])
        sm = metrics(case, selected, order, fixtures["rate"])
        rm = metrics(case, retained, order, fixtures["rate"])
        losses = []
        domains = []
        for group, ts in case["positives"].items():
            for t in ts:
                for b in t["bounds"]:
                    grids = [
                        row
                        for g in answers
                        if g["group"] == group
                        for a in g["anchors"]
                        for row in a["rows"]
                        if row["recording_id"] == t["recording_id"]
                    ]
                    reachable = any(
                        geometry.overlaps(r["original_bounds"], b)["half_truth"] for r in grids
                    )
                    selected_ok = any(
                        d["group"] == group
                        and d["recording_id"] == t["recording_id"]
                        and d["truth"] == b
                        and d["best"]
                        and d["best"]["half_truth"]
                        for d in sm["localization"]
                    )
                    reason = (
                        "shortlist-miss"
                        if group not in order
                        else "anchor-cap-or-local-geometry"
                        if not reachable
                        else "scoring-selection-loss"
                        if not selected_ok
                        else None
                    )
                    domains.append(
                        {
                            "group": group,
                            "recording_id": t["recording_id"],
                            "truth": b,
                            "reachable": reachable,
                            "loss": reason,
                        }
                    )
                    if reason:
                        losses.append(reason)
        if rm["found_events"] < bm["found_events"]:
            raise InputError("C03 original-alternate positive retention guard failed")
        outcome = {
            "case": case,
            "state": "complete",
            "input_order": order,
            "group_order_changed": False,
            "group_refs": state["active"]["groups"],
            "arms": {"unrefined": bm, "original-local": sm},
            "with_retained_originals": rm,
            "domains": domains,
            "losses": losses,
            "distance_minima_are_quality": False,
            "extraction": "omitted",
        }
    state["cases"][cid] = owner.put(budget, "development/outcomes", outcome)
    state["active"] = None
    owner.publish(budget, p, state)
    if len(state["cases"]) < len(owner.protocol["development"]["cases"]):
        return {"status": "ok", "state": "in_progress", "cases": len(state["cases"])}
    result = {
        "schema_version": "c03-development-comparison-1",
        "binding": binding,
        "cases": state["cases"],
        "evaluations": 24,
        "group_ranking": "unchanged",
        "truth": "familiar inspected development; no human relevance",
    }
    owner.publish(budget, owner.directory / "development/comparison.json", result, immutable=True)
    state["state"] = "complete"
    owner.publish(budget, p, state)
    return {"status": "ok", "state": "complete", "cases": 12, "evaluations": 24}
