"""Fixed offline C01 workers, persistent reservations and separately measured actions."""

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
        with project_lock(root, ".c01-worker.lock"):
            budget = CatalogueBudget(root, limits)
            ledger = Ledger(owner.directory, budget, owner.cfg["policy"], "c01-ledger-1")
            seconds = min(
                limits["max_seconds"],
                ledger.value["ceilings"]["worker_seconds"] - ledger.value["charged_worker_seconds"],
            )
            if seconds < 2:
                raise ResourceError("C01 cumulative worker time exhausted; retain ledger/progress")
            if not (owner.directory / "work.json").exists():
                # Reserve the complete fixed metadata envelope, including shared
                # query/rank coordinators that use the unchanged JSON writer.
                owner.charge(budget, managed_output_bytes=32 * 1024**2)
            owner.charge(budget, workers=1)
            ledger.begin_worker(seconds)
        started = time.monotonic()
        result = None
        try:
            result = execute(
                {
                    **request,
                    "command": "indexing_step",
                    "cursor": cursor,
                    "limits": {**limits, "max_seconds": seconds},
                }
            )
        finally:
            with project_lock(root, ".c01-worker.lock"):
                budget = CatalogueBudget(root, limits)
                ledger = Ledger(owner.directory, budget, owner.cfg["policy"], "c01-ledger-1")
                elapsed = time.monotonic() - started
                ledger.end_worker(elapsed)
                path = owner.directory / "timing.json"
                timing = record(path) if path.exists() else {"worker_seconds_by_action": {}}
                action = request["indexing_action"]
                if action in {"build", "verify"}:
                    action += ":" + str(request.get("bank") or "plan") + ":" + request["scope"]
                timing["worker_seconds_by_action"][action] = (
                    timing["worker_seconds_by_action"].get(action, 0) + elapsed
                )
                peaks = timing.setdefault("peak_working_bytes_by_action", {})
                if result is not None and result.get("peak_working_bytes") is not None:
                    peaks[action] = max(peaks.get(action, 0), result["peak_working_bytes"])
                write_record(path, timing, budget)
        if result.get("status") != "ok" or result.get("state") != "in_progress":
            result["ledger"] = ledger.value
            result["work"] = record(owner.directory / "work.json")
            return result
        cursor = result.get("cursor", cursor)
    raise ResourceError(
        "C01 dispatch bound reached; resume unchanged command with retained charges"
    )


def worker(request, budget):
    with project_lock(budget.root, ".c01-worker.lock"), offline_network():
        from ..matchers.runner import memory_check
        from .commands import dispatch

        result = dispatch(request, budget, Context(budget.root, request.get("receipt")))
        result["peak_working_bytes"] = memory_check(budget)
        return result
