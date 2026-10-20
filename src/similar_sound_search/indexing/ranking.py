"""Exact independent per-bank execution with complete group winners and no fusion."""

from pathlib import Path

from ..evaluation.artifacts import record
from ..events import compatibility
from ..search import sources
from ..search.contracts import code_identity
from ..search.ranking import distances, excluded_source, timbre_key
from ..storage import InputError, contained, digest
from . import build, queries, reader


def hit(source, query, per, score, passage):
    a, b = passage["original_bounds"]
    return {
        "recording_id": source["recording_id"],
        "group": source["group"],
        "start_frame": a,
        "end_frame": b,
        "score": float(score),
        "timbre_distance": float(score),
        "per_example_distances": per.tolist(),
        "pitch_contribution": 0,
        "pitch": {"hz": None, "reason": "pitch preference off"},
        "source": source,
        "duration_mismatch_seconds": [
            (b - a) / source["source"]["sample_rate_hz"] - v["audio"]["duration_seconds"]
            for v in query["examples"]
        ],
    }


def save_progress(budget, owner, key, path, state):
    """Publish final group winners once; progress carries compact hashed references."""
    refs = {}
    for group, winner in sorted(state["best"].items()):
        value = {
            "schema_version": "c01-group-winner-1",
            "execution_identity_hash": key,
            "winner": winner,
            "passage": state["passages"][group],
        }
        target = owner.directory / "rank-winners" / key / (digest(value) + ".json")
        saved = owner.publish(budget, target, value, immutable=True)
        refs[group] = {
            "path": target.relative_to(owner.root).as_posix(),
            "record_hash": saved["record_hash"],
        }
    compact = {
        k: v
        for k, v in state.items()
        if k not in {"record_hash", "best", "passages", "winner_references"}
    }
    compact["winner_references"] = refs
    owner.publish(budget, path, compact)


def load_progress(owner, key, path, identity):
    state = record(path)
    if state["identity"] != identity:
        raise InputError("C01 rank progress: bank/query/consumer changed")
    best, passages = {}, {}
    for group, ref in state["winner_references"].items():
        target = contained(owner.root / ref["path"], owner.directory / "rank-winners" / key)
        value = record(target)
        if (
            value.get("schema_version") != "c01-group-winner-1"
            or value["record_hash"] != ref["record_hash"]
            or value["execution_identity_hash"] != key
            or value["winner"]["group"] != group
            or value["winner"]["source"]["group"] != group
            or value["passage"]["bank_id"] != identity["bank_id"]
        ):
            raise InputError("C01 rank progress: immutable group-winner binding changed")
        if target.stem != digest({k: v for k, v in value.items() if k != "record_hash"}):
            raise InputError("C01 rank progress: group-winner identity differs")
        best[group], passages[group] = value["winner"], value["passage"]
    return {**state, "best": best, "passages": passages}


def step(request, budget, owner):
    value = reader.read_bank(
        budget, owner, Path(request["input"]), request.get("allow_partial", False)
    )
    revision, saved, query, features = queries.load(
        budget,
        owner,
        request.get("revision"),
        request.get("materialization"),
        request.get("derived", False),
    )
    if value["bank"]["identity"]["representation"] != query["identity"]["representation"]:
        raise InputError("C01 search: bank and saved-query representations differ")
    audit = compatibility.audit(owner.root)
    identity = {
        "version": "c01-execution-1",
        "bank_hash": value["record_hash"],
        "bank_id": value["bank"]["bank_id"],
        "revision_id": revision["revision_id"],
        "materialization_id": saved["materialization_id"],
        "query_hash": query["record_hash"],
        "pitch_weight": 0,
        "consumer_code": code_identity(),
        "consumer_audit": digest(audit),
    }
    key = digest(identity)
    path = owner.directory / "executions" / (key + ".json")
    if path.exists():
        raise InputError("C01 exact execution already complete; read its immutable winners")
    progress_path = owner.directory / "rank-progress" / (key + ".json")
    if progress_path.exists():
        state = load_progress(owner, key, progress_path, identity)
    else:
        owner.charge(budget, query_jobs=1)
        state = {
            "identity": identity,
            "validated": [],
            "best": {},
            "passages": {},
            "excluded_groups": query["identity"]["excluded_groups"],
            "scored_windows": 0,
        }
        save_progress(budget, owner, key, progress_path, state)
    keys = sorted(value["signals"])
    for source_id in [k for k in keys if k not in state["validated"]][:4]:
        signal = value["signals"][source_id]
        source = signal["original"]
        if signal["kind"] == "original":
            sources.load(budget, source, context=owner)
        else:
            build.load_signal(budget, owner, signal)
            sources.load(budget, source, context=owner)
        if excluded_source(source, query) or set(signal.get("ancestry_groups", [])) & set(
            query["identity"]["excluded_groups"]
        ):
            state["excluded_groups"] = sorted(set(state["excluded_groups"]) | {source["group"]})
            state["validated"].append(source_id)
            continue
        for unit in (u for u in value["committed"] if u["signal_id"] == source_id):
            array, passages = reader.rows(budget, owner, value, unit)
            per, scores = distances(
                features, array, value["bank"]["identity"]["representation"]["distance"]
            )
            for i, passage in enumerate(passages):
                candidate = hit(source, query, per[:, i], scores[i], passage)
                group = source["group"]
                if group not in state["best"] or timbre_key(candidate) < timbre_key(
                    state["best"][group]
                ):
                    state["best"][group] = candidate
                    state["passages"][group] = passage
            state["scored_windows"] += len(array)
        state["validated"].append(source_id)
    save_progress(budget, owner, key, progress_path, state)
    if len(state["validated"]) < len(keys):
        return {
            "status": "ok",
            "state": "in_progress",
            "validated_signals": len(state["validated"]),
        }
    winners = sorted(state["best"].values(), key=timbre_key)
    result = {
        "schema_version": "c01-execution-1",
        "execution_id": key,
        "identity": identity,
        "bank": Path(request["input"]).relative_to(owner.root).as_posix(),
        "bank_hash": value["record_hash"],
        "coverage": value["coverage"],
        "revision": revision,
        "materialization": saved,
        "query": query,
        "winners": winners,
        "passages": state["passages"],
        "candidates": winners[: owner.cfg["results"]],
        "complete_eligible_group_winners": True,
        "eligible_groups": len(winners),
        "excluded_groups": sorted(state["excluded_groups"]),
        "scored_windows": state["scored_windows"],
        "metric": "unordered mean per-example cosine distance; lower better; no presence threshold",
        "scope": "one bank only; no cross-bank fusion",
    }
    if (
        value["schema_version"] == "c01-legacy-reference-1"
        and revision["revision_id"] == owner.protocol["delivery"]["revision"]
    ):
        baseline_path = (
            owner.root
            / "data/runs/queries/executions"
            / (owner.protocol["delivery"]["baseline_execution"] + ".json")
        )
        baseline = record(baseline_path)
        direct = record(
            contained(owner.root / baseline["winners"], owner.root / "data/runs/queries/winners")
        )
        # Exact, complete semantic equality, not merely matching top-ten IDs.
        if (
            direct["record_hash"] != baseline["identity"]["winners_hash"]
            or not direct["complete"]
            or baseline["identity"]["query_hash"] != query["record_hash"]
            or direct["winners"] != winners
            or baseline["excluded_groups"] != result["excluded_groups"]
        ):
            raise InputError(
                "C01 original-only equivalence failed: full winners/query/exclusions differ"
            )
        result["baseline_equivalence"] = {
            "passed": True,
            "baseline_hash": baseline["record_hash"],
            "direct_winners_hash": direct["record_hash"],
            "complete_winners_hash": digest(winners),
            "groups": len(winners),
            "exact_fields": "all winner fields/order/native intervals/distances/query/exclusions",
        }
    owner.publish(budget, path, result, immutable=True)
    return {
        "status": "ok",
        "state": "complete",
        "execution": path.relative_to(owner.root).as_posix(),
        "eligible_groups": len(winners),
        "scored_windows": state["scored_windows"],
        "baseline_equivalence": result.get("baseline_equivalence"),
    }
