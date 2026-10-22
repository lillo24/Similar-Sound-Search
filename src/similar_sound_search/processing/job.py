"""Durable claims/reservations and single publication under OS locks and deadlines."""

import time

from ..evaluation.artifacts import record, write_record
from ..matchers.job import offline_network
from ..matchers.runner import memory_check
from ..resources import CatalogueBudget
from ..storage import InputError, ResourceError, canonical, project_lock
from . import api, engine
from .context import Context


def progress(owner, job_ref):
    path = owner.directory / "progress" / (job_ref["record_hash"] + ".json")
    value = record(path)
    if value["schema_version"] != "c04-progress-1" or value["job"] != job_ref:
        raise InputError("C04 progress/job mismatch")
    return path, {k: v for k, v in value.items() if k != "record_hash"}


def output(owner, state, unit):
    value = owner.get(state["completed"][unit["unit_id"]], "unit-results")
    if value["unit"] != unit:
        raise InputError("C04 committed unit/dependency membership differs")
    return value["output"]


def collect(owner, state, plan, kind):
    return {
        u["subject"]: output(owner, state, u)
        for u in plan["units"]
        if u["kind"] == kind and u["unit_id"] in state["completed"]
    }


def unit_path(owner, job_ref, unit):
    return owner.directory / "unit-commits" / job_ref["record_hash"] / (unit["unit_id"] + ".json")


def step(request, budget, owner, fault=lambda _: None):
    job_ref = request["job_ref"]
    job = owner.get(job_ref, "jobs")
    plan = api.load_plan(owner, job["plan"])
    path, state = progress(owner, job_ref)
    cancel = owner.directory / "cancellation" / (job_ref["record_hash"] + ".json")
    if cancel.exists():
        state.update(state="cancelled", error=None)
        owner.publish(budget, path, state)
        return dict(status="ok", state="cancelled", job=job_ref)
    # Resume audits committed feature outputs in bounded units before admitting new work.
    if request.get("validate_unit"):
        unit = next(u for u in plan["units"] if u["unit_id"] == request["validate_unit"])
        previous = output(owner, state, unit)
        if unit["kind"] == "features":
            source = next(
                s for s in plan["input"]["sources"] if s["recording_id"] == unit["subject"]
            )
            from ..search import sources
            from . import cache

            sources.load(budget, source, context=owner)
            cache.vectors(budget, owner, previous["rows"])
        elif unit["kind"] == "query":
            # Query recipe/audio/cue lineage is validated again, with no feature production.
            from . import cache

            q = previous["query"]
            if "features" in previous:
                from ..search import sources

                sources.load(budget, q["native_source"], context=owner)
                cache.vectors(budget, owner, previous["features"])
            else:
                engine.query_vectors(budget, owner, previous)
        return dict(status="ok", state="validated", unit=unit["unit_id"], new_encodes=0)
    todo = [u for u in plan["units"] if u["unit_id"] not in state["completed"]]
    if not todo:
        api.result(owner.root, state["result"])
        return dict(
            status="ok", state="complete", job=job_ref, result=state["result"], new_encodes=0
        )
    unit = todo[0]
    if any(d not in state["completed"] for d in unit["dependencies"]):
        raise InputError("C04 deterministic graph contains unsatisfied dependencies")
    prior = [
        int(p.stem) for p in (owner.directory / "attempts" / job_ref["record_hash"]).glob("*.json")
    ]
    attempt = dict(
        schema_version="c04-attempt-1",
        job=job_ref,
        unit=unit,
        sequence=max([state["attempts"], *prior]) + 1,
        state="running",
        reservation=request["reservation"],
        consumer=plan["consumer"],
        started_monotonic=time.monotonic(),
    )
    attempt_path = (
        owner.directory / "attempts" / job_ref["record_hash"] / (str(attempt["sequence"]) + ".json")
    )
    # A retry never overwrites its predecessor. The pool reservation predates this claim.
    owner.publish(budget, attempt_path, attempt)
    state.update(attempts=attempt["sequence"], state="running", error=None)
    owner.publish(budget, path, state)
    producer = owner.put(
        budget,
        "producers",
        dict(
            schema_version="c04-producer-1",
            job=job_ref,
            unit_id=unit["unit_id"],
            attempt=attempt["sequence"],
            consumer=plan["consumer"],
        ),
    )
    commit = unit_path(owner, job_ref, unit)
    try:
        if commit.exists():
            value = record(commit)
            saved = owner.get(value["result"], "unit-results")
            if saved["unit"] != unit:
                raise InputError("C04 orphan membership unit differs")
            answer = saved["output"]
            # Arrays must reopen before adopting membership after an interrupted advance.
            if unit["kind"] in {"features", "query"}:
                from . import cache

                refs = answer.get("rows", answer.get("features", []))
                if refs:
                    cache.vectors(budget, owner, refs)
            result_ref = value["result"]
            attempt["recovered_membership"] = True
        else:
            f = collect(owner, state, plan, "features")
            queries = collect(owner, state, plan, "query").get("query")
            if unit["kind"] == "features":
                source = next(
                    s for s in plan["input"]["sources"] if s["recording_id"] == unit["subject"]
                )
                answer = engine.features(budget, owner, plan, source, producer, fault)
            elif unit["kind"] == "query":
                answer = engine.query(budget, owner, plan, producer, fault)
            elif unit["kind"] == "score":
                source = next(
                    s for s in plan["input"]["sources"] if s["recording_id"] == unit["subject"]
                )
                answer = engine.score(budget, owner, plan, source, f[unit["subject"]], queries)
            elif unit["kind"] == "aggregate":
                answer = engine.aggregate(
                    budget,
                    owner,
                    plan,
                    f,
                    queries,
                    collect(owner, state, plan, "score"),
                    memberships={
                        u["subject"]: state["completed"][u["unit_id"]]
                        for u in plan["units"]
                        if u["kind"] == "features"
                    },
                )
            elif unit["kind"] == "refinement":
                from .historical import refinement

                answer = refinement(
                    budget,
                    owner,
                    plan,
                    collect(owner, state, plan, "aggregate")["population"],
                    queries,
                )
            elif unit["kind"] == "publish":
                aggregate = collect(owner, state, plan, "aggregate")["population"]
                historical = collect(owner, state, plan, "refinement").get("historical")
                value = dict(
                    schema_version="c04-result-1",
                    state="complete",
                    plan=job["plan"],
                    input_ref=plan["input_ref"],
                    consumer=plan["consumer"],
                    **aggregate,
                    refinement=historical,
                    label=plan["input"]["label"],
                    playback=None if historical is None else historical["playback"],
                    defaults=dict(audio="original", retrieval="legacy-mean", pitch="off"),
                    resource_owner="data/runs/processing/pool.json",
                )
                answer = dict(result=owner.put(budget, "results", value))
                fault("final")
            else:
                raise InputError("C04 unsupported executable unit kind")
            result_ref = owner.put(budget, "unit-results", dict(unit=unit, output=answer))
            owner.publish(
                budget,
                commit,
                dict(unit=unit, result=result_ref, producer=producer),
                immutable=True,
            )
            fault("progress")
        state["completed"][unit["unit_id"]] = result_ref
        state["state"] = "in_progress"
        if unit["kind"] == "publish":
            api.result(owner.root, answer["result"])
            state.update(state="complete", result=answer["result"])
            # Immutable complete result is published first; current/last pointers are last.
            owner.publish(
                budget,
                owner.directory / "last-complete.json",
                dict(job=job_ref, result=answer["result"]),
            )
        owner.publish(budget, path, state)
        attempt.update(
            state="committed", result=result_ref, new_encodes=answer.get("new_encodes", 0)
        )
        owner.publish(budget, attempt_path, attempt)
        return dict(
            status="ok",
            state=state["state"],
            job=job_ref,
            unit=unit["unit_id"],
            kind=unit["kind"],
            new_encodes=answer.get("new_encodes", 0),
            result=state["result"],
        )
    except (InputError, OSError, ValueError, RuntimeError, MemoryError) as exc:
        error = dict(
            step=unit["kind"],
            target=unit["subject"],
            unit_id=unit["unit_id"],
            error_type=type(exc).__name__,
            message=str(exc),
            recovery="preserve artifacts; resume same job after resolving this dependency",
        )
        attempt.update(state="failed", error=error)
        owner.publish(budget, attempt_path, attempt)
        state.update(state="blocked" if isinstance(exc, ResourceError) else "failed", error=error)
        owner.publish(budget, path, state)
        raise


def reserve(owner, budget):
    pool = owner.pool()
    # A crashed owner has no observable elapsed time: retain its whole reservation.
    if pool["pending_worker_seconds"]:
        journal = (
            owner.directory / "worker-settlements" / (str(pool["pending_worker_id"]) + ".json")
        )
        if journal.exists():
            saved = record(journal)
            if saved["sequence"] != pool["pending_worker_id"]:
                raise InputError("C04 settlement journal reservation differs")
            pool = saved["pool_after"]
        else:
            pool["uncertain_worker_seconds"] += pool["pending_worker_seconds"]
            pool["pending_worker_seconds"] = 0
            pool["pending_worker_id"] = None
        owner.save_pool(budget, pool)
    seconds = min(
        120,
        budget.limits["max_seconds"],
        pool["ceilings"]["job_seconds"] - pool["counts"]["job_seconds"],
    )
    if seconds < 2:
        raise ResourceError("C04 worker time exhausted; same pool remains blocked")
    pool = owner.charge(budget, workers=1, job_seconds=seconds)
    pool["pending_worker_seconds"] = seconds
    pool["pending_worker_id"] = pool["counts"]["workers"]
    owner.save_pool(budget, pool)
    return pool["counts"]["workers"], seconds


def settle(owner, budget, sequence, seconds, elapsed, result):
    path = owner.directory / "worker-settlements" / (str(sequence) + ".json")
    if path.exists():
        raise InputError("C04 worker reservation already settled")
    # Settlement journal before pool update allows exactly-once reconciliation.
    value = dict(
        sequence=sequence,
        reserved_seconds=seconds,
        measured_seconds=elapsed,
        peak_working_bytes=result.get("peak_working_bytes", 0),
        outcome=result.get("status"),
        action=result.get("kind", result.get("state", "failed")),
    )
    # Charge the journal and pool writes before writing either transaction member.
    owner.charge(budget, metadata_bytes=len(canonical(value)) * 2 + 16384)
    pool = owner.pool()
    if pool["pending_worker_seconds"] != seconds or pool["pending_worker_id"] != sequence:
        raise InputError("C04 pending worker reservation differs")
    pool["counts"]["job_seconds"] += elapsed - seconds
    pool["measured_worker_seconds"] += elapsed
    pool["pending_worker_seconds"] = 0
    pool["pending_worker_id"] = None
    pool["last_settled_worker"] = sequence
    write_record(path, dict(**value, pool_after=pool), budget)
    owner.save_pool(budget, pool)


def run(request, execute):
    root = __import__("pathlib").Path(request["root"])
    owner = Context(root)
    limits = {
        **request["limits"],
        "max_download_bytes": 0,
        "max_seconds": min(120, request["limits"]["max_seconds"]),
    }
    with project_lock(root, ".c04-coordinator.lock"):
        # Reject orphaned live workers before reservations, source writes or settlement.
        with project_lock(root, ".c04-worker.lock"):
            pass
        budget = CatalogueBudget(root, limits)
        job_ref = request.get("job_ref")
        if job_ref is None:
            job_ref = api.create_job(owner, budget, request["plan_ref"], request["job"])
        job = owner.get(job_ref, "jobs")
        plan = api.load_plan(owner, job["plan"])
        path, state = progress(owner, job_ref)
        # A cancelled job is resumed explicitly; the immutable cancellation remains evidence.
        control = owner.directory / "cancellation" / (job_ref["record_hash"] + ".json")
        if request.get("resume") and control.exists():
            with project_lock(root, ".c04-control.lock"):
                archive = (
                    owner.directory
                    / "cancelled-history"
                    / job_ref["record_hash"]
                    / (str(state["attempts"]) + ".json")
                )
                archive.parent.mkdir(parents=True, exist_ok=True)
                control.replace(archive)
        validate = [
            u["unit_id"]
            for u in plan["units"]
            if u["kind"] in {"features", "query"} and u["unit_id"] in state["completed"]
        ]
        encoded = 0
        for _ in range(owner.cfg["policy"]["max_workers"]):
            with project_lock(root, ".c04-worker.lock"):
                budget = CatalogueBudget(root, limits)
                sequence, seconds = reserve(owner, budget)
            worker_request = {
                **request,
                "root": str(root),
                "command": "processing_step",
                "job_ref": job_ref,
                "reservation": sequence,
                "limits": {**limits, "max_seconds": seconds},
            }
            if validate:
                worker_request["validate_units"] = validate[:4]
            started, result = time.monotonic(), None
            try:
                result = execute(worker_request)
            finally:
                with project_lock(root, ".c04-worker.lock"):
                    if result is not None:
                        settle(
                            owner,
                            CatalogueBudget(root, limits),
                            sequence,
                            seconds,
                            time.monotonic() - started,
                            result,
                        )
                    # On an unobservable dispatcher crash the pending reservation stays charged.
            if result is None:
                raise InputError("C04 dispatcher returned no explicit result")
            encoded += result.get("new_encodes", 0)
            if result.get("status") == "failed":
                path, state = progress(owner, job_ref)
                state.update(
                    state="failed",
                    error=dict(
                        step="worker",
                        target=job_ref["record_hash"],
                        message=result.get("error", "worker failed"),
                        error_type=result.get("error_type"),
                    ),
                )
                owner.publish(CatalogueBudget(root, limits), path, state)
                return {**result, "job": job_ref, "new_encodes": encoded}
            if validate:
                del validate[:4]
                if not validate and state["state"] == "complete":
                    return dict(
                        status="ok",
                        state="complete",
                        job=job_ref,
                        result=state["result"],
                        new_encodes=encoded,
                    )
            elif result["state"] not in {"in_progress", "running"}:
                return {**result, "new_encodes": encoded, "pool": owner.pool()}
            if request.get("pilot"):
                return {**result, "new_encodes": encoded, "pool": owner.pool()}
        raise ResourceError("C04 finite dispatch bound reached; retain progress")


def worker(request, budget):
    with project_lock(budget.root, ".c04-worker.lock"), offline_network():
        owner = Context(budget.root)
        encodes, completed = 0, []
        if request.get("validate_units"):
            for key in request["validate_units"]:
                result = step({**request, "validate_unit": key}, budget, owner)
                completed.append(key)
            return {
                **result,
                "validated_units": completed,
                "peak_working_bytes": memory_check(budget),
            }
        for _ in range(4):
            result = step(request, budget, owner)
            encodes += result.get("new_encodes", 0)
            completed.append(result.get("unit"))
            if result["state"] != "in_progress" or time.monotonic() - budget.started > 60:
                break
        return {
            **result,
            "new_encodes": encodes,
            "committed_units": completed,
            "peak_working_bytes": memory_check(budget),
        }
