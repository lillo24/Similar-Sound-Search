"""One immutable A06 held-out declaration/run; predictions precede shared scoring."""

import platform
import subprocess
import time

import numpy as np

from ..evaluation.artifacts import load_asset, record, write_record
from ..evaluation.scoring import event_matches, ranked, score
from ..matchers.acoustic import checked, distance
from ..matchers.correction import prediction
from ..matchers.models import adapter
from ..matchers.runner import assets_for, memory_check
from ..matchers.windows import POLICY, routes
from ..storage import InputError, digest
from .contracts import (
    CHOICE,
    CONFIG,
    PROTOCOL,
    SUITE,
    code_identity,
    configuration,
    frozen,
    load_array,
    save_array,
)
from .job import charge, read_charge


def self_hash(value):
    return isinstance(value, dict) and value.get("record_hash") == digest(
        {k: v for k, v in value.items() if k != "record_hash"}
    )


def validate_guard(declaration, protocol, pred):
    """An arbitrary stage:A06 object cannot authorize model scoring."""
    if not self_hash(declaration):
        raise InputError(
            "held-out model scores reserved for A06; self-hashed pre-inference declaration required"
        )
    choice = declaration.get("a05_choice")
    shortlist = declaration.get("a05_shortlist")
    binding = declaration.get("binding", {})
    if (
        not self_hash(choice)
        or choice["record_hash"] != CHOICE
        or choice["stage"] != "A05"
        or not self_hash(shortlist)
        or shortlist["record_hash"] != choice["shortlist_hash"]
        or declaration.get("schema_version") != "a06-final-1"
        or declaration.get("stage") != "A06"
        or declaration.get("selected_on") != "development"
        or declaration.get("declared_before_inference") is not True
        or binding.get("choice_hash") != CHOICE
        or binding.get("protocol_hash") != PROTOCOL
        or protocol["record_hash"] != PROTOCOL
        or binding.get("suite_hash") != SUITE
        or binding.get("config_hash") != CONFIG
        or binding.get("method_id") != "efficientat"
        or binding.get("configuration") != choice["configuration"]
        or binding.get("configuration") != shortlist["methods"]["efficientat"]
        or binding.get("shortlist_hash") != shortlist["record_hash"]
        or binding.get("checkpoint") != choice["configuration"]["checkpoint"]
        or binding.get("query_count") != 80
        or binding.get("accounting_owner") != "data/runs/search"
        or binding.get("grid") != POLICY
        or binding.get("split") != "held_out"
        or binding.get("pitch_weight") != 0
        or binding.get("refinement") != "empty"
        or binding.get("attempt") != 1
        or not binding.get("code")
        or not binding.get("environment")
        or declaration.get("run_id") != "a06-final-" + digest(binding)
        or pred.get("run_id") != declaration["run_id"]
        or any(
            pred.get(k) != binding.get(k)
            for k in ("protocol_hash", "suite_hash", "method_id", "config_hash", "configuration")
        )
    ):
        raise InputError("A06 held-out guard: frozen choice/provenance/grid/run binding differs")


def declare(budget):
    choice, shortlist, protocol, suite, desc = frozen(budget)
    cfg = configuration(budget.root)
    path = budget.root / "manifests/search/final-check.json"
    git = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=budget.root, capture_output=True, text=True, check=False
    )
    if git.returncode:
        raise InputError("final declaration: cannot capture committed implementation revision")
    binding = {
        "choice_hash": CHOICE,
        "shortlist_hash": shortlist["record_hash"],
        "protocol_hash": protocol["record_hash"],
        "suite_hash": suite["record_hash"],
        "method_id": "efficientat",
        "configuration": desc,
        "config_hash": digest(desc),
        "checkpoint": desc["checkpoint"],
        "grid": POLICY,
        "split": "held_out",
        "query_count": 80,
        "pitch_weight": 0,
        "refinement": "empty",
        "attempt": 1,
        "code": code_identity(),
        "search_configuration": cfg,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "tools": desc["tools"],
            "torch": "2.6.0+cpu",
            "numerical_threads": 1,
        },
        "implementation_commit": git.stdout.strip(),
        "accounting_owner": "data/runs/search",
        "final_windows_cap": cfg["policy"]["max_final_windows"],
    }
    if path.exists():
        saved = record(path)
        current = {k: v for k, v in binding.items() if k != "implementation_commit"}
        previous = {k: v for k, v in saved["binding"].items() if k != "implementation_commit"}
        if current != previous:
            raise InputError("final declaration immutable; do not mint another held-out attempt")
        return {
            "status": "ok",
            "declaration": path.relative_to(budget.root).as_posix(),
            "run_id": saved["run_id"],
            "reused": True,
        }
    charge(budget, final_attempts=1)
    value = {
        "schema_version": "a06-final-1",
        "stage": "A06",
        "selected_on": "development",
        "declared_before_inference": True,
        "held_out_scores_previously_inspected": False,
        "run_id": "a06-final-" + digest(binding),
        "binding": binding,
        "a05_choice": choice,
        "a05_shortlist": shortlist,
    }
    write_record(path, value, budget)
    return {
        "status": "ok",
        "declaration": path.relative_to(budget.root).as_posix(),
        "run_id": value["run_id"],
        "reused": False,
    }


def declaration_for(budget):
    value = record(budget.root / "manifests/search/final-check.json")
    _, _, protocol, suite, desc = frozen(budget)
    header = {**value["binding"], "run_id": value["run_id"]}
    validate_guard(value, protocol, header)
    if value["binding"]["code"] != code_identity() or value["binding"][
        "search_configuration"
    ] != configuration(budget.root):
        raise InputError("final check: code/search policy changed after declaration; preserve run")
    return value, protocol, suite, desc


def final_shard(asset, bounds, desc):
    return {
        "stage": "A06-held_out",
        "asset_id": asset["asset_id"],
        "audio": asset["audio"],
        "bounds": [list(v) for v in bounds],
        "representation": desc,
        "dimension": desc["dimension"],
    }


def run_step(budget):
    declaration, protocol, suite, desc = declaration_for(budget)
    assets = assets_for(budget, suite)
    routing, queries = routes(suite, assets, "held_out")
    grouped = {}
    for key, route in routing.items():
        grouped.setdefault(route["asset_id"], []).append((key, route))
    directory = budget.root / "data/runs/search/final"
    path = directory / "progress.json"
    progress = (
        record(path)
        if path.exists()
        else {
            "declaration_hash": declaration["record_hash"],
            "state": "in_progress",
            "done": [],
            "load_seconds": 0,
            "extraction_seconds": 0,
            "validation_seconds": 0,
            "peak_working_bytes": 0,
        }
    )
    if progress["declaration_hash"] != declaration["record_hash"]:
        raise InputError("final progress: declaration differs")
    missing = [k for k in sorted(grouped) if k not in progress["done"]]
    if missing:
        budget.reserve(512 * 384 * 4 + 65536, 768 * 1024**2)
        obj, seconds = adapter(budget, "efficientat", desc)
        progress["load_seconds"] += seconds
        processed = 0
        for asset_id in missing:
            items = grouped[asset_id]
            if processed and processed + len(items) > 512:
                break
            asset = assets[asset_id]
            read_charge(budget, asset["audio"])
            started = time.perf_counter()
            samples, _ = load_asset(budget.root, asset_id, budget)
            progress["validation_seconds"] += time.perf_counter() - started
            bounds = [(v["start_frame"], v["end_frame"]) for _, v in items]
            identity = final_shard(asset, bounds, desc)
            shard = directory / "features" / digest(identity)
            if shard.exists():
                load_array(shard, identity, budget)
            else:
                charge(
                    budget,
                    final_windows=len(items),
                    feature_bytes=len(items) * 384 * 4 + 65536,
                    processed_window_seconds=sum(
                        (b - a) / asset["audio"]["sample_rate_hz"] for a, b in bounds
                    ),
                )
                started = time.perf_counter()
                array = np.stack(
                    [
                        checked(obj.encode(samples[a:b], asset["audio"]["sample_rate_hz"]), 384)
                        for a, b in bounds
                    ]
                )
                progress["extraction_seconds"] += time.perf_counter() - started
                save_array(directory / "features", identity, array, budget)
            progress["done"].append(asset_id)
            processed += len(items)
            progress["peak_working_bytes"] = max(
                progress["peak_working_bytes"], memory_check(budget)
            )
            write_record(path, progress, budget)
        if len(progress["done"]) < len(grouped):
            return {
                "status": "ok",
                "state": "in_progress",
                "assets_complete": len(progress["done"]),
                "assets_expected": len(grouped),
            }
    # Sequentially validate each asset on final publication/reuse; only small vectors stay in RAM.
    features = {}
    storage_bytes = 0
    for asset_id, items in grouped.items():
        asset = assets[asset_id]
        read_charge(budget, asset["audio"])
        load_asset(budget.root, asset_id, budget)
        bounds = [(v["start_frame"], v["end_frame"]) for _, v in items]
        identity = final_shard(asset, bounds, desc)
        array, meta = load_array(directory / "features" / digest(identity), identity, budget)
        storage_bytes += meta["bytes"]
        features.update({key: array[i] for i, (key, _) in enumerate(items)})
    started = time.perf_counter()
    outputs = [
        {
            "query_id": q["query_id"],
            "candidate": [
                {k: p[k] for k in ("asset_id", "start_frame", "end_frame")}
                | {"score": distance(features[q["query_route"]], features[p["route"]], "cosine")}
                for p in q["pool"]
            ],
            "refined": [],
        }
        for q in queries
    ]
    rank_seconds = time.perf_counter() - started
    cost = {
        "wall_seconds": progress["load_seconds"] + progress["extraction_seconds"] + rank_seconds,
        "processed_audio_seconds": sum(
            (r["end_frame"] - r["start_frame"]) / r["sample_rate_hz"] for r in routing.values()
        ),
        "storage_bytes": storage_bytes,
        "peak_working_bytes_estimate": 768 * 1024**2,
    }
    pred = prediction(protocol, suite, "efficientat", desc, outputs, "matcher", cost)
    pred.update(run_id=declaration["run_id"], split="held_out")
    pred_path = directory / "predictions.json"
    if pred_path.exists():
        old = record(pred_path)
        if (
            old["queries"] != outputs
            or old["configuration"] != desc
            or old["run_id"] != declaration["run_id"]
        ):
            raise InputError("final saved predictions differ; preserve evidence")
        pred = old
    else:
        # No truth join/scoring occurs before complete prediction publication.
        write_record(pred_path, pred, budget)
        pred = record(pred_path)
    progress.update(
        state="complete", unique_windows=len(routing), queries=len(outputs), cost=pred["cost"]
    )
    write_record(path, progress, budget)
    return {
        "status": "ok",
        "state": "complete",
        "run_id": declaration["run_id"],
        "predictions": pred_path.relative_to(budget.root).as_posix(),
        "queries": len(outputs),
        "windows": len(routing),
        "cost": pred["cost"],
        "peak_working_bytes": progress["peak_working_bytes"],
    }


def score_saved(budget):
    declaration, protocol, suite, _ = declaration_for(budget)
    directory = budget.root / "data/runs/search/final"
    progress = record(directory / "progress.json")
    if progress["state"] != "complete":
        raise InputError("final scoring requires a complete persisted prediction run")
    pred = record(directory / "predictions.json")
    assets = assets_for(budget, suite)
    for asset in assets.values():
        if asset["split"] == "held_out":
            read_charge(budget, asset["audio"])
            load_asset(budget.root, asset["asset_id"], budget)
    result = score(pred, protocol, suite, assets, "held_out", declaration)
    outputs = {v["query_id"]: v for v in pred["queries"]}
    families = {}
    for q in suite["queries"]:
        if q["split"] != "held_out":
            continue
        family = assets[q["query_asset_id"]]["families"][0]
        group = families.setdefault(
            family,
            {
                "queries": 0,
                "targets": 0,
                "at_k": {str(k): {"hit_queries": 0, "recovered_targets": 0} for k in (1, 5, 10)},
            },
        )
        group["queries"] += 1
        group["targets"] += len(q["targets"])
        ordered = ranked(outputs[q["query_id"]]["candidate"], "lower_better", assets)
        for k in (1, 5, 10):
            matches = event_matches(ordered[:k], q["targets"], protocol["matching"]["minimum_iou"])
            group["at_k"][str(k)]["hit_queries"] += bool(matches)
            group["at_k"][str(k)]["recovered_targets"] += len(matches)
    result.update(
        families=families,
        declaration_hash=declaration["record_hash"],
        predictions_hash=pred["record_hash"],
        suite_hash=suite["record_hash"],
        peak_working_bytes=progress["peak_working_bytes"],
        limitations=protocol["limitations"],
        held_out_scores_inspected=True,
    )
    write_record(directory / "scores.json", result, budget)
    write_record(budget.root / "manifests/search/final-results.json", result, budget)
    return {
        "status": "ok",
        "scores": "data/runs/search/final/scores.json",
        "expected_queries": result["expected_queries"],
        "provided_queries": result["provided_queries"],
    }
