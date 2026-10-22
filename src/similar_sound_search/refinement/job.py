"""Offline 120-second C03 workers; cumulative reservations survive every retry."""

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
    owner = Context(root)
    limits = {**request["limits"], "max_download_bytes": 0}
    cursor = 0
    for _ in range(owner.cfg["policy"]["max_workers"]):
        with project_lock(root, ".c03-worker.lock"):
            budget = CatalogueBudget(root, limits)
            ledger = Ledger(owner.directory, budget, owner.cfg["policy"], "c03-ledger-1")
            seconds = min(
                limits["max_seconds"],
                ledger.value["ceilings"]["worker_seconds"] - ledger.value["charged_worker_seconds"],
            )
            if seconds < 2:
                raise ResourceError("C03 cumulative time exhausted; retain progress")
            if not (owner.directory / "work.json").exists():
                owner.charge(budget, managed_output_bytes=96 * 1024**2)
            owner.charge(budget, workers=1)
            ledger.begin_worker(seconds)
        result = None
        started = time.monotonic()
        try:
            result = execute(
                {
                    **request,
                    "command": "refinement_step",
                    "cursor": cursor,
                    "limits": {**limits, "max_seconds": seconds},
                }
            )
        finally:
            with project_lock(root, ".c03-worker.lock"):
                budget = CatalogueBudget(root, limits)
                ledger = Ledger(owner.directory, budget, owner.cfg["policy"], "c03-ledger-1")
                elapsed = time.monotonic() - started
                ledger.end_worker(elapsed)
                path = owner.directory / "timing.json"
                timing = (
                    record(path)
                    if path.exists()
                    else {"worker_seconds_by_action": {}, "peak_working_bytes_by_action": {}}
                )
                action = request["refinement_action"]
                timing["worker_seconds_by_action"][action] = (
                    timing["worker_seconds_by_action"].get(action, 0) + elapsed
                )
                if result is not None:
                    timing["peak_working_bytes_by_action"][action] = max(
                        timing["peak_working_bytes_by_action"].get(action, 0),
                        result.get("peak_working_bytes", 0),
                    )
                write_record(path, timing, budget)
        if result.get("status") != "ok" or result.get("state") != "in_progress":
            return {**result, "ledger": ledger.value, "work": record(owner.directory / "work.json")}
        if request.get("pilot"):
            return {**result, "ledger": ledger.value, "work": record(owner.directory / "work.json")}
        cursor = result.get("cursor", cursor)
    raise ResourceError("C03 worker dispatch bound; resume same command with retained charges")


def worker(request, budget):
    from ..matchers.runner import memory_check
    from .commands import dispatch

    with project_lock(budget.root, ".c03-worker.lock"), offline_network():
        result = dispatch(request, budget, Context(budget.root))
        return {**result, "peak_working_bytes": memory_check(budget)}
