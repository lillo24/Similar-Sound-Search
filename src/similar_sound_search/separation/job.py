"""One fixed offline B02 ledger, retained reservations and hard-deadline workers."""

import time
from pathlib import Path

from ..catalogue.transfer import Ledger
from ..evaluation.artifacts import record, write_record
from ..matchers.job import offline_network
from ..resources import CatalogueBudget
from ..storage import ResourceError, project_lock
from .context import Context


def run(request, execute):
    root = Path(request["root"])
    context = Context(root)
    limits = {**request["limits"], "max_download_bytes": 0}
    cursor = 0
    for _ in range(context.cfg["policy"]["max_workers"]):
        with project_lock(root, ".b02-worker.lock"):
            budget = CatalogueBudget(root, limits)
            ledger = Ledger(context.directory, budget, context.cfg["policy"], "b02-ledger-1")
            seconds = min(
                limits["max_seconds"],
                ledger.value["ceilings"]["worker_seconds"] - ledger.value["charged_worker_seconds"],
            )
            if seconds < 2:
                raise ResourceError("B02 cumulative worker time exhausted; retain ledger")
            context.charge(budget, workers=1)
            ledger.begin_worker(seconds)
        started = time.monotonic()
        try:
            result = execute(
                {
                    **request,
                    "command": "separation_step",
                    "cursor": cursor,
                    "limits": {**limits, "max_seconds": seconds},
                }
            )
        finally:
            with project_lock(root, ".b02-worker.lock"):
                budget = CatalogueBudget(root, limits)
                ledger = Ledger(context.directory, budget, context.cfg["policy"], "b02-ledger-1")
                elapsed = time.monotonic() - started
                ledger.end_worker(elapsed)
                path = context.directory / "timing.json"
                timing = record(path) if path.exists() else {"worker_seconds_by_action": {}}
                action = request["separation_action"]
                timing["worker_seconds_by_action"][action] = (
                    timing["worker_seconds_by_action"].get(action, 0) + elapsed
                )
                write_record(path, timing, budget)
        if result.get("status") != "ok" or result.get("state") != "in_progress":
            result["ledger"] = ledger.value
            result["work"] = record(context.directory / "work.json")
            return result
        cursor = result.get("cursor", cursor)
    raise ResourceError("B02 dispatch bound reached; resume same command with retained charges")


def worker(request, budget):
    with project_lock(budget.root, ".b02-worker.lock"), offline_network():
        from .commands import dispatch

        return dispatch(request, budget, Context(budget.root, request.get("receipt")))
