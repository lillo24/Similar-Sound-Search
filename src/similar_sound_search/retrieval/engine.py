"""Exact bounded shard scans, compact resumable evidence and the versioned C03 export."""

from pathlib import Path

from ..evaluation.artifacts import record
from ..events import compatibility
from ..indexing import ranking as baseline
from ..indexing import reader
from ..search import sources
from ..search.contracts import code_identity
from ..search.ranking import distances, excluded_source, timbre_key
from ..storage import InputError, digest
from . import fusion, history
from .context import load_query


def read_shortlist(owner, execution_ref, arm=None):
    """Reopen immutable C03 metadata; audio/arrays need the new consumer's own audit."""
    value = owner.get(execution_ref, "executions")
    arm = arm or owner.cfg["default"]
    if (
        value.get("schema_version") != "c02-c03-shortlist-1"
        or value.get("state") != "complete"
        or arm not in value["arms"]
    ):
        raise InputError("C03 import requires a complete explicit C02 arm")
    selected = value["arms"][arm]["shortlist"]
    if len(selected) > owner.cfg["shortlist"]:
        raise InputError("C03 shortlist exceeds its declared cap")
    output = []
    seen = set()
    for rank, ref in enumerate(selected, 1):
        group = owner.get(ref, "c03-groups")
        if (
            group["arm"] != arm
            or group["rank"] != rank
            or group["group"] in seen
            or group["execution_identity_hash"] != digest(value["identity"])
            or group["policy_hash"] != digest(value["identity"]["policy"])
        ):
            raise InputError("C03 shortlist rank/group/policy/execution binding differs")
        owner.get(group["group_support"], "group-supports")
        for source_ref in group["sources"].values():
            owner.get(source_ref, "sources")
        seen.add(group["group"])
        output.append(group)
    return value, output


def evidence(source, bank_hash, passage, per, score):
    return {
        **passage,
        "recording_id": source["recording_id"],
        "group": source["group"],
        "rate": source["source"]["sample_rate_hz"],
        "bank_hash": bank_hash,
        "distance": float(score),
        "per_example_distances": [float(v) for v in per],
        "original_context": [
            max(0, passage["original_bounds"][0] - source["source"]["sample_rate_hz"]),
            min(
                source["source"]["sample_count"],
                passage["original_bounds"][1] + source["source"]["sample_rate_hz"],
            ),
        ],
        "master_offset": source["offset"],
        "master_offset_evidence": source["offset_evidence"],
    }


def scan(budget, owner, view, bank_values, query, features, source_id, variants):
    value = {
        "source_id": source_id,
        "objectives": {},
        "opportunities": {},
        "baseline": None,
        "baseline_row": None,
        "excluded": False,
    }
    source = bank_values[0]["value"]["signals"][source_id]["original"]
    sources.load(budget, source, context=owner)
    value["group"] = source["group"]
    value["source_ref"] = owner.put(
        budget, "sources", {"schema_version": "c02-source-1", "source": source}
    )
    if excluded_source(source, query):
        value["excluded"] = True
        return value
    for number, bank in enumerate(bank_values):
        b = bank["value"]
        bh = bank["binding"]["historical_bank_hash"]
        count = 0
        for unit in (u for u in b["committed"] if u["signal_id"] == source_id):
            array, passages = reader.rows(budget, view, b, unit)
            per, means = distances(features, array, "cosine")
            for i, passage in enumerate(passages):
                if number == 0:
                    candidate = baseline.hit(source, query, per[:, i], means[i], passage)
                    if value["baseline"] is None or timbre_key(candidate) < timbre_key(
                        value["baseline"]
                    ):
                        value["baseline"] = candidate
                        value["baseline_row"] = evidence(source, bh, passage, per[:, i], means[i])
                for q, variant in enumerate(variants):
                    key = bh + ":" + variant
                    obj = value["objectives"].setdefault(key, {"count": 0, "rows": []})
                    row = evidence(source, bh, passage, per[:, i], per[q, i])
                    obj["count"] += 1
                    # Only a bounded candidate set survives each streamed block.
                    obj["rows"] = fusion.retain([*obj["rows"], row], owner.cfg["raw_support_cap"])
            count += len(array)
        value["opportunities"][bh] = count
    return value


def group_sources(values, cfg):
    groups = {}
    for source in sorted(values, key=lambda v: v["source_id"]):
        if source["excluded"]:
            continue
        group = groups.setdefault(
            source["group"],
            {"objectives": {}, "opportunities": {}, "baseline": None, "sources": {}},
        )
        group["sources"][source["source_id"]] = source["source_ref"]
        if source["baseline"] is not None and (
            group["baseline"] is None
            or timbre_key(source["baseline"]) < timbre_key(group["baseline"])
        ):
            group["baseline"], group["baseline_row"] = source["baseline"], source["baseline_row"]
        for bank, count in source["opportunities"].items():
            group["opportunities"][bank] = group["opportunities"].get(bank, 0) + count
        for key, obj in source["objectives"].items():
            target = group["objectives"].setdefault(key, {"count": 0, "rows": []})
            target["count"] += obj["count"]
            target["rows"] = fusion.retain([*target["rows"], *obj["rows"]], cfg["raw_support_cap"])
    return groups


def finish(budget, owner, identity, query, values, bank_values, event_map):
    groups = group_sources(values, owner.cfg)
    banks = [b["binding"]["historical_bank_hash"] for b in bank_values]
    baseline_winners = sorted((v["baseline"] for v in groups.values()), key=timbre_key)
    old = record(
        owner.root
        / "data/runs/indexing/executions"
        / (owner.protocol["delivery"]["baseline_execution"] + ".json")
    )
    same_query = old["query"]["record_hash"] == query["record_hash"]
    if same_query and old["winners"] != baseline_winners:
        raise InputError("C02 legacy-only complete baseline equivalence failed")
    excluded = sorted(
        set(query["identity"]["excluded_groups"]) | {v["group"] for v in values if v["excluded"]}
    )
    if same_query and excluded != old["excluded_groups"]:
        raise InputError("C02 baseline exclusions differ")
    equivalence = (
        {
            "passed": True,
            "c01_execution_hash": old["record_hash"],
            "winner_digest": digest(baseline_winners),
            "exact": "all fields and order",
        }
        if same_query
        else {"passed": None, "reason": "No historical execution of this exact saved query"}
    )
    complete = owner.put(
        budget,
        "baseline-winners",
        {
            "schema_version": "c02-baseline-winners-1",
            "winners": baseline_winners,
            "query_hash": query["record_hash"],
            "complete": True,
            "equivalence": equivalence,
        },
    )
    group_refs = {g: owner.put(budget, "group-supports", v) for g, v in groups.items()}
    arms = {}
    for arm in owner.protocol["fusion"]["arms"]:
        ranking = fusion.results(groups, event_map, banks, owner.cfg, arm)
        refs = []
        for rank, group in enumerate(ranking, 1):
            refs.append(
                owner.put(
                    budget,
                    "c03-groups",
                    {
                        "schema_version": "c02-c03-group-1",
                        "execution_identity_hash": digest(identity),
                        "policy_hash": digest(owner.cfg),
                        "arm": arm,
                        "rank": rank,
                        "sources": groups[group["group"]]["sources"],
                        "group_support": group_refs[group["group"]],
                        "representative_rule": (
                            "rank credit, bank identity, distance, recording/native bounds/row ID"
                        ),
                        **group,
                    },
                )
            )
        arms[arm] = {
            "complete_groups": refs,
            "shortlist": refs[: owner.cfg["shortlist"]],
            "display": refs[: owner.cfg["display"]],
            "eligible_groups": len(refs),
            "score_direction": "lower_better" if arm == "legacy-mean" else "higher_better",
            "shortfall_reason": None
            if len(refs) >= owner.cfg["shortlist"]
            else "fewer eligible groups",
        }
    result = {
        "schema_version": "c02-c03-shortlist-1",
        "identity": identity,
        "state": "complete",
        "query_ref": owner.put(budget, "queries", query),
        "event_map": event_map,
        "arms": arms,
        "complete_supports": group_refs,
        "baseline_winners": complete,
        "excluded_groups": excluded,
        "scored_windows": {b: sum(v["opportunities"].get(b, 0) for v in values) for b in banks},
        "validated_sources": len(values),
        "coverage": (
            "complete scans of selected complete original banks; optional C01 banks "
            "partial and diagnostic only"
        ),
        "presence": "forced candidates; no calibrated threshold or human relevance claim",
    }
    ref = owner.put(budget, "executions", result)
    owner.publish(budget, owner.directory / "execution.json", {"execution": ref})
    return {
        "status": "ok",
        "state": "complete",
        "execution": ref["path"],
        "eligible_groups": len(groups),
        "baseline_equivalence": equivalence["passed"],
        "scored_windows": result["scored_windows"],
    }


def step(request, budget, owner):
    receipt = Path(request["receipt"])
    snapshot, view, bank_values = history.open_snapshot(budget, owner, receipt)
    revision, saved, query, features = load_query(
        budget,
        owner,
        request.get("revision"),
        request.get("materialization"),
        request.get("derived", False),
    )
    desc = bank_values[0]["value"]["bank"]["identity"]["representation"]
    if desc != query["identity"]["representation"]:
        raise InputError("C02 saved query and bank representation differ")
    variants = [v["example_id"] for v in query["examples"]]
    event_map = fusion.events(variants)
    identity = {
        "version": "c02-execution-1",
        "snapshot_hash": snapshot["record_hash"],
        "banks": [v["binding"] for v in bank_values],
        "revision_id": revision["revision_id"],
        "materialization_id": saved["materialization_id"],
        "query_hash": query["record_hash"],
        "query_feature_hash": query["feature_hash"],
        "events": event_map,
        "policy": owner.cfg,
        "protocol_hash": digest(owner.protocol),
        "consumer_code": code_identity(),
        "consumer_audit": digest(compatibility.audit(owner.root)),
        "pitch_weight": 0,
    }
    key = digest(identity)
    active = owner.directory / "active-execution.json"
    if active.exists() and record(active)["identity_hash"] != key:
        raise InputError("C02 execution inputs/consumer conflict with retained active execution")
    if not active.exists():
        owner.publish(budget, active, {"identity_hash": key}, immutable=True)
    path = owner.directory / "progress" / (key + ".json")
    if (owner.directory / "execution.json").exists():
        raise InputError("C02 execution already complete; use retrieval verify for one reuse pass")
    if path.exists():
        state = record(path)
        if state["identity"] != identity:
            raise InputError("C02 interrupted execution inputs/consumer changed")
    else:
        owner.charge(budget, query_jobs=3)
        state = {"identity": identity, "state": "pending", "sources": {}, "failed_attempts": []}
        owner.publish(budget, path, state)
    keys = sorted(bank_values[0]["value"]["signals"])
    for source in [k for k in keys if k not in state["sources"]][:4]:
        try:
            result = scan(budget, owner, view, bank_values, query, features, source, variants)
            state["sources"][source] = owner.put(budget, "scan-sources", result)
        except (InputError, OSError) as exc:
            state["failed_attempts"].append({"source": source, "error": str(exc)})
            owner.publish(budget, path, state)
            raise
        owner.publish(budget, path, state)
    if len(state["sources"]) < len(keys):
        return {"status": "ok", "state": "in_progress", "validated_sources": len(state["sources"])}
    values = [owner.get(state["sources"][k], "scan-sources") for k in keys]
    result = finish(budget, owner, identity, query, values, bank_values, event_map)
    owner.publish(budget, path, {**state, "state": "complete"})
    return result


def verify(request, budget, owner):
    execution = owner.get(record(owner.directory / "execution.json")["execution"], "executions")
    if execution["identity"]["consumer_code"] != code_identity():
        raise InputError("C02 reuse consumer code changed")
    _, view, values = history.open_snapshot(budget, owner, Path(request["receipt"]))
    _, _, query, _ = load_query(budget, owner)
    if query["record_hash"] != execution["identity"]["query_hash"]:
        raise InputError("C02 reuse query differs")
    path = owner.directory / "reuse.json"
    if path.exists():
        state = record(path)
        if state["state"] == "complete":
            raise InputError("C02 one necessary reuse already complete; retain evidence")
        if state["execution_hash"] != execution["record_hash"]:
            raise InputError("C02 reuse execution changed")
    else:
        owner.charge(budget, query_jobs=1)
        state = {"execution_hash": execution["record_hash"], "state": "pending", "validated": []}
        owner.publish(budget, path, state)
    keys = sorted(values[0]["value"]["signals"])
    for key in [k for k in keys if k not in state["validated"]][:4]:
        sources.load(budget, values[0]["value"]["signals"][key]["original"], context=owner)
        for bank in values:
            for unit in (u for u in bank["value"]["committed"] if u["signal_id"] == key):
                reader.rows(budget, view, bank["value"], unit)
        state["validated"].append(key)
        owner.publish(budget, path, state)
    if len(state["validated"]) == len(keys):
        state["state"] = "complete"
        owner.publish(budget, path, state)
    return {
        "status": "ok",
        "state": "complete" if state["state"] == "complete" else "in_progress",
        "validated_sources": len(state["validated"]),
        "new_features": 0,
    }
