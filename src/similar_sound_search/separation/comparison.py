"""One fixed development batch; query-side arms plus one equal-support candidate diagnostic."""

import time

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..inputs import decode
from ..search.contracts import code_identity, frozen
from ..search.ranking import distances
from ..storage import InputError, digest, read_json
from . import artifacts, metrics, protocol
from .features import Features

ARMS = {"original": "original", "broad": "harmonic", "guided": "extracted"}


def read(budget, context, spec):
    from ..inputs import probe

    path = budget.root / spec["path"]
    info = probe(path, budget)
    context.charge(budget, read_audio_seconds=info.frames / info.samplerate)
    x, audio = decode(path, budget)
    if audio["sha256"] != spec["sha256"]:
        raise InputError("B02 comparison source changed: " + spec["path"])
    return x, audio


def hits(vector, pool, vectors):
    if vector is None:
        return []
    _, values = distances(vector[None], np.stack(vectors), "cosine")
    return sorted(
        [
            {"asset_id": key, "start_frame": 0, "end_frame": 57600, "score": float(value)}
            for key, value in zip(pool, values, strict=True)
        ],
        key=lambda v: (v["score"], v["asset_id"], v["start_frame"], v["end_frame"]),
    )


def case(budget, context, item, desc):
    features = Features(budget, context, desc)
    pool, vecs = [], []
    for key in item["candidate_assets"]:
        x, asset = protocol.load(budget, context, key)
        pool.append(key)
        vecs.append(features.get(x, asset["audio"]["sample_rate_hz"]))
    spec = read_json(budget.root / item["input"])
    mix, audio = read(budget, context, spec["source"])
    exact, _ = read(budget, context, item["evaluator_target"])
    first, last = item["event"]
    target, mixture = exact[first:last], mix[first:last]
    arms = {}
    for mode, name in ARMS.items():
        result = artifacts.process(budget, spec, mode, context)
        value = record(budget.root / result["transform"])
        output = value["outputs"][name]
        signal, _ = read(
            budget, context, {"path": output["path"], "sha256": output["audio"]["sha256"]}
        )
        selected = signal[first - spec["region"][0] : last - spec["region"][0]]
        context.charge(budget, comparison_queries=1)
        ranked = hits(features.get(selected, audio["sample_rate_hz"]), pool, vecs)
        arms[mode] = {
            "hits": ranked,
            "outcome": metrics.outcome(ranked, item["truth_assets"]),
            "preservation": metrics.preservation(
                selected, target, mixture, audio["sample_rate_hz"]
            ),
            "transform": result["transform"],
            "component": name,
        }
    context.charge(budget, comparison_queries=1)
    oracle = hits(features.get(target, audio["sample_rate_hz"]), pool, vecs)
    arms["oracle"] = {
        "hits": oracle,
        "outcome": metrics.outcome(oracle, item["truth_assets"]),
        "label": "exact inserted target, evaluation-only privileged diagnostic",
    }
    return {"case": item, "arms": arms, "features": features.stats()}


def candidate_diagnostic(budget, context, plan, first_case, desc):
    features = Features(budget, context, desc)
    item = plan["cases"][0]
    qspec = read_json(budget.root / item["input"])
    queries = {}
    for mode in ARMS:
        saved = record(budget.root / first_case["arms"][mode]["transform"])
        out = saved["outputs"][ARMS[mode]]
        x, _ = read(budget, context, {"path": out["path"], "sha256": out["audio"]["sha256"]})
        a, b = item["native_mapping"]["selected_in_region"]
        queries[mode] = features.get(x[a:b], 24000)
    pool = item["candidate_assets"]
    progress = context.directory / "comparison/candidate-progress.json"
    state = (
        record(progress)
        if progress.exists()
        else {"matrices": {"broad": [], "guided": []}, "receipts": [], "completed": [], "costs": []}
    )
    matrices, receipts = state["matrices"], state["receipts"]
    for key in [v for v in pool if v not in state["completed"]][:2]:
        _, asset = protocol.load(budget, context, key)
        # All candidates receive identical native coverage and the same operational
        # audio cue. No target identity or truth enters the extraction interface.
        spec = {
            "schema_version": "b02-process-input-1",
            "source": {"path": asset["local_path"], "sha256": asset["audio"]["sha256"]},
            "region": [0, 57600],
            "event": [0, 57600],
            "cue": qspec["cue"],
            "label": "B02 candidate diagnostic",
        }
        for mode in matrices:
            result = artifacts.process(budget, spec, mode, context)
            receipts.append(
                {
                    "candidate": key,
                    "mode": mode,
                    "cue": digest(qspec["cue"]),
                    "transform": result["transform"],
                }
            )
            saved = record(budget.root / result["transform"])["outputs"][ARMS[mode]]
            x, _ = read(
                budget, context, {"path": saved["path"], "sha256": saved["audio"]["sha256"]}
            )
            vector = features.get(x, 24000)
            matrices[mode].append(vector.tolist() if vector is not None else None)
        state["completed"].append(key)
        write_record(progress, state, budget)
    state["costs"].append(features.stats())
    write_record(progress, state, budget)
    if len(state["completed"]) < len(pool):
        return {"status": "ok", "state": "in_progress", "candidate_pairs": len(receipts)}
    outcomes = {}
    for mode, matrix in matrices.items():
        if any(v is None for v in matrix):
            raise InputError(
                "B02 candidate diagnostic: unsupported silent candidate; retain failure"
            )
        for query_mode in ("original", mode):
            context.charge(budget, comparison_queries=1)
            ranked = hits(queries[query_mode], pool, matrix)
            outcomes[query_mode + "-query/" + mode + "-candidates"] = {
                "hits": ranked,
                "outcome": metrics.outcome(ranked, item["truth_assets"]),
            }
    return {
        "scope": "one predetermined development case, all original candidate passages; "
        "not a global index",
        "case_id": item["case_id"],
        "coverage": "same complete 0..57600 native frames in every candidate arm",
        "outcomes": outcomes,
        "pair_receipts": receipts,
        "features": state["costs"],
    }


def summarize(results):
    positives = [v for v in results if v["case"]["stratum"].startswith("positive")]
    summary = {}
    for mode in (*ARMS, "oracle"):
        summary[mode] = {
            "cases": len(positives),
            "hit_at": {
                str(k): sum(v["arms"][mode]["outcome"]["hit_at"][str(k)] for v in positives)
                for k in (1, 5, 10)
            },
            "failures_or_abstentions": sum(
                v["arms"][mode]["outcome"]["abstained"] for v in positives
            ),
        }
    decisions = {}
    for mode in ("broad", "guided"):
        signals = [v["arms"][mode]["preservation"] for v in positives]
        gains = sum(
            v["arms"][mode]["outcome"]["hit_at"]["1"]
            and not v["arms"]["original"]["outcome"]["hit_at"]["1"]
            for v in positives
        )
        losses = sum(
            v["arms"]["original"]["outcome"]["hit_at"]["1"]
            and not v["arms"][mode]["outcome"]["hit_at"]["1"]
            for v in positives
        )
        retained = all(
            v["attack_projection"] is not None
            and v["tail_projection"] is not None
            and 0.8 <= v["attack_projection"] <= 1.25
            and 0.8 <= v["tail_projection"] <= 1.25
            and v["overload_samples"] == 0
            for v in signals
        )
        quality = float(np.median([v["sdr_improvement_db"] for v in signals]))
        retrieval = (
            gains >= 2
            and losses == 0
            and summary[mode]["hit_at"]["10"] >= summary["original"]["hit_at"]["10"]
        )
        costs = [record_transform_cost(v["arms"][mode]) for v in positives]
        decisions[mode] = {
            "paired_top1_gains": gains,
            "paired_top1_losses": losses,
            "retrieval_gate": retrieval,
            "preservation_gate": retained and quality >= 1,
            "median_sdr_improvement_db": quality,
            "cost_gate": max(costs, default=0) <= 10,
            "promoted": retrieval and retained and quality >= 1 and max(costs, default=0) <= 10,
        }
    return {
        "primary": summary,
        "strata": {
            stratum: {
                mode: {
                    "cases": sum(v["case"]["stratum"] == stratum for v in results),
                    "hit_at": {
                        str(k): sum(
                            v["arms"][mode]["outcome"]["hit_at"][str(k)]
                            for v in results
                            if v["case"]["stratum"] == stratum
                        )
                        for k in (1, 5, 10)
                    },
                }
                for mode in (*ARMS, "oracle")
            }
            for stratum in sorted({v["case"]["stratum"] for v in results})
        },
        "decisions": decisions,
        "default": "original",
        "default_reason": "processing remains opt-in unless every prospective gate passes; "
        "privileged oracle never eligible",
    }


def record_transform_cost(arm):
    # Cost is added from each immutable transformation receipt before aggregation.
    return arm["processing_seconds"]


def step(budget, context):
    declaration = record(budget.root / "manifests/separation/development.json")
    plan = record(context.directory / "preflight.json")
    geometry = record(context.directory / "geometry.json")
    if (
        declaration["preflight_hash"] != plan["record_hash"]
        or declaration["configuration_hash"] != digest(context.cfg)
        or declaration["geometry_hash"] != geometry["record_hash"]
        or geometry["preflight_hash"] != plan["record_hash"]
        or geometry["positive_full_support"] is not True
    ):
        raise InputError("B02 comparison: freeze eligible preflight/configuration before inference")
    _, _, _, _, desc = frozen(budget)
    identity = {"plan": declaration["record_hash"], "code": code_identity(), "representation": desc}
    directory = context.directory / "comparison"
    path = directory / "progress.json"
    if path.exists():
        state = record(path)
        if state["identity"] != identity:
            raise InputError(
                "B02 comparison: code/protocol changed; retain predictions, no replacement batch"
            )
    else:
        context.charge(budget, comparisons=1, query_jobs=1, comparison_cases=len(plan["cases"]))
        state = {"identity": identity, "completed": [], "candidate_diagnostic": None}
        write_record(path, state, budget)
    todo = [c for c in plan["cases"] if c["case_id"] not in state["completed"]]
    if todo:
        item = todo[0]
        started = time.perf_counter()
        value = case(budget, context, item, desc)
        for arm in ARMS:
            value["arms"][arm]["processing_seconds"] = record(
                budget.root / value["arms"][arm]["transform"]
            )["processing_seconds"]
        value["case_seconds"] = time.perf_counter() - started
        write_record(directory / (item["case_id"] + ".json"), value, budget)
        state["completed"].append(item["case_id"])
        write_record(path, state, budget)
        return {
            "status": "ok",
            "state": "in_progress",
            "completed_cases": len(state["completed"]),
            "cursor": len(state["completed"]),
        }
    results = [record(directory / (c["case_id"] + ".json")) for c in plan["cases"]]
    if state["candidate_diagnostic"] is None:
        diagnostic = candidate_diagnostic(budget, context, plan, results[0], desc)
        if diagnostic.get("state") == "in_progress":
            return diagnostic
        write_record(directory / "candidate-diagnostic.json", diagnostic, budget)
        state["candidate_diagnostic"] = True
        write_record(path, state, budget)
    value = {
        "schema_version": "b02-comparison-1",
        "identity": identity,
        "cases": results,
        "candidate_diagnostic": record(directory / "candidate-diagnostic.json"),
        **summarize(results),
    }
    write_record(directory / "summary.json", value, budget)
    return {
        "status": "ok",
        "comparison": (directory / "summary.json").relative_to(budget.root).as_posix(),
        "cases": len(results),
        "decision": value["decisions"],
        "default": value["default"],
    }
