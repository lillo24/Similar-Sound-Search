"""Sequential development-only inference, persistent progress and explicit diagnostics."""

import time

import numpy as np

from ..evaluation.artifacts import load_asset, record, write_record
from ..evaluation.scoring import known_answers, score_file
from ..evaluation.suite import load_suite, validate
from ..storage import InputError, read_json
from . import cache
from .acoustic import distance
from .correction import prediction
from .job import charge
from .models import acquire, adapter, descriptor, shortlist
from .selection import compare
from .windows import routes


def peak_memory():
    import sys

    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (k, ctypes.c_size_t)
                for k in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ]

        counts = Counters()
        counts.cb = ctypes.sizeof(counts)
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        ctypes.windll.psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counts), counts.cb
        ):
            raise InputError("memory evidence: GetProcessMemoryInfo failed")
        return counts.PeakWorkingSetSize
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
        1 if sys.platform == "darwin" else 1024
    )


def memory_check(budget):
    value = peak_memory()
    budget.cap("max_working_bytes", value, "measured worker peak RSS/working set")
    return value


def assets_for(budget, suite):
    assets = {
        k: record(budget.root / "manifests/evaluation/assets" / (k + ".json"))
        for k in suite["assets"]
    }
    if any(v["record_hash"] != suite["asset_record_hashes"][k] for k, v in assets.items()):
        raise InputError("A05: asset metadata differs from frozen suite")
    return assets


def run_batch(budget, settings, protocol, suite, assets, frozen, method):
    if method not in frozen["methods"]:
        raise InputError("run: explicit shortlisted method required")
    desc = frozen["methods"][method]
    routing, queries = routes(suite, assets)
    directory = budget.root / "data/runs/matchers"
    progress_path = directory / (method + "-progress.json")
    if progress_path.exists():
        progress = record(progress_path)
        if progress["shortlist_hash"] != frozen["record_hash"]:
            raise InputError("A05 progress: stale shortlist")
    else:
        charge(budget, settings, model_runs=1)
        progress = {
            "shortlist_hash": frozen["record_hash"],
            "state": "in_progress",
            "done": [],
            "load_seconds": 0,
            "load_calls": 0,
            "peak_working_bytes": 0,
        }
        write_record(progress_path, progress, budget)
    # Inputs are fully decoded/hashed before any feature/cache is accepted, including repeats.
    samples = {}
    for route in routing.values():
        key = route["asset_id"]
        if key not in samples:
            x, _ = load_asset(budget.root, key, budget)
            samples[key] = x
    all_features, all_meta, missing = {}, {}, []
    for key, route in routing.items():
        cached = cache.get(budget, route, desc)
        if cached:
            all_features[key], all_meta[key] = cached
        else:
            if key in progress["done"]:
                raise InputError("A05 progress: completed feature missing; preserve evidence")
            missing.append(key)
    if progress["state"] == "complete":
        charge(budget, settings, model_runs=1)
        if missing:
            raise InputError("A05 complete run cache unexpectedly missing")
        saved = record(directory / (method + "-predictions.json"))
        if (
            saved["protocol_hash"] != protocol["record_hash"]
            or saved["suite_hash"] != suite["record_hash"]
            or saved["configuration"] != desc
            or len(saved["queries"]) != len(queries)
        ):
            raise InputError("A05 completed predictions stale/incomplete")
        # The repeated operation retains measured cold model cost, never zero cache-hit cost.
        return {
            "status": "ok",
            "state": "complete",
            "method": method,
            "reused_features": len(routing),
            "prediction": (directory / (method + "-predictions.json"))
            .relative_to(budget.root)
            .as_posix(),
            "cold_cost_retained": True,
        }
    if missing:
        obj, seconds = adapter(budget, method, desc)
        progress["load_seconds"] += seconds
        progress["load_calls"] += 1
        write_record(progress_path, progress, budget)
        for key in missing[: settings["windows_per_worker"]]:
            route = routing[key]
            selected = samples[route["asset_id"]][route["start_frame"] : route["end_frame"]]
            all_features[key], all_meta[key] = cache.put(
                budget, settings, route, desc, obj, selected
            )
            progress["done"].append(key)
            progress["peak_working_bytes"] = max(
                progress["peak_working_bytes"], memory_check(budget)
            )
        write_record(progress_path, progress, budget)
        if len(missing) > settings["windows_per_worker"]:
            return {
                "status": "ok",
                "state": "in_progress",
                "completed": len(all_features),
                "expected": len(routing),
                "method": method,
            }
    started = time.perf_counter()
    outputs = []
    for q in queries:
        values = [
            {k: p[k] for k in ("asset_id", "start_frame", "end_frame")}
            | {
                "score": distance(
                    all_features[q["query_route"]], all_features[p["route"]], desc["distance"]
                )
            }
            for p in q["pool"]
        ]
        outputs.append({"query_id": q["query_id"], "candidate": values, "refined": []})
    ranking_seconds = time.perf_counter() - started
    extraction_seconds = sum(v["extraction_seconds"] for v in all_meta.values())
    cost = {
        "wall_seconds": progress["load_seconds"] + extraction_seconds + ranking_seconds,
        "processed_audio_seconds": sum(v["audio_seconds"] for v in all_meta.values()),
        "storage_bytes": sum(v["bytes"] for v in all_meta.values()),
        "peak_working_bytes_estimate": 768 * 1024 * 1024
        if method == "efficientat"
        else 64 * 1024 * 1024,
    }
    # Persist complete predictions before any join with construction truth.
    pred = prediction(protocol, suite, method, desc, outputs, "matcher", cost)
    write_record(directory / (method + "-predictions.json"), pred, budget)
    progress.update(
        {
            "state": "complete",
            "unique_windows": len(routing),
            "extraction_seconds": extraction_seconds,
            "ranking_seconds": ranking_seconds,
            "cost": cost,
        }
    )
    write_record(progress_path, progress, budget)
    return {
        "status": "ok",
        "state": "complete",
        "method": method,
        "queries": len(outputs),
        "unique_windows": len(routing),
        "cost": cost,
        "measured_peak_working_bytes": progress["peak_working_bytes"],
        "load_calls": progress["load_calls"],
        "load_seconds": progress["load_seconds"],
        "extraction_seconds": extraction_seconds,
        "ranking_seconds": ranking_seconds,
    }


def dispatch(request, budget):
    action, method, settings = request["matcher_action"], request.get("method"), request["policy"]
    if action == "acquire":
        return acquire(budget, settings)
    protocol, suite = load_suite(budget)
    if "comparison_interval_policy" not in protocol:
        raise InputError("A05: run prospective matchers freeze before inference")
    if action == "validate":
        return validate(budget, "all")
    if action == "known-answer":
        return known_answers(budget)
    if action == "score":
        if not request.get("input"):
            raise InputError("matchers score: explicit predictions required")
        return score_file(budget, read_json(request["input"]), "development")
    if action == "smoke":
        if method not in {"acoustic", "efficientat"}:
            raise InputError("adapter smoke: explicit method required")
        desc = descriptor(budget.root, method)
        charge(budget, settings, smoke_windows=3, processed_windows=3)
        obj, loading = adapter(budget, method, desc)
        tone = np.sin(2 * np.pi * 440 * np.arange(57600) / 24000).astype(np.float32) * 0.1
        result = []
        for samples in (tone, np.zeros(24, dtype=np.float32), np.stack([tone, tone * 0.5], axis=1)):
            started = time.perf_counter()
            vector = obj.encode(samples, 24000)
            result.append(
                {
                    "input_shape": list(samples.shape),
                    "dimension": len(vector),
                    "finite": bool(np.isfinite(vector).all()),
                    "inference_seconds": time.perf_counter() - started,
                }
            )
        return {
            "status": "ok",
            "method": method,
            "load_seconds": loading,
            "cases": result,
            "measured_peak_working_bytes": memory_check(budget),
            "model_quality": "not evaluated by smoke",
        }
    assets = assets_for(budget, suite)
    frozen = shortlist(budget, protocol, suite)
    if action == "run":
        return run_batch(budget, settings, protocol, suite, assets, frozen, method)
    if action == "compare":
        # Verify actual development inputs again before scoring complete persisted files.
        for key, a in assets.items():
            if a["split"] == "development":
                load_asset(budget.root, key, budget)
        return compare(budget, protocol, suite, assets, frozen)
    raise InputError("A05 unsupported operation " + action)
