"""CLI routing and bounded metadata/setup units; numerical ownership stays separate."""

import json
import time
from pathlib import Path

from ..matchers.job import offline_network
from ..matchers.runner import memory_check
from ..resources import CatalogueBudget
from ..storage import InputError, contained, project_lock, read_json
from . import api, job
from .context import Context


def historical_workers(root):
    """An orphan from any earlier stage still owns numerical concurrency one."""
    for name in ("a03", "a04", "a05", "a06", "b01", "b02", "b03", "c01", "c02", "c03"):
        with project_lock(root, "." + name + "-worker.lock"):
            pass


def admin(request, execute):
    owner = Context(Path(request["root"]))
    with project_lock(owner.root, ".c04-coordinator.lock"), project_lock(owner.root):
        historical_workers(owner.root)
        with project_lock(owner.root, ".c04-worker.lock"):
            budget = CatalogueBudget(owner.root, request["limits"])
            seq, seconds = job.reserve(owner, budget)
        started = time.monotonic()
        result = execute(
            {
                **request,
                "command": "processing_admin",
                "reservation": seq,
                "limits": {**request["limits"], "max_seconds": seconds, "max_download_bytes": 0},
            }
        )
        with project_lock(owner.root, ".c04-worker.lock"):
            job.settle(
                owner,
                CatalogueBudget(owner.root, request["limits"]),
                seq,
                seconds,
                time.monotonic() - started,
                result,
            )
        return {**result, "pool": owner.pool()}


def worker(request, budget):
    if request["command"] == "processing_step":
        return job.worker(request, budget)
    with project_lock(budget.root, ".c04-worker.lock"), offline_network():
        from . import validation

        owner = Context(budget.root)
        action = request["processing_action"]
        if action == "known-answer":
            answer = validation.known_answer()
        elif action == "preflight":
            from ..indexing.commands import memory_status
            from ..search.contracts import frozen

            frozen(budget)
            answer = dict(
                status="ok",
                memory=memory_status(),
                resources=budget.reserve(65536),
                frozen_representation=True,
                pool=owner.pool(),
            )
        elif action == "fixtures":
            answer = validation.fixtures(budget, owner)
        elif action == "clean-check":
            answer = validation.clean_check(budget, owner, request["input"])
        elif action == "derive-query":
            from ..retrieval.context import derive_query

            if not request.get("revision"):
                raise InputError("processing derive-query requires --revision EXACT_ID")
            answer = derive_query(budget, owner, request["revision"])
        elif action == "import":
            answer = validation.register_sources(budget, owner, read_json(request["input"]))
        else:
            raise InputError("C04 unsupported admin unit")
        return {**answer, "peak_working_bytes": memory_check(budget), "kind": action}


def main(args, request, execute):
    root = Path(request["root"])
    owner, action = Context(root), args.processing_action
    report = contained(args.report or owner.reports / "last-command.json", owner.reports)
    started = time.monotonic()
    value = None
    if args.input and action not in {"plan", "import", "clean-check"}:
        kind = "plans" if action == "run" else "results" if action == "result" else "jobs"
        value = api.reference(owner, args.input, kind)
    try:
        if action == "plan":
            if args.input is None:
                raise InputError("processing plan requires an explicit input revision JSON")
            previous = api.reference(owner, args.previous, "plans") if args.previous else None
            answer = dict(
                status="ok",
                state="planned",
                plan=api.plan(root, request["limits"], api.input_file(root, args.input), previous),
            )
        elif action == "run":
            if value is None or args.job is None:
                raise InputError("processing run requires immutable plan and --job NAME")
            with project_lock(root):
                historical_workers(root)
                answer = job.run({**request, "plan_ref": value}, execute)
        elif action == "resume":
            if value is None:
                raise InputError("processing resume requires immutable job reference")
            with project_lock(root):
                historical_workers(root)
                answer = job.run({**request, "job_ref": value, "resume": True}, execute)
        elif action in {"status", "cancel"}:
            if value is None:
                raise InputError("processing " + action + " requires immutable job reference")
            answer = (
                dict(status="ok", **api.status(root, value))
                if action == "status"
                else api.cancel(root, value)
            )
        elif action == "result":
            answer = dict(status="ok", result=api.result(root, value))
        elif action == "inventory":
            answer = dict(status="ok", **api.inventory(root))
        elif action == "serve":
            if value is None:
                raise InputError("processing serve requires a completed job")
            state = api.status(root, value)
            if state["state"] != "complete":
                raise InputError("C04 requested job is incomplete; last-complete is separate")
            result = api.result(root, state["result"])
            if result["playback"] is None:
                raise InputError("C04 job has no playable historical result")
            from ..search.report import serve

            serve(root, root / result["playback"]["path"], args.port, root / "reports/local/c03")
            return 0
        else:
            answer = admin(request, execute)
    except (InputError, OSError, ValueError) as exc:
        answer = dict(status="failed", error_type=type(exc).__name__, error=str(exc))
    answer.update(command="processing", action=action, wall_seconds=time.monotonic() - started)
    # Summaries are counted and contained in C04; read-only status/cancel do not write
    # to the numerical pool while a worker owns it. Their bounded response is stdout.
    if action not in {"status", "cancel", "inventory", "result"}:
        with project_lock(root, ".c04-coordinator.lock"):
            owner.publish(CatalogueBudget(root, request["limits"]), report, answer)
    print(json.dumps(answer, indent=2, allow_nan=False))
    return 0 if answer["status"] == "ok" else 1
