"""Small B01 command router and prospectively named local demonstration inputs."""

from pathlib import Path

from ..evaluation.artifacts import record
from ..evaluation.scoring import known_answers
from ..search import query, ranking, report
from ..storage import InputError, read_json
from . import artifacts, compatibility, selection


def inputs(budget, context):
    plan = record(budget.root / "manifests/events/development.json")
    directory = context.directory / "inputs"
    control = record(
        budget.root
        / "manifests/evaluation/assets"
        / (plan["cases"][0]["reference_asset"] + ".json")
    )
    controlled_context = {
        "schema_version": "a02-input-1",
        "kind": "excerpt",
        "recording": {
            "recording_id": control["asset_id"],
            "title": "A04 controlled harmonic development phrase",
            "version": "A04 immutable procedural construction",
            "identity_status": "verified",
            "identity_evidence": control["record_hash"],
        },
        "provenance": {"permitted_use": "Project generated engineering audio"},
        "original_recording_offset_seconds": 0,
        "offset_evidence": "Constructed file timeline",
    }
    ctxpath = directory / "controlled-context.json"
    # A02 context has a strict field set, so its public metadata is plain JSON.
    from ..storage import bounded_json

    bounded_json(ctxpath, controlled_context, budget)
    specs = [
        {
            "schema_version": "b01-source-1",
            "path": control["local_path"],
            "sha256": control["audio"]["sha256"],
            "region": {"start_frame": 0, "end_frame": 57600},
            "context": ctxpath.relative_to(budget.root).as_posix(),
        }
    ]
    for alternative in plan["demo_alternatives"]:
        value = record(
            budget.root
            / "manifests/catalogue/starter/entries"
            / (alternative["entry_id"] + ".json")
        )
        if value["record_hash"] != alternative["record_hash"]:
            raise InputError("B01 named demonstration original changed")
        mapping = value["timestamp_mapping"]
        source = value["source_asset"]
        ctx = {
            "schema_version": "a02-input-1",
            "kind": source["kind"],
            "recording": {
                "recording_id": value["entry_id"],
                "title": value["recording"]["title"],
                "artist": value["recording"]["artist"],
                "version": "A03 provider available file",
                "identity_status": "verified",
                "identity_evidence": value["record_hash"],
            },
            "provenance": {"permitted_use": str(value["acquisition"]["rights"])},
            "original_recording_offset_seconds": mapping["original_recording_offset_seconds"],
        }
        if mapping["original_recording_offset_seconds"] is not None:
            ctx["offset_evidence"] = mapping["offset_evidence"]
        ctxpath = directory / (value["entry_id"] + "-context.json")
        bounded_json(ctxpath, ctx, budget)
        specs.append(
            {
                "schema_version": "b01-source-1",
                "path": source["local_path"],
                "sha256": source["sha256"],
                "region": dict(
                    zip(
                        ("start_seconds", "end_seconds"), alternative["region_seconds"], strict=True
                    )
                ),
                "context": ctxpath.relative_to(budget.root).as_posix(),
            }
        )
    paths = []
    for i, spec in enumerate(specs):
        path = directory / ("controlled.json" if i == 0 else f"alternative-{i}.json")
        bounded_json(path, spec, budget)
        paths.append(path.relative_to(budget.root).as_posix())
    context.charge(budget, managed_output_bytes=65536)
    return {
        "status": "ok",
        "controlled": paths[0],
        "alternatives_in_order": paths[1:],
        "choice_rule": plan["demo_choice_rule"],
        "loulou": "missing; no substitution identity claim",
    }


def dispatch(request, budget, context):
    action = request["events_action"]
    path = Path(request["input"]) if request.get("input") else None
    if action == "inputs":
        return inputs(budget, context)
    if action == "compatibility":
        return compatibility.step(request, budget, context)
    if (
        action in {"propose", "select", "extract", "prepare-query", "report", "event-report"}
        and path is None
    ):
        raise InputError("events " + action + " requires explicit input JSON")
    if action == "propose":
        return artifacts.generate(budget, path, context)
    if action == "select":
        intervals = []
        for interval in request.get("intervals") or []:
            try:
                intervals.append([int(x) for x in interval.split(":")])
            except ValueError as exc:
                raise InputError(
                    "manual intervals: START:END native integer frames required"
                ) from exc
        return selection.select(
            budget, path, context, request.get("ids"), intervals, request.get("auto", False)
        )
    if action == "extract":
        return selection.extract(budget, path, context)
    if action == "prepare-query":
        return query.prepare_query(budget, path, "efficientat", context=context)
    if action == "rank":
        if not request.get("index") or not request.get("query"):
            raise InputError("events rank requires --index, --query and --receipt")
        return ranking.rank(request, budget, context=context)
    if action == "report":
        return report.build(budget, path, context=context)
    if action == "event-report":
        from .report import build

        return build(budget, read_json(path), context)
    if action == "compare":
        from .comparison import step

        return step(budget, context)
    if action == "audit-boundaries":
        from .audit import saved

        return saved(budget, context)
    if action == "known-answer":
        return known_answers(budget, context.directory / "known")
    raise InputError("unsupported B01 operation " + action)
