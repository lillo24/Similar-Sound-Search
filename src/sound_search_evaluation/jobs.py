"""Actual-PID bounded serial workers, useful-unit commits and protected settlement."""

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from similar_sound_search.application import api
from similar_sound_search.application.job import committed, unit_path
from similar_sound_search.application.locks import lock
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import InputError, ResourceError, digest, project_lock

from . import contracts, pipeline
from .budget import CatalogueBudget
from .context import Context
from .runtime import Runtime, category


def graph(value):
    request = value["identity"]["request"]
    return request["input"].get("units", [request["kind"]])


def submit(root, limits, stage, split, operation, units, extra=None):
    owner = Context(root, stage, split)
    request = dict(
        kind=operation,
        input=dict(units=units, **(extra or {})),
        request_id=digest([operation, split, units, extra]),
    )
    identity = dict(request=request, consumer=contracts.consumer(owner), split=split)
    key = digest(identity)
    path = owner.directory / "jobs" / (key + ".json")
    if path.exists():
        return key
    owner.job_id = key
    budget = CatalogueBudget(root, limits)
    owner.charge(budget, query_jobs=1)
    owner.publish(
        budget,
        path,
        dict(
            schema_version="d02-job-1",
            job_id=key,
            identity=identity,
            consumer=identity["consumer"],
            allocation_owner=stage,
            split=split,
        ),
        immutable=True,
    )
    slot = "submit-" + key
    owner.reserve_attempt(slot, seconds=0)
    owner.terminal(
        slot,
        api.state_path(owner, key),
        dict(
            schema_version="d01-state-1",
            job_id=key,
            state="pending",
            completed=0,
            requested=len(units),
            result=None,
            error=None,
        ),
        elapsed=0,
    )
    return key


def perform(budget, owner, value, unit):
    from . import audit, dataset

    request = value["identity"]["request"]
    kind, spec = request["kind"], request["input"]
    if kind == "generate":
        if unit.startswith("source:"):
            return dataset.generate_sources(budget, owner, [int(unit.split(":")[1])])
        return dataset.generate_queries(budget, owner, [int(unit.split(":")[1])])
    if kind == "audit":
        return audit.validate(budget, owner)
    if kind == "index":
        return pipeline.index_sources(budget, owner, [int(unit)])
    if kind == "queries":
        path = owner.directory / "case-bindings" / (unit + ".json")
        if not path.exists():
            dataset.register_case(budget, owner, unit)
        q, _, ref = pipeline.load_case(budget, owner, unit)
        return dict(case_id=unit, query=ref, new_encodes=q["new_encodes"])
    if kind in {"batch", "replay"}:
        binding = owner.directory / "prediction-bindings" / (owner.split + "-" + unit + ".json")
        if kind == "batch" and binding.exists():
            return dict(prediction=record(binding)["prediction"], reused=True)
        output = pipeline.calculate(
            budget, owner, unit, category="technical" if kind == "replay" else "initial"
        )
        ref = pipeline.prediction(budget, owner, output, job_id=owner.job_id)
        if kind == "replay":
            if pipeline.semantic(owner.get(ref, "predictions")) != pipeline.semantic(
                pipeline.saved_prediction(owner, unit)
            ):
                raise InputError("D02 product/component or invariance replay disagrees")
        return dict(prediction=ref, new_encodes=output["new_query_encodes"])
    if kind == "score":
        from .scoring import score

        return score(budget, owner)
    if kind == "report":
        from .report import build

        return build(budget, owner)
    if kind in {"search", "validate"}:
        case_id = pipeline.case_for_revision(owner, spec["query"]["revision"])
        output = pipeline.calculate(
            budget, owner, case_id, spec["query"]["revision"], category(owner, case_id)
        )
        return dict(
            result=pipeline.product_result(budget, owner, value["job_id"], spec, output),
            new_encodes=output["new_query_encodes"],
        )
    if kind == "native-qa":
        return native(budget, owner, spec)
    from similar_sound_search.application.job import perform as application_perform

    return application_perform(budget, owner, value, unit, {})


def native(budget, owner, spec):
    """Independent PCM comparison of every product player against native source samples."""
    import numpy as np

    from similar_sound_search.application import media
    from similar_sound_search.inputs import decode
    from similar_sound_search.search import sources
    from similar_sound_search.search.report import pcm16

    value = api.result(owner.root, spec["job_id"], runtime=Runtime(owner.root, owner.split))
    checked = []
    for card in value["cards"]:
        for p in card["passages"]:
            if p["additional"]:
                continue
            for label in ("scored", "context"):
                path, clip = media.validate(owner, p[label]["record_hash"])
                original = sources.load(budget, clip["original"], context=owner)
                a, b = clip["bounds"]
                owner.charge(
                    budget,
                    read_audio_seconds=(b - a) / clip["original"]["source"]["sample_rate_hz"],
                )
                actual, meta = decode(path, budget)
                expected, _ = pcm16(original[a:b])
                if (
                    not np.array_equal(actual, expected.astype(np.float32) / 32768)
                    or meta["sample_count"] != b - a
                ):
                    raise InputError("D02 native QA differs from immutable scored/context interval")
                checked.append(dict(media=p[label]["record_hash"], bounds=[a, b], frames=b - a))
    return dict(passed=True, checked=checked)


def worker(request):
    from similar_sound_search.matchers.job import offline_network
    from similar_sound_search.matchers.runner import memory_check

    root, key = Path(request["root"]), request["job_id"]
    owner = Runtime(root, request["split"]).context(root, key)
    budget = CatalogueBudget(root, request["limits"])
    with project_lock(root), lock(root, "worker"), offline_network():
        value = api.job(owner, key)
        if contracts.consumer(owner) != value["consumer"] and not contracts.compatible(
            owner, value["consumer"]
        ):
            raise InputError("D02 worker consumer differs from its admitted job")
        done, encodes = [], 0
        for unit in graph(value):
            if committed(owner, key, unit) is not None:
                continue
            stop = owner.directory / "cancels" / (key + ".json")
            if stop.exists() and not record(stop).get("resumed", False):
                return dict(
                    status="ok",
                    state="cancelled",
                    completed=done,
                    new_encodes=encodes,
                    peak_working_bytes=memory_check(budget),
                )
            try:
                output = perform(budget, owner, value, unit)
            except contracts.Cancelled:
                return dict(
                    status="ok",
                    state="cancelled",
                    completed=done,
                    new_encodes=encodes,
                    peak_working_bytes=memory_check(budget),
                )
            owner.publish(
                budget,
                unit_path(owner, key, unit),
                dict(job_id=key, unit=unit, output=output),
                immutable=True,
            )
            done.append(unit)
            encodes += output.get("new_encodes", 0) if isinstance(output, dict) else 0
            if len(done) >= 4 or time.monotonic() - budget.started > 60:
                break
        complete = all(unit_path(owner, key, u).exists() for u in graph(value))
        return dict(
            status="ok",
            state="complete" if complete else "in_progress",
            completed=done,
            new_encodes=encodes,
            peak_working_bytes=memory_check(budget),
        )


def execute(owner, key, limits):
    from similar_sound_search.processing.runner import python_command

    env = os.environ.copy()
    env.update(
        OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONIOENCODING="utf-8"
    )
    try:
        completed = subprocess.run(
            python_command(owner.root / "scripts/evaluation-worker.py"),
            input=json.dumps(
                dict(root=str(owner.root), job_id=key, split=owner.split, limits=limits)
            ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return dict(
            status="failed",
            error_type="ResourceError",
            error="D02 actual worker exceeded 120s; reservation retained",
            uncertain=True,
        )
    try:
        answer = json.loads(completed.stdout)
    except ValueError:
        return dict(
            status="failed",
            error_type="WorkerExit",
            error="D02 worker missing JSON: " + completed.stderr[-1500:],
            uncertain=True,
        )
    if completed.returncode and answer.get("status") != "failed":
        raise InputError("D02 nonzero worker without explicit failure")
    return answer


def run(root, limits, key, split="development"):
    from similar_sound_search.application.context import PersistenceError
    from similar_sound_search.application.job import reconcile

    owner = Runtime(root, split).context(root, key)
    with lock(root, "coordinator"):
        with lock(root, "worker"):
            reconcile(owner, key)
        value = api.job(owner, key)
        units = graph(value)
        for _ in range(256):
            previous = record(api.state_path(owner, key))
            if previous["state"] == "complete":
                return previous
            slot = "attempt-" + uuid.uuid4().hex
            owner.reserve_attempt(slot)
            started = time.monotonic()
            running = dict(
                schema_version="d01-state-1",
                job_id=key,
                state="running",
                completed=sum(unit_path(owner, key, u).exists() for u in units),
                requested=len(units),
                result=None,
                error=None,
                attempt=slot,
            )
            try:
                budget = CatalogueBudget(root, limits)
                owner.publish(
                    budget, owner.directory / "active.json", dict(job_id=key, pid=os.getpid())
                )
                owner.publish(budget, api.state_path(owner, key), running)
                from similar_sound_search.indexing.commands import memory_status
                from similar_sound_search.matchers.runner import peak_memory

                server_memory = peak_memory()
                available = memory_status().get("available_commit_bytes")
                if (
                    available is not None
                    and available < limits["max_working_bytes"] + server_memory
                ):
                    raise ResourceError("D02 insufficient commit for server and bounded worker")
                answer = execute(owner, key, limits)
                # The child has its own actual-PID deadline. Final publication is
                # a fresh bounded coordinator transaction, as in the D01 runner.
                budget = CatalogueBudget(root, limits)
                outcome = answer.get(
                    "state", "blocked" if answer.get("error_type") == "ResourceError" else "failed"
                )
                if answer["status"] == "failed":
                    outcome = "blocked" if answer.get("error_type") == "ResourceError" else "failed"
                result = None
                if outcome == "complete":
                    output = committed(owner, key, units[-1])
                    if value["identity"]["request"]["kind"] in {"search", "validate"}:
                        result = output["result"]
                        owner.publish(
                            budget,
                            owner.directory / "last-complete.json",
                            dict(job_id=key, result=result),
                        )
                    else:
                        result = owner.put(
                            budget,
                            "results",
                            dict(
                                schema_version="d01-operation-result-1",
                                state="complete",
                                job_id=key,
                                operation=value["identity"]["request"]["kind"],
                                output=output,
                            ),
                        )
                answer.update(
                    server_peak_working_bytes=server_memory,
                    overlap_peak_bound=server_memory + answer.get("peak_working_bytes", 0),
                )
                terminal = {
                    **running,
                    "state": outcome,
                    "completed": sum(unit_path(owner, key, u).exists() for u in units),
                    "result": result,
                    "error": None
                    if answer["status"] == "ok"
                    else dict(
                        step="worker",
                        message=answer.get("error"),
                        error_type=answer.get("error_type"),
                    ),
                    "worker_evidence": answer,
                }
                owner.terminal(
                    slot,
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
                    slot, api.state_path(owner, key), terminal, elapsed=time.monotonic() - started
                )
            if terminal["state"] != "in_progress":
                return terminal
        raise ResourceError("D02 finite dispatch count exceeded")
