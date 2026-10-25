"""Stable D02 product boundary. Reads never dispatch, write progress or charge work."""

import re

from ..evaluation.artifacts import record
from ..resources import CatalogueBudget
from ..storage import InputError, ResourceError, digest
from . import history, queries
from .context import Context
from .locks import active, lock


def owner_for(root, allocation=None, runtime=None):
    """Explicit trusted provider injection; HTTP payloads never select an owner."""
    return Context(root, allocation) if runtime is None else runtime.context(root, allocation)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch("[a-f0-9]{64}", value):
        raise InputError("D01 expected opaque SHA256 identifier")
    return value


def job(owner, key):
    value = record(owner.directory / "jobs" / (identifier(key) + ".json"))
    if value["job_id"] != key or digest(value["identity"]) != key:
        raise InputError("D01 job identity differs")
    return value


def state_path(owner, key):
    return owner.directory / "states" / (identifier(key) + ".json")


def submit(root, limits, request, acceptance=False, runtime=None):
    """Explicit POST semantics; same immutable request yields the same durable job."""
    if (
        not isinstance(request, dict)
        or set(request) != {"kind", "input", "request_id"}
        or not isinstance(request["kind"], str)
        or request["kind"]
        not in {
            "search",
            "register",
            "save",
            "rename",
            "preview",
            "validate",
            "copy-reference",
            "metadata-preflight",
            "native-qa",
        }
    ):
        raise InputError("D01 unsupported operation/settings")
    if not isinstance(request["input"], dict):
        raise InputError("D01 operation input must be an object")
    token = request["request_id"]
    if not isinstance(token, str) or not re.fullmatch("[a-zA-Z0-9_-]{1,80}", token):
        raise InputError("D01 stable request ID required")
    owner = owner_for(root, runtime=runtime)
    # Bind client retries before creating a second request. Different payload under the same
    # idempotency key is a conflict, not a new execution.
    binding = owner.directory / "requests" / (digest(token) + ".json")
    with lock(owner.root, "library"):
        if binding.exists():
            old = record(binding)
            if old["request"] != request:
                raise InputError("D01 request conflict: idempotency key has different input")
            return dict(job_id=old["job_id"], reused=True)
        consumer = history.consumer(owner) if runtime is None else runtime.consumer(owner)
        if runtime is not None:
            runtime.validate_request(owner, request)
        if request["kind"] in {"search", "validate"}:
            selection = request["input"]
            if (
                set(selection) != {"query", "arm"}
                or not isinstance(selection["arm"], str)
                or selection["arm"]
                not in {
                    "legacy-mean",
                    "event-multi",
                    "historical-refinement",
                }
            ):
                raise InputError("D01 unavailable retrieval option; original/pitch-off routes only")
            if not isinstance(selection["query"], dict):
                raise InputError("D01 immutable query selection must be an object")
            if selection["arm"] == "historical-refinement" and not selection["query"].get(
                "historical"
            ):
                raise InputError("D01 refinement unavailable for a new query")
        size = 20 * 1024**2 if request["kind"] in {"search", "validate"} else 2 * 1024**2
        if runtime is not None:
            size = runtime.estimate(request)
        elif request["kind"] in {"search", "validate"}:
            from ..queries.library import revision
            from .pipeline import geometry_estimate
            from .queries import QueryOwner

            selection = request["input"].get("query", {})
            n = (
                1
                if selection.get("historical")
                else len(revision(QueryOwner(owner), selection["revision"])["recipe"]["examples"])
            )
            geometry = geometry_estimate(owner, n)
            if not geometry["fits"]:
                raise ResourceError("D01 complete population metadata estimate cannot fit")
            size = max(
                size,
                ((geometry["complete_path_counted_bytes"] + 1024**2 - 1) // 1024**2 + 1) * 1024**2,
            )
        identity = dict(
            request=request,
            consumer=consumer,
            population=owner.protocol["snapshot"]
            if runtime is None
            else runtime.population_id(owner),
        )
        key = digest(identity)
        if runtime is None:
            owner.admit(key, size, acceptance=acceptance, jobs=1)
            owner.allocation = key
        else:
            owner.allocation = runtime.allocation(request)
            owner.job_id = key
            runtime.admit(owner, request)
        budget = (CatalogueBudget if runtime is None else runtime.budget)(root, limits)
        value = dict(
            schema_version="d01-job-1",
            job_id=key,
            identity=identity,
            allocation=size,
            consumer=consumer,
        )
        if runtime is not None:
            value["allocation_owner"] = owner.allocation
        owner.publish(budget, owner.directory / "jobs" / (key + ".json"), value, immutable=True)
        owner.publish(budget, binding, dict(request=request, job_id=key), immutable=True)
        slot = "submit-" + key
        owner.reserve_attempt(slot, seconds=0)
        owner.terminal(
            slot,
            state_path(owner, key),
            dict(
                schema_version="d01-state-1",
                job_id=key,
                state="pending",
                completed=0,
                requested=0,
                result=None,
                error=None,
                attempt=None,
            ),
            elapsed=0,
        )
        return dict(job_id=key, reused=False)


def status(root, key, runtime=None):
    owner = owner_for(root, key, runtime)
    value = job(owner, key)
    state = record(state_path(owner, key))
    running = active(owner.root, "worker") or active(owner.root, "coordinator")
    # OS lock ownership plus exact active job receipt; another request is not this worker.
    current = owner.directory / "active.json"
    same = current.exists() and record(current).get("job_id") == key
    observed = "active" if running and same else "stopped"
    durable = state["state"]
    display = durable
    if durable in {"running", "in_progress"} and observed == "stopped":
        display = "interrupted"
    cancel = owner.directory / "cancels" / (key + ".json")
    cancellation = cancel.exists() and not record(cancel).get("resumed", False)
    previous = owner.directory / "last-complete.json"
    pool = owner.pool()
    return dict(
        schema_version="d01-status-1",
        job_id=key,
        state=display,
        durable_state=durable,
        observed_process=observed,
        completed=state["completed"],
        requested=state["requested"],
        result=state["result"],
        error=state["error"],
        cancellation_pending=cancellation and running and same,
        cancellation_requested=cancellation,
        last_complete=record(previous) if previous.exists() else None,
        query=value["identity"]["request"]["input"].get("query"),
        policy=value["identity"]["request"]["input"].get("arm"),
        allowance=dict(
            counts=pool["counts"],
            ordinary_reserved=pool["ordinary_reserved"],
            protected_reserved=pool["protected_reserved"],
            protected_used=pool["protected_used"],
            uncertain_worker_seconds=pool["uncertain_worker_seconds"],
        ),
        historical_c04="partial 145/148; 120 seconds pending, separate closed pool",
    )


def cancel(root, key, request_id, runtime=None):
    owner = owner_for(root, key, runtime)
    job(owner, key)
    identifier(request_id)
    slot = "cancel-" + request_id
    owner.reserve_attempt(slot, seconds=0)
    owner.terminal(
        slot,
        owner.directory / "cancels" / (key + ".json"),
        dict(job_id=key, resumed=False, request_id=request_id),
        elapsed=0,
    )
    return dict(job_id=key, state="cancellation_requested")


def resume_control(root, key, request_id, runtime=None):
    owner = owner_for(root, key, runtime)
    job(owner, key)
    if active(owner.root, "worker") or active(owner.root, "coordinator"):
        raise ResourceError("D01 worker still active; cancellation remains pending until it stops")
    identifier(request_id)
    state = record(state_path(owner, key))
    if state["state"] == "complete":
        return dict(job_id=key, state="complete")
    path = owner.directory / "cancels" / (key + ".json")
    if path.exists():
        slot = "resume-" + request_id
        owner.reserve_attempt(slot, seconds=0)
        owner.terminal(slot, path, dict(job_id=key, resumed=True, request_id=request_id), elapsed=0)
    # Acknowledge a durable queued state before HTTP returns 202. A fast poll must
    # not mistake the prior cancelled/blocked record for the new attempt's outcome.
    pending = {**state, "state": "pending", "error": None, "resume_request_id": request_id}
    slot = "resume-state-" + request_id
    owner.reserve_attempt(slot, seconds=0)
    owner.terminal(slot, state_path(owner, key), pending, elapsed=0)
    return dict(job_id=key, state="resume_requested")


def result(root, key, runtime=None):
    owner = owner_for(root, key, runtime)
    state = record(state_path(owner, key))
    if state["state"] != "complete" or state["result"] is None:
        raise InputError("D01 request has no complete result; partial work is not a result")
    value = owner.get(state["result"], "results")
    if value["job_id"] != key or value["state"] != "complete":
        raise InputError("D01 result/job identity differs")
    if value["schema_version"] == "d01-result-1":
        from .media import validate

        query = owner.get(value["query"], "queries")["query"]
        if query["record_hash"] != value["query_hash"]:
            raise InputError("D01 result/query binding differs")
        selected = value["arms"][value["selected_arm"]]["display"]
        for card in value["cards"]:
            if (
                card["query_hash"] != value["query_hash"]
                or card["arm"] != value["selected_arm"]
                or card["population"] != value["snapshot"]["record_hash"]
                or card["group_ref"] not in selected
            ):
                raise InputError("D01 result/card query, arm or population differs")
            group = owner.get(card["group_ref"], "group-results")
            for p in card["passages"]:
                if p["additional"]:
                    continue
                if p["row"] != group["passages"][0]["representative"]:
                    raise InputError("D01 player representative differs from the scored result")
                for label, bounds in (
                    ("scored", p["scored_bounds"]),
                    ("context", p["context_bounds"]),
                ):
                    _, saved = validate(owner, p[label]["record_hash"])
                    if (
                        saved["bounds"] != bounds
                        or saved["original"]["recording_id"] != p["row"]["recording_id"]
                    ):
                        raise InputError("D01 media/native interval differs from selected result")
    return value


def result_media(root, result_id, media_id, runtime=None):
    """Resolve media only through its immutable complete query/arm/population result."""
    owner = owner_for(root, runtime=runtime)
    if runtime is not None and hasattr(runtime, "result_context"):
        owner = runtime.result_context(result_id)
    ref = dict(
        path=(owner.directory / "results" / (identifier(result_id) + ".json"))
        .relative_to(owner.root)
        .as_posix(),
        record_hash=result_id,
    )
    declared = owner.get(ref, "results")
    value = result(root, declared["job_id"], runtime=runtime)
    if value["record_hash"] != result_id or value["schema_version"] != "d01-result-1":
        raise InputError("D01 media result is not the job's complete publication")
    identifier(media_id)
    members = {
        p[k]["record_hash"]
        for c in value["cards"]
        for p in c["passages"]
        if not p["additional"]
        for k in ("scored", "context")
    }
    if media_id not in members:
        raise InputError("D01 media does not belong to this query/arm/population/result")
    from .media import validate

    return validate(owner, media_id)


def library(root, runtime=None):
    owner = owner_for(root, runtime=runtime)
    return queries.inventory(owner) if runtime is None else runtime.inventory(owner)


def completed_searches(root, runtime=None):
    """Bounded immutable navigation for a fresh browser; no worker or audit is started."""
    owner = owner_for(root, runtime=runtime)
    names = library(root, runtime=runtime)["names"]
    output = []
    for path in sorted((owner.directory / "states").glob("*.json"))[
        : owner.cfg["policy"]["max_query_jobs"]
    ]:
        state = record(path)
        if state["state"] != "complete":
            continue
        saved = job(owner, state["job_id"])
        if saved["identity"]["request"]["kind"] not in {"search", "validate"}:
            continue
        value = owner.get(state["result"], "results")
        q = owner.get(value["query"], "queries")
        historical = value["selection"].get("historical", False)
        label = (
            "Loulou 3:38–4:00"
            if historical
            else next((n["label"] for n in names if q["revision"] in n["revisions"]), "Saved query")
        )
        output.append(
            dict(
                job_id=state["job_id"],
                result=state["result"],
                label=label,
                query=dict(
                    historical=historical,
                    revision=q["revision"],
                    materialization=q["materialization"],
                ),
                policy=value["policy"],
                query_hash=value["query_hash"],
            )
        )
    if runtime is not None and hasattr(runtime, "additional_completed"):
        output.extend(runtime.additional_completed())
    return output


def catalogue(root, runtime=None):
    owner = owner_for(root, runtime=runtime)
    if runtime is not None:
        return runtime.catalogue(owner)
    try:
        _, plan, _ = history.inputs(owner)
        missing = sum(
            not (owner.root / s["source"]["local_path"]).is_file() for s in plan["input"]["sources"]
        )
        return dict(
            state="missing-input" if missing else "ready-for-validation",
            recordings=72,
            native_rows=54939,
            missing=missing,
            message="72 recordings; exact source and array validation runs on submission",
        )
    except (InputError, OSError, KeyError) as exc:
        return dict(state="missing-input", recordings=0, message=str(exc))
