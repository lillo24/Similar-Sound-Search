"""One fixed offline A06 ledger, retained reservations and hard-deadline workers."""

import math
import time
from pathlib import Path

from ..catalogue.transfer import Ledger
from ..evaluation.artifacts import record, write_record
from ..matchers.job import offline_network
from ..resources import CatalogueBudget
from ..storage import InputError, ResourceError, project_lock
from .contracts import configuration


def charge(budget, **amounts):
    settings = configuration(budget.root)["policy"]
    keys = set(settings) - {"max_job_seconds", "max_http_attempts", "max_download_bytes"}
    path = budget.root / "data/runs/search/work.json"
    value = (
        record(path)
        if path.exists()
        else {
            "schema_version": "a06-work-1",
            "counts": {k[4:]: 0 for k in keys},
            "ceilings": {k[4:]: settings[k] for k in keys},
        }
    )
    if set(amounts) - set(value["counts"]):
        raise InputError("A06 accounting: unknown counter")
    for key in value["ceilings"]:
        value["ceilings"][key] = min(value["ceilings"][key], settings["max_" + key])
    # Persist a lower allowance even if the requested work is refused.
    write_record(path, value, budget)
    for key in value["ceilings"]:
        v = amounts.get(key, 0)
        old = value["counts"][key]
        if (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or v < 0
            or not isinstance(old, (int, float))
            or old < 0
            or old + v > value["ceilings"][key]
        ):
            raise ResourceError("A06 lifetime " + key + " exhausted; retain ledger/progress")
    for key in value["counts"]:
        value["counts"][key] += amounts.get(key, 0)
    write_record(path, value, budget)
    return value


def read_charge(budget, metadata, repetitions=1):
    charge(budget, read_audio_seconds=repetitions * metadata["duration_seconds"])


def run(request, execute):
    root = Path(request["root"])
    cfg = configuration(root)
    limits = {**request["limits"], "max_download_bytes": 0}
    cursor = 0
    for _ in range(cfg["policy"]["max_workers"]):
        with project_lock(root, ".a06-worker.lock"):
            budget = CatalogueBudget(root, limits)
            ledger = Ledger(root / "data/runs/search", budget, cfg["policy"], "a06-ledger-1")
            seconds = min(
                limits["max_seconds"],
                ledger.value["ceilings"]["worker_seconds"] - ledger.value["charged_worker_seconds"],
            )
            if seconds < 2:
                raise ResourceError("A06 cumulative worker time exhausted; retain ledger")
            charge(budget, workers=1)
            ledger.begin_worker(seconds)
        started = time.monotonic()
        try:
            result = execute(
                {
                    **request,
                    "command": "search_step",
                    "cursor": cursor,
                    "limits": {**limits, "max_seconds": seconds},
                }
            )
        finally:
            with project_lock(root, ".a06-worker.lock"):
                budget = CatalogueBudget(root, limits)
                ledger = Ledger(root / "data/runs/search", budget, cfg["policy"], "a06-ledger-1")
                elapsed = time.monotonic() - started
                ledger.end_worker(elapsed)
                path = root / "data/runs/search/timing.json"
                times = record(path) if path.exists() else {"worker_seconds_by_action": {}}
                action = request["search_action"]
                times["worker_seconds_by_action"][action] = (
                    times["worker_seconds_by_action"].get(action, 0) + elapsed
                )
                write_record(path, times, budget)
        if result.get("status") != "ok" or result.get("state") != "in_progress":
            result["ledger"] = ledger.value
            result["work"] = record(root / "data/runs/search/work.json")
            return result
        cursor = result.get("cursor", cursor)
    raise ResourceError("A06 dispatch bound reached; resume same command with retained charges")


def worker(request, budget):
    with project_lock(budget.root, ".a06-worker.lock"), offline_network():
        from .commands import dispatch

        return dispatch(request, budget)
