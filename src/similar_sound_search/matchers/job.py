"""A05 lifetime accounting and bounded resumable worker orchestration."""

import socket
import time
from contextlib import contextmanager
from pathlib import Path

from ..catalogue.transfer import Ledger
from ..evaluation.artifacts import record, write_record
from ..resources import CatalogueBudget
from ..storage import InputError, ResourceError, project_lock, read_json


@contextmanager
def offline_network():
    """A05 CLI children cannot download implicitly outside explicit acquisition."""
    old_connect, old_create = socket.socket.connect, socket.create_connection

    def refused(*args, **kwargs):
        raise InputError("A05 offline operation: network disabled; use explicit matchers acquire")

    socket.socket.connect = refused
    socket.create_connection = refused
    try:
        yield
    finally:
        socket.socket.connect, socket.create_connection = old_connect, old_create


def policy(root):
    value = read_json(root / "config/matchers.json")
    expected = {
        "max_download_bytes",
        "max_http_attempts",
        "max_job_seconds",
        "request_timeout_seconds",
        "attempts_per_url",
        "max_redirects",
        "backoff_seconds",
        "max_model_runs",
        "max_processed_windows",
        "max_feature_bytes",
        "windows_per_worker",
        "max_smoke_windows",
    }
    if value.get("schema_version") != "a05-policy-1" or set(value) != expected | {"schema_version"}:
        raise InputError("A05 policy: complete versioned numeric limits required")
    for key in expected:
        v = value[key]
        if (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not 0 < v <= 2**31
            or (key != "backoff_seconds" and not isinstance(v, int))
        ):
            raise InputError("A05 policy: invalid " + key)
    if (
        value["attempts_per_url"] > 2
        or value["max_redirects"] > 3
        or value["windows_per_worker"] > 128
    ):
        raise InputError("A05 policy: transport/batch limits exceeded")
    return {k: v for k, v in value.items() if k != "schema_version"}


def charge(budget, limits, **amounts):
    path = budget.root / "data/runs/matchers/work.json"
    value = (
        record(path)
        if path.exists()
        else {
            "counts": {
                k: 0 for k in ("model_runs", "processed_windows", "feature_bytes", "smoke_windows")
            },
            "ceilings": {
                k: limits["max_" + k]
                for k in ("model_runs", "processed_windows", "feature_bytes", "smoke_windows")
            },
        }
    )
    for key in value["ceilings"]:
        value["ceilings"][key] = min(value["ceilings"][key], limits["max_" + key])
        amount = amounts.get(key, 0)
        if (
            not isinstance(amount, int)
            or amount < 0
            or value["counts"][key] + amount > value["ceilings"][key]
        ):
            raise ResourceError("A05 lifetime " + key + " exhausted; preserve work ledger")
        value["counts"][key] += amount
    write_record(path, value, budget)


def run(request, execute):
    if request.get("split") != "development":
        raise InputError(
            "A05 refuses held-out inference/scoring; A06 must explicitly initiate its final check"
        )
    root = Path(request["root"])
    settings = policy(root)
    limits = {
        **request["limits"],
        "max_download_bytes": min(
            request["limits"]["max_download_bytes"], settings["max_download_bytes"]
        ),
    }
    # One operation can resume at most the finite total window allowance in bounded workers.
    for _ in range(settings["max_processed_windows"] // settings["windows_per_worker"] + 2):
        with project_lock(root, ".a05-worker.lock"):
            budget = CatalogueBudget(root, limits)
            ledger = Ledger(root / "data/runs/matchers", budget, settings, "a05-ledger-1")
            seconds = min(
                limits["max_seconds"],
                ledger.value["ceilings"]["worker_seconds"] - ledger.value["charged_worker_seconds"],
            )
            if seconds < 2:
                raise ResourceError("A05 lifetime worker allowance exhausted; preserve ledger")
            ledger.begin_worker(seconds)
        started = time.monotonic()
        try:
            result = execute(
                {
                    **request,
                    "command": "matchers_step",
                    "policy": settings,
                    "limits": {**limits, "max_seconds": seconds},
                }
            )
        finally:
            with project_lock(root, ".a05-worker.lock"):
                ledger = Ledger(
                    root / "data/runs/matchers",
                    CatalogueBudget(root, limits),
                    settings,
                    "a05-ledger-1",
                )
                ledger.end_worker(time.monotonic() - started)
        if result.get("state") != "in_progress" or result.get("status") != "ok":
            result["ledger"] = ledger.value
            return result
    raise ResourceError(
        "A05 bounded worker count exhausted; rerun same command with retained progress"
    )


def worker(request, budget):
    from .correction import revise

    with project_lock(budget.root, ".a05-worker.lock"):
        from .runner import dispatch

        if request["matcher_action"] == "acquire":
            return dispatch(request, budget)
        with offline_network():
            if request["matcher_action"] == "freeze":
                return revise(budget)
            return dispatch(request, budget)
