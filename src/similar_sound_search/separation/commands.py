"""Explicit B02 command routing; compute always uses the fixed offline owner."""

from pathlib import Path

from ..evaluation.artifacts import write_record
from ..events import compatibility
from ..search import query, ranking
from ..storage import InputError, read_json
from . import artifacts, protocol


def dispatch(request, budget, context):
    action = request["separation_action"]
    path = Path(request["input"]) if request.get("input") else None
    if action == "preflight":
        result = protocol.preflight(budget, context)
        from .geometry import validate

        value = validate(budget, context)
        return {
            **result,
            "geometry_hash": value["record_hash"]
            if "record_hash" in value
            else "data/runs/separation/geometry.json",
        }
    if action == "compatibility":
        return compatibility.step(request, budget, context)
    if action in {"process", "handoff", "prepare-query", "report"} and path is None:
        raise InputError("separation " + action + " requires explicit input JSON")
    if action == "process":
        return artifacts.process(budget, read_json(path), request["mode"], context)
    if action == "handoff":
        return artifacts.handoff(budget, path, request.get("component"), context)
    if action == "prepare-query":
        return query.prepare_query(budget, path, "efficientat", context=context)
    if action == "rank":
        if not request.get("query") or not request.get("index"):
            raise InputError("B02 rank requires --index --query --receipt")
        return ranking.rank(request, budget, context=context)
    if action == "compare":
        from .comparison import step

        return step(budget, context)
    if action == "report":
        from .report import build

        return build(budget, read_json(path), context)
    if action in {"pilot", "known-answer"}:
        from .validation import run

        value = run(budget, context, pilot=action == "pilot")
        write_record(context.directory / (action + ".json"), value, budget)
        return {"status": "ok", **value}
    raise InputError("unsupported B02 operation " + action)
