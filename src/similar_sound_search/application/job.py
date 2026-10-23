"""Serial bounded worker orchestration, immutable unit commits and protected settlement."""

import json
import os
import subprocess
import time
import uuid

from ..evaluation.artifacts import record
from ..resources import CatalogueBudget
from ..storage import InputError, ResourceError, digest, project_lock
from . import api, history, media, pipeline, queries
from .context import Context, PersistenceError
from .locks import lock


def unit_path(owner, key, unit):
    return owner.directory / "units" / key / (digest(unit) + ".json")


def units(owner, value):
    request = value["identity"]["request"]
    if request["kind"] not in {"search", "validate"}:
        return [request["kind"]]
    old = history.inputs(owner)[1]
    count = len(old["input"]["sources"])
    return [
        "query",
        *[
            "source:" + s["recording_id"]
            for s in sorted(old["input"]["sources"], key=lambda s: s["recording_id"])
        ],
        *["aggregate:" + str(i) for i in range((count * 2 + 7) // 8)],
        "aggregate-final",
        *(["chain"] if request["input"]["query"].get("historical") else []),
        *["media:" + str(i) for i in range(5)],
        "publish",
    ]


def committed(owner, key, unit):
    path = unit_path(owner, key, unit)
    if not path.exists():
        return None
    value = record(path)
    if value["job_id"] != key or value["unit"] != unit:
        raise InputError("D01 committed unit/dependency mismatch")
    return value["output"]


def perform(budget, owner, value, unit, query_cache):
    request = value["identity"]["request"]
    spec, key = request["input"], value["job_id"]
    if request["kind"] == "register":
        from .server import upload_path

        return queries.register(budget, owner, upload_path(owner, spec["upload_id"]), spec["label"])
    if request["kind"] == "copy-reference":
        return queries.copy_historical(budget, owner, spec["revision"])
    if request["kind"] == "metadata-preflight":
        owner.charge(budget, metadata_bytes=128 * 1024)
        return pipeline.metadata_preflight(budget, owner)
    if request["kind"] == "native-qa":
        from .validation import native

        return native(budget, owner, spec)
    if request["kind"] == "save":
        return queries.save(budget, owner, spec)
    if request["kind"] == "rename":
        return queries.rename(budget, owner, spec)
    if request["kind"] == "preview":
        source = media.source_for_asset(owner, spec["asset_id"])
        from ..queries.assets import read_asset

        _, _, samples = read_asset(
            budget, queries.QueryOwner(owner), spec["asset_id"], with_samples=True
        )
        return dict(media=media.cached_clip(budget, owner, source, spec["bounds"], samples))
    if "query" not in query_cache:
        selection = dict(spec["query"])
        previous_query = committed(owner, key, "query")
        if previous_query is not None:
            saved = owner.get(previous_query["query"], "queries")
            selection["materialization"] = saved["materialization"]
        query_cache["query"] = queries.load(budget, owner, selection)
    q, matrix = query_cache["query"]
    if unit == "query":
        return dict(query=owner.put(budget, "queries", q), new_encodes=q["new_encodes"])
    if unit.startswith("source:"):
        return pipeline.source_unit(budget, owner, spec, unit[7:], q, matrix)
    source_results = {
        u[7:]: committed(owner, key, u) for u in units(owner, value) if u.startswith("source:")
    }
    if unit.startswith("aggregate:") or unit == "aggregate-final":
        if "aggregate" not in query_cache:
            query_cache["aggregate"] = pipeline.aggregate(budget, owner, spec, source_results, q)
        result, capture = query_cache["aggregate"]
        if unit == "aggregate-final":
            # All group/source/snapshot refs must exist before publishing this root.
            for path, (kind, data) in capture.records.items():
                ref = dict(path=path, record_hash=__import__("pathlib").Path(path).stem)
                owner.get(ref, kind)
            return dict(aggregate=owner.put(budget, "aggregates", result))
        i = int(unit.split(":")[1]) * 8
        items = sorted(capture.records.items())
        # Sources/snapshot are small shared records. Groups are the bounded subunits.
        groups = [(path, item) for path, item in items if item[0] == "group-results"]
        for path, (kind, data) in [(p, v) for p, v in items if v[0] != "group-results"] + groups[
            i : i + 8
        ]:
            owner.put(budget, kind, data)
        return dict(groups=[p for p, _ in groups[i : i + 8]], new_encodes=0)
    aggregate = owner.get(committed(owner, key, "aggregate-final")["aggregate"], "aggregates")
    if unit == "chain":
        return dict(
            chain=owner.put(
                budget, "chains", pipeline.audit_chain(budget, owner, spec, aggregate, q)
            )
        )
    if unit.startswith("media:"):
        # C03 experimental rendering is explicitly separate from legacy/event cards.
        if spec["arm"] == "historical-refinement":
            return dict(cards=[], historical=True)
        return dict(cards=media.cards(budget, owner, aggregate, int(unit[6:]) * 2, 2))
    if unit == "publish":
        cards = [c for i in range(5) for c in committed(owner, key, "media:" + str(i))["cards"]]
        chain = committed(owner, key, "chain") if spec["query"].get("historical") else None
        return dict(
            result=owner.put(
                budget,
                "results",
                dict(
                    schema_version="d01-result-1",
                    state="complete",
                    job_id=key,
                    query=committed(owner, key, "query")["query"],
                    selection=spec["query"],
                    policy=spec["arm"],
                    consumer=value["consumer"],
                    **aggregate,
                    cards=cards,
                    chain=chain,
                    historical_view=spec["arm"] == "historical-refinement",
                    resource_owner="data/runs/application/pool.json",
                    historical_c04_state="partial 145/148",
                    new_catalogue_encodes=0,
                    defaults=dict(audio="original", arm="legacy-mean", pitch="off"),
                ),
            )
        )
    raise InputError("D01 unknown executable unit")


def worker(request):
    from ..matchers.job import offline_network
    from ..matchers.runner import memory_check

    owner = Context(__import__("pathlib").Path(request["root"]), request["job_id"])
    budget = CatalogueBudget(owner.root, request["limits"])
    key = request["job_id"]
    with project_lock(owner.root), lock(owner.root, "worker"), offline_network():
        value = api.job(owner, key)
        if history.consumer(owner) != value["consumer"] and not history.compatible(
            owner, value["consumer"]
        ):
            raise InputError("D01 request consumer changed; declare scoped compatibility")
        graph = units(owner, value)
        cache, done, encodes = {}, [], 0
        if request.get("validate_units"):
            spec = value["identity"]["request"]["input"]
            saved = owner.get(committed(owner, key, "query")["query"], "queries")
            q, matrix = queries.load(
                budget, owner, {**spec["query"], "materialization": saved["materialization"]}
            )
            for unit in request["validate_units"]:
                cancel = owner.directory / "cancels" / (key + ".json")
                if cancel.exists() and not record(cancel).get("resumed", False):
                    return dict(status="ok", state="cancelled", completed=[], new_encodes=0)
                answer = pipeline.source_unit(budget, owner, spec, unit[7:], q, matrix)
                if answer != committed(owner, key, unit):
                    raise InputError(
                        "D01 resumed source/score dependency differs from committed output"
                    )
            return dict(
                status="ok",
                state="validated",
                completed=[],
                new_encodes=0,
                peak_working_bytes=memory_check(budget),
            )
        # Four useful units maximum. The worker owns one lazy model and query matrix.
        for unit in graph:
            if committed(owner, key, unit) is not None:
                continue
            cancel = owner.directory / "cancels" / (key + ".json")
            if cancel.exists() and not record(cancel).get("resumed", False):
                return dict(
                    status="ok",
                    state="cancelled",
                    completed=done,
                    new_encodes=encodes,
                    peak_working_bytes=memory_check(budget),
                )
            answer = perform(budget, owner, value, unit, cache)
            owner.publish(
                budget,
                unit_path(owner, key, unit),
                dict(job_id=key, unit=unit, output=answer),
                immutable=True,
            )
            done.append(unit)
            encodes += answer.get("new_encodes", 0)
            if len(done) >= 4 or time.monotonic() - budget.started > 60:
                break
        count = sum(unit_path(owner, key, u).exists() for u in graph)
        return dict(
            status="ok",
            state="complete" if count == len(graph) else "in_progress",
            completed=done,
            new_encodes=encodes,
            peak_working_bytes=memory_check(budget),
        )


def execute(owner, key, limits, validate_units=None):
    from ..processing.runner import python_command

    environment = os.environ.copy()
    environment.update(
        OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONIOENCODING="utf-8"
    )
    command = python_command(owner.root / "scripts/application-worker.py")
    request = dict(root=str(owner.root), job_id=key, limits=limits)
    if validate_units:
        request["validate_units"] = validate_units
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=limits["max_seconds"],
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return dict(
            status="failed",
            error_type="ResourceError",
            error="D01 actual worker exceeded 120s and stopped; retain reservation",
            uncertain=True,
        )
    try:
        result = json.loads(completed.stdout)
    except ValueError:
        return dict(
            status="failed",
            error_type="WorkerExit",
            error="D01 worker exited without a durable answer: " + completed.stderr[-1500:],
            uncertain=True,
        )
    return result


def reconcile(owner, key):
    """Only after exclusive coordinator/worker locks. Unobservable time stays charged."""
    pool = owner.pool()
    for identity, slot in pool["attempts"].items():
        if not slot["settled"]:
            previous_key = slot.get("job_id") or key
            previous = record(api.state_path(owner, previous_key))
            previous.update(
                state="interrupted",
                error=dict(
                    step="recovery",
                    message="Owned process stopped without settlement; full reservation retained",
                ),
            )
            owner.terminal(identity, api.state_path(owner, previous_key), previous, uncertain=True)


def _run(root, limits, key):
    owner = Context(root, key)
    # This lock belongs to the coordinator while HTTP control/status runs independently.
    with lock(owner.root, "coordinator"):
        with lock(owner.root, "worker"):
            reconcile(owner, key)
        value = api.job(owner, key)
        graph = units(owner, value)
        budget = CatalogueBudget(root, limits)
        validate = [
            u for u in graph if u.startswith("source:") and committed(owner, key, u) is not None
        ]
        for _ in range(256):
            # The 120s deadline bounds each child and each coordinator transaction,
            # not the complete multi-worker request. Aggregate time stays in the pool.
            budget = CatalogueBudget(root, limits)
            state = record(api.state_path(owner, key))
            if state["state"] == "complete":
                return state
            identity = "attempt-" + uuid.uuid4().hex
            owner.reserve_attempt(identity)
            started = time.monotonic()
            running = dict(
                schema_version="d01-state-1",
                job_id=key,
                state="running",
                completed=sum(unit_path(owner, key, u).exists() for u in graph),
                requested=len(graph),
                result=None,
                error=None,
                attempt=identity,
            )
            try:
                owner.publish(
                    budget, owner.directory / "active.json", dict(job_id=key, pid=os.getpid())
                )
                owner.publish(budget, api.state_path(owner, key), running)
                budget.reserve(65536)
                from ..indexing.commands import memory_status
                from ..matchers.runner import peak_memory

                host = memory_status()
                server_memory = peak_memory()
                available = host.get("available_commit_bytes")
                if (
                    available is not None
                    and available < limits["max_working_bytes"] + server_memory
                ):
                    raise ResourceError(
                        "D01 insufficient available commit for worker plus server overlap"
                    )
                answer = execute(owner, key, {**limits, "max_seconds": 120}, validate[:4])
                budget = CatalogueBudget(root, limits)
                answer["server_peak_working_bytes"] = server_memory
                answer["overlap_peak_bound"] = server_memory + answer.get("peak_working_bytes", 0)
                if answer.get("state") == "validated":
                    del validate[:4]
                    answer["state"] = "in_progress"
                count = sum(unit_path(owner, key, u).exists() for u in graph)
                outcome = answer.get(
                    "state", "blocked" if answer.get("error_type") == "ResourceError" else "failed"
                )
                if answer["status"] == "failed":
                    outcome = "blocked" if answer.get("error_type") == "ResourceError" else "failed"
                result = (
                    committed(owner, key, "publish")["result"]
                    if outcome == "complete" and request_search(value)
                    else None
                )
                if outcome == "complete" and not request_search(value):
                    result = owner.put(
                        budget,
                        "results",
                        dict(
                            schema_version="d01-operation-result-1",
                            state="complete",
                            job_id=key,
                            operation=value["identity"]["request"]["kind"],
                            output=committed(owner, key, graph[0]),
                        ),
                    )
                terminal = {
                    **running,
                    "state": outcome,
                    "completed": count,
                    "result": result,
                    "error": None
                    if answer["status"] == "ok"
                    else dict(
                        step="worker",
                        error_type=answer.get("error_type"),
                        message=answer.get("error"),
                    ),
                    "worker_evidence": answer,
                }
                if outcome == "complete" and request_search(value):
                    owner.publish(
                        budget,
                        owner.directory / "last-complete.json",
                        dict(job_id=key, result=result),
                    )
                owner.terminal(
                    identity,
                    api.state_path(owner, key),
                    terminal,
                    elapsed=time.monotonic() - started,
                    uncertain=answer.get("uncertain", False),
                )
            except PersistenceError:
                raise
            except (InputError, OSError, ValueError, RuntimeError, MemoryError) as exc:
                terminal = {
                    **running,
                    "state": "blocked" if isinstance(exc, ResourceError) else "failed",
                    "error": dict(
                        step="coordinator", error_type=type(exc).__name__, message=str(exc)
                    ),
                }
                owner.terminal(
                    identity,
                    api.state_path(owner, key),
                    terminal,
                    elapsed=time.monotonic() - started,
                )
                return terminal
            if terminal["state"] != "in_progress":
                if terminal["state"] == "complete":
                    owner.release(key)
                return terminal
        raise ResourceError("D01 finite dispatch limit reached")


def request_search(value):
    return value["identity"]["request"]["kind"] in {"search", "validate"}


def run(root, limits, key):
    try:
        return _run(root, limits, key)
    except PersistenceError:
        raise
    except (InputError, OSError, ValueError, RuntimeError) as exc:
        from .locks import active

        if active(root, "coordinator") or active(root, "worker"):
            raise
        owner = Context(root, key)
        previous = record(api.state_path(owner, key))
        slot = "admission-" + uuid.uuid4().hex
        owner.reserve_attempt(slot, seconds=0)
        terminal = {
            **previous,
            "state": "blocked" if isinstance(exc, ResourceError) else "failed",
            "error": dict(step="admission", message=str(exc), error_type=type(exc).__name__),
        }
        owner.terminal(slot, api.state_path(owner, key), terminal, elapsed=0)
        return terminal
