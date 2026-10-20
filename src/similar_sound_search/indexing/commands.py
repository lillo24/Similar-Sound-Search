"""C01 command ownership, prospective preflight and explicit artifact routing."""

import ctypes
import os
from pathlib import Path

from ..evaluation.artifacts import record
from ..events import compatibility
from ..search.contracts import frozen, grid
from ..storage import InputError, digest
from . import banks, build, components, development, queries, ranking, reader, validation


def memory_status():
    if os.name != "nt":
        return {
            "available_commit_bytes": None,
            "measurement": "Windows commit unavailable; inspect host before inference",
        }

    class Memory(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (k, ctypes.c_ulonglong)
            for k in (
                "total_physical",
                "available_physical",
                "total_page_file",
                "available_page_file",
                "total_virtual",
                "available_virtual",
                "available_extended",
            )
        ]

    value = Memory()
    value.length = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise InputError("C01 memory preflight: GlobalMemoryStatusEx failed")
    return {
        "available_commit_bytes": value.available_page_file,
        "available_physical_bytes": value.available_physical,
        "total_commit_bytes": value.total_page_file,
        "measurement": "Windows GlobalMemoryStatusEx; available commit is not installed RAM",
    }


def preflight(budget, owner):
    path = owner.directory / "preflight.json"
    if path.exists():
        raise InputError("C01 preflight already declared; use its immutable plan paths")
    _, _, _, _, desc = frozen(budget)
    population = banks.population(owner.root)
    ordered = sorted(
        population,
        key=lambda k: (
            population[k]["audio"]["sample_count"] * population[k]["audio"]["channels"],
            k,
        ),
    )
    selected = [ordered[-1], ordered[len(ordered) // 2]]
    if selected != owner.protocol["real_pilot"]["source_ids"] or len(population) != 72:
        raise InputError("C01 preflight: catalogue differs from prospective source selection")
    plans, geometry = {}, {}
    largest = population[ordered[-1]]["audio"]
    peak = 512 * 1024**2 + largest["sample_count"] * largest["channels"] * 12 + 32 * 1024**2
    budget.reserve(0, peak)
    for label, cfg in owner.cfg["candidates"].items():
        p, value = banks.create_plan(budget, owner, label, "original", desc, cfg, population)
        plans[label] = p.relative_to(owner.root).as_posix()
        expected = banks.units(value)
        geometry[label] = {
            "recordings": len(population),
            "windows": sum(len(u["identity"]["bounds"]) for u in expected),
            "shards": len(expected),
            "vector_bytes": sum(len(u["identity"]["bounds"]) for u in expected) * 384 * 4,
            "encoded_seconds": sum(
                sum(b - a for a, b in u["identity"]["bounds"])
                / population[u["signal_id"]]["audio"]["sample_rate_hz"]
                for u in expected
            ),
            "full_decode_read_seconds": sum(
                population[u["signal_id"]]["audio"]["duration_seconds"] for u in expected
            ),
        }
    old = {"window_milliseconds": 2400, "hop_milliseconds": 250}
    geometry["legacy"] = {
        "windows": sum(
            len(grid(v["audio"]["sample_count"], v["audio"]["sample_rate_hz"], old))
            for v in population.values()
        ),
        "new_windows": 0,
        "read_only": True,
    }
    value = {
        "schema_version": "c01-preflight-1",
        "protocol_hash": digest(owner.protocol),
        "configuration": owner.cfg,
        "plans": plans,
        "geometry": geometry,
        "largest_source_id": ordered[-1],
        "largest_native_decoded_bytes": largest["sample_count"] * largest["channels"] * 4,
        "largest_worker_allocation_estimate": peak,
        "memory": memory_status(),
        "namespaces": [
            "data/indexes/c01",
            "data/features/indexing",
            "data/runs/indexing",
            "data/audio/indexing",
            "manifests/indexing",
            "reports/local/c01",
        ],
        "decode_policy": "full native sequential verification per shard; repeated reads charged",
        "default": "legacy-original; pitch off",
        "inference_measured": False,
    }
    owner.publish(budget, path, value, immutable=True)
    return {"status": "ok", **value}


def plan_path(request, owner):
    if request.get("input"):
        return Path(request["input"])
    label = request.get("bank")
    values = record(owner.directory / "preflight.json")["plans"]
    if label not in values:
        raise InputError("C01 build/verify requires a plan input or --bank short/long")
    return owner.root / values[label]


def dispatch(request, budget, owner):
    action = request["indexing_action"]
    if action == "known-answer":
        return validation.known_answer()
    if action == "preflight":
        return preflight(budget, owner)
    if action == "compatibility":
        return compatibility.step(request, budget, owner)
    if action in {"build", "verify"}:
        p = plan_path(request, owner)
        return (build.step if action == "build" else build.verify)(
            budget, owner, p, request["scope"]
        )
    if action == "generate":
        return development.generate(budget, owner, frozen(budget)[-1])
    if action == "derive-query":
        return queries.derive(
            budget, owner, request.get("revision") or owner.protocol["delivery"]["revision"]
        )
    if action == "search":
        if not request.get("input"):
            raise InputError("C01 search requires one explicit bank snapshot input")
        return ranking.step(request, budget, owner)
    if action == "admit":
        return validation.admit(budget, owner, record(owner.directory / "preflight.json"))
    if action == "snapshot":
        if not request.get("receipt"):
            raise InputError("C01 snapshot requires its fresh --receipt")
        plans = [
            owner.root / v for v in record(owner.directory / "preflight.json")["plans"].values()
        ]
        if (owner.directory / "components.json").exists():
            plans.extend(
                owner.root / v for v in record(owner.directory / "components.json")["plans"]
            )
        return reader.snapshot(budget, owner, Path(request["receipt"]), plans)
    if action in {"report", "verify-native"}:
        from . import report

        return (
            report.build(budget, owner)
            if action == "report"
            else report.verify_native(budget, owner)
        )
    fixtures = record(owner.directory / "development/fixtures.json")
    if action == "geometry":
        return validation.geometry(budget, owner, fixtures)
    if action == "compare":
        return development.compare(budget, owner, fixtures, frozen(budget)[-1])
    if action == "components":
        return components.prepare(
            budget, owner, frozen(budget)[-1], banks.population(owner.root), fixtures
        )
    raise InputError("unknown C01 command: " + action)
