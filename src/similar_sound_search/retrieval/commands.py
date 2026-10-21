"""Explicit C02 routing and measured memory/population preflight."""

from ..events import compatibility
from ..indexing import banks
from ..indexing.commands import memory_status
from ..storage import InputError, digest
from . import development, engine
from .context import derive_query


def preflight(budget, owner):
    from ..search.contracts import frozen, grid

    path = owner.directory / "preflight.json"
    if path.exists():
        raise InputError("C02 preflight already declared")
    frozen(budget)
    sources = banks.population(owner.root)
    largest = max(v["audio"]["sample_count"] * v["audio"]["channels"] * 4 for v in sources.values())
    peak = 512 * 1024**2 + largest * 3 + 32 * 1024**2
    budget.reserve(0, peak)
    memory = memory_status()
    if memory["available_commit_bytes"] is not None and memory["available_commit_bytes"] < peak:
        raise InputError("C02 available Windows commit is below declared allocation estimate")
    stats = {}
    for ms, hop in [(2400, 250), (4800, 1000)]:
        stats[str(ms)] = {
            k: len(
                grid(
                    v["audio"]["sample_count"],
                    v["audio"]["sample_rate_hz"],
                    {"window_milliseconds": ms, "hop_milliseconds": hop},
                )
            )
            for k, v in sources.items()
        }
    result = {
        "schema_version": "c02-preflight-1",
        "protocol_hash": digest(owner.protocol),
        "memory": memory,
        "worker_allocation_estimate": peak,
        "largest_native_bytes": largest,
        "recordings": len(sources),
        "opportunities": stats,
        "configuration": owner.cfg,
        "new_discovery_features": 0,
        "c01_staging": "retained; denied deletion not retried",
        "namespaces": [
            "data/runs/retrieval",
            "data/features/retrieval",
            "data/audio/retrieval",
            "manifests/retrieval",
            "reports/local/c02",
        ],
    }
    owner.publish(budget, path, result, immutable=True)
    return {"status": "ok", **result}


def dispatch(request, budget, owner):
    action = request["retrieval_action"]
    if action == "preflight":
        return preflight(budget, owner)
    if action == "known-answer":
        from .validation import known_answer

        return known_answer()
    if action == "generate":
        return development.generate(budget, owner)
    if action == "geometry":
        return development.geometry(budget, owner)
    if action == "build-development":
        return development.build(budget, owner)
    if action == "compare":
        return development.compare(budget, owner)
    if action == "diagnostics":
        from .validation import diagnostics

        return diagnostics(budget, owner)
    if action == "compatibility":
        return compatibility.step(request, budget, owner)
    if action == "derive-query":
        return derive_query(
            budget, owner, request.get("revision") or owner.protocol["delivery"]["revision"]
        )
    if action in {"search", "verify"}:
        if not request.get("receipt"):
            raise InputError("C02 search/verify requires its fresh --receipt")
        return (engine.step if action == "search" else engine.verify)(request, budget, owner)
    if action in {"report", "verify-native"}:
        from . import report

        return (report.build if action == "report" else report.verify_native)(budget, owner)
    raise InputError("Unknown C02 action: " + action)
