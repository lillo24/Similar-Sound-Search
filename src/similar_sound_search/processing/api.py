"""D01 metadata API: immutable plans, job status, cancellation and bounded inventory."""

import os
import re
from pathlib import Path

from ..evaluation.artifacts import record
from ..matchers.models import descriptor
from ..resources import CatalogueBudget
from ..storage import InputError, atomic_json, contained, digest, project_lock, read_json
from . import cache, contracts
from .context import Context


def reference(owner, path, kind):
    path = contained(path, owner.directory / kind)
    value = record(path)
    if path.stem != value["record_hash"]:
        raise InputError("C04 expected content-addressed immutable " + kind)
    return {"path": path.relative_to(owner.root).as_posix(), "record_hash": value["record_hash"]}


def graph(value):
    units = []

    def add(kind, subject, dependencies):
        item = dict(kind=kind, subject=subject, dependencies=dependencies)
        item["unit_id"] = digest(item)
        units.append(item)
        return item["unit_id"]

    features = {
        s["recording_id"]: add("features", s["recording_id"], [])
        for s in sorted(value["sources"], key=lambda s: s["recording_id"])
    }
    query = add("query", "query", [])
    scores = [add("score", key, [features[key], query]) for key in sorted(features)]
    aggregate = add("aggregate", "population", scores)
    if value["refinement"] == "historical":
        aggregate = add("refinement", "historical", [aggregate, query])
    add("publish", "complete", [aggregate])
    return units


def plan(root, limits, request, previous=None):
    """Metadata only. Reuse is a candidate until run verifies source PCM and arrays."""
    with project_lock(root, ".c04-coordinator.lock"):
        owner, budget = Context(root), CatalogueBudget(root, limits)
        value = contracts.validate_input(owner, request)
        proof = contracts.consumer(owner)
        desc = descriptor(root, "efficientat")
        old = owner.get(previous, "plans")["input"] if previous else None
        estimates = []
        for source in sorted(value["sources"], key=lambda s: s["recording_id"]):
            rows = contracts.native_rows(source, value["banks"])
            candidates = cache.lookup(owner, source, desc)
            missing = [b for b in rows if contracts.row_key(source, b, desc) not in candidates]
            prior = (
                next(
                    (s for s in old["sources"] if s["recording_id"] == source["recording_id"]), None
                )
                if old
                else None
            )
            reasons = []
            if prior is None:
                reasons.append("source added or first explicit revision")
            elif contracts.source_key(source) != contracts.source_key(prior):
                reasons.append(
                    "source samples/decoder changed; affected native features invalidated"
                )
            elif source != prior:
                reasons.append(
                    "metadata/ancestry changed; features compatible, eligibility recomputed"
                )
            if old and value["banks"] != old["banks"]:
                reasons.append("window policy changed; only exact compatible rows survive")
            estimates.append(
                dict(
                    source=source["recording_id"],
                    requested_rows=len(rows),
                    metadata_reuse_candidates=len(rows) - len(missing),
                    missing_rows=len(missing),
                    encoding_seconds=sum(b - a for a, b in missing)
                    / source["source"]["sample_rate_hz"],
                    validation_read_seconds=source["source"]["duration_seconds"],
                    reasons=reasons,
                )
            )
        blockers = []
        if value["historical"]:
            from .historical import inspect_inputs

            inspect_inputs(owner, value)
        for source in value["sources"]:
            if not (root / source["source"]["local_path"]).is_file():
                blockers.append(dict(target=source["recording_id"], error="missing original audio"))
        changed = []
        if old:
            for key in ("query", "policy", "packing", "label", "refinement"):
                if value[key] != old[key]:
                    changed.append(key)
        removed = (
            sorted(
                {s["recording_id"] for s in old["sources"]}
                - {s["recording_id"] for s in value["sources"]}
            )
            if old
            else []
        )
        saved = owner.put(
            budget, "inputs", dict(schema_version="c04-input-revision-1", value=value)
        )
        data = dict(
            schema_version="c04-plan-1",
            input_ref=saved,
            input=value,
            representation=desc,
            consumer=proof,
            protocol_hash=digest(owner.protocol),
            units=graph(value),
            previous=previous,
            tombstones=removed,
            changed_dependencies=changed,
            estimates=estimates,
            blockers=blockers,
            validation="metadata candidates only; full source/array verification required at run",
            estimated_new_rows=sum(v["missing_rows"] for v in estimates),
        )
        return owner.put(budget, "plans", data)


def load_plan(owner, ref):
    value = owner.get(ref, "plans")
    active = contracts.consumer(owner)
    transition = (
        None
        if value["consumer"] == active
        else contracts.compatible_consumer(owner, value["consumer"], active)
    )
    if (
        value.get("schema_version") != "c04-plan-1"
        or (value["consumer"] != active and transition is None)
        or value["protocol_hash"] != digest(owner.protocol)
        or value["units"] != graph(value["input"])
    ):
        raise InputError("C04 plan schema, graph, protocol or consumer changed")
    contracts.validate_input(owner, value["input"])
    if owner.get(value["input_ref"], "inputs")["value"] != value["input"]:
        raise InputError("C04 plan/input revision mismatch")
    return {
        **value,
        "declared_consumer": value["consumer"],
        "consumer": active,
        "consumer_transition": transition,
    }


def create_job(owner, budget, plan_ref, name):
    if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name):
        raise InputError("C04 job requires a 1..64 character stable name")
    plan_value = load_plan(owner, plan_ref)
    ref = owner.put(budget, "jobs", dict(schema_version="c04-job-1", name=name, plan=plan_ref))
    path = owner.directory / "progress" / (ref["record_hash"] + ".json")
    if not path.exists():
        owner.charge(budget, query_jobs=1)
        owner.publish(
            budget,
            path,
            dict(
                schema_version="c04-progress-1",
                job=ref,
                state="pending",
                completed={},
                attempts=0,
                result=None,
                error=None,
                requested_units=len(plan_value["units"]),
            ),
        )
    return ref


def status(root, job_ref):
    """Read-only; does not infer, refresh sources, or return an older result as success."""
    owner = Context(root)
    job = owner.get(job_ref, "jobs")
    state = record(owner.directory / "progress" / (job_ref["record_hash"] + ".json"))
    plan_value = owner.get(job["plan"], "plans")
    if state["job"] != job_ref:
        raise InputError("C04 status job/progress mismatch")
    pool = owner.pool()
    last = owner.directory / "last-complete.json"
    return dict(
        schema_version="c04-status-1",
        job=job_ref,
        plan=job["plan"],
        state=state["state"],
        requested=len(plan_value["units"]),
        completed=len(state["completed"]),
        remaining_units=[
            u["unit_id"] for u in plan_value["units"] if u["unit_id"] not in state["completed"]
        ],
        error=state["error"],
        result=state["result"],
        cancellation_requested=(
            owner.directory / "cancellation" / (job_ref["record_hash"] + ".json")
        ).exists(),
        last_complete=record(last) if last.exists() else None,
        allowance=pool,
        remaining_allowance={k: max(0, pool["ceilings"][k] - v) for k, v in pool["counts"].items()},
        events_path="data/runs/processing/attempts/" + job_ref["record_hash"],
    )


def cancel(root, job_ref):
    # Separate control lock permits cancellation while a numerical worker is active.
    owner = Context(root)
    owner.get(job_ref, "jobs")
    with project_lock(root, ".c04-control.lock"):
        path = owner.directory / "cancellation" / (job_ref["record_hash"] + ".json")
        atomic_json(path, dict(schema_version="c04-cancel-1", job=job_ref))
    return dict(
        status="ok",
        state="cancellation_requested",
        job=job_ref,
        active_worker="finishes its bounded unit (at most 120 seconds); no new unit admitted",
    )


def result(root, result_ref):
    owner = Context(root)
    value = owner.get(result_ref, "results")
    if value.get("schema_version") != "c04-result-1" or value["state"] != "complete":
        raise InputError("C04 result is not a complete immutable publication")
    owner.get(value["snapshot"], "snapshots")
    return value


def membership(root, ref):
    """Read either immutable legacy or compact membership without exposing packing."""
    from .records import expand

    owner = Context(root)
    value = owner.get(ref, "unit-results")
    return expand(value["output"])


def inventory(root, limit=256):
    """Bounded read-only listing. Obsolete means retained, never safe to delete."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 512:
        raise InputError("C04 inventory limit requires 1..512")
    owner = Context(root)
    output, more = [], False
    last = owner.directory / "last-complete.json"
    last_value = record(last) if last.exists() else None
    current = set()
    if last_value:
        current.add(last_value["result"]["path"])
        complete = owner.get(last_value["result"], "results")
        current.add(complete["snapshot"]["path"])

    def references(value):
        found = []

        def visit(v):
            if len(found) >= 32:
                return
            if isinstance(v, dict):
                if set(v) == {"path", "record_hash"}:
                    found.append(v)
                else:
                    for x in v.values():
                        visit(x)
            elif isinstance(v, list):
                for x in v:
                    visit(x)

        visit(value)
        return found

    for base in (owner.directory, owner.features, owner.indexes, owner.audio, owner.reports):
        for directory, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
            for name in sorted(files):
                path = Path(directory) / name
                if path.is_symlink():
                    continue
                if len(output) == limit:
                    more = True
                    break
                rel = path.relative_to(root).as_posix()
                output.append(
                    dict(
                        path=rel,
                        bytes=path.stat().st_size,
                        owner="C04",
                        retention="current-complete"
                        if rel in current
                        else "retained-history-or-diagnostic",
                        references=references(read_json(path)) if path.suffix == ".json" else [],
                    )
                )
            if more:
                break
        if more:
            break
    return dict(
        schema_version="c04-inventory-1",
        files=output,
        truncated=more,
        deletion_authorized=False,
        historical_owners="C01/C02/C03 read-only; outside C04 inventory",
        obsolete_relative_to="last-complete snapshot; older jobs remain reproducible and retained",
        last_complete=last_value,
    )


def input_file(root, path):
    return read_json(contained(path, root))


def run(root, limits, plan_ref, name, execute, pilot=False):
    """Start/reopen an explicitly named job. The name never selects a new pool."""
    from .commands import historical_workers
    from .job import run as dispatch

    with project_lock(root):
        historical_workers(root)
        return dispatch(
            dict(root=str(root), limits=limits, plan_ref=plan_ref, job=name, pilot=pilot), execute
        )


def resume(root, limits, job_ref, execute, pilot=False):
    from .commands import historical_workers
    from .job import run as dispatch

    with project_lock(root):
        historical_workers(root)
        return dispatch(
            dict(root=str(root), limits=limits, job_ref=job_ref, resume=True, pilot=pilot), execute
        )


def import_sources(root, limits, input_path, execute):
    """Bounded native registration; does not enlarge the frozen discovery population."""
    from .commands import admin

    return admin(
        dict(root=str(root), limits=limits, input=str(input_path), processing_action="import"),
        execute,
    )


def playback(root, job_ref):
    state = status(root, job_ref)
    if state["state"] != "complete":
        raise InputError("C04 playback: requested job incomplete; last-complete is separate")
    value = result(root, state["result"])
    if value["playback"] is None:
        raise InputError("C04 playback: no media route in this result")
    return value["playback"]


def events(root, job_ref, after=0, limit=64):
    owner = Context(root)
    owner.get(job_ref, "jobs")
    if (
        any(isinstance(v, bool) or not isinstance(v, int) for v in (after, limit))
        or after < 0
        or not 1 <= limit <= 64
    ):
        raise InputError("C04 events: nonnegative cursor and limit 1..64 required")
    files = sorted(
        (owner.directory / "attempts" / job_ref["record_hash"]).glob("*.json"),
        key=lambda p: int(p.stem),
    )
    selected = [p for p in files if int(p.stem) > after][:limit]
    values = [record(p) for p in selected]
    return dict(
        schema_version="c04-events-1",
        attempts=values,
        next_cursor=after if not values else values[-1]["sequence"],
        semantics="Attempts advance running->committed/failed; poll status for current attempt.",
    )
