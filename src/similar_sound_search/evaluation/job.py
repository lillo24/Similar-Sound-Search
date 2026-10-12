"""Single bounded A04 worker and durable allowances, separate from catalogue acquisition."""

import time
from pathlib import Path

from ..catalogue.transfer import Ledger
from ..resources import CatalogueBudget
from ..storage import InputError, ResourceError, project_lock, read_json

FIELDS = {
    "max_download_bytes",
    "max_http_attempts",
    "max_job_seconds",
    "max_generation_bytes",
    "max_generation_seconds",
    "max_generation_items",
    "request_timeout_seconds",
    "attempts_per_url",
    "max_redirects",
    "backoff_seconds",
}


def load_policy(root):
    value = read_json(root / "config/evaluation.json")
    if value.get("schema_version") != "a04-policy-1" or set(value) != FIELDS | {"schema_version"}:
        raise InputError("A04 policy: complete a04-policy-1 configuration required")
    for key in FIELDS:
        number = value[key]
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not 0 < number <= 2**31
            or (key != "backoff_seconds" and not isinstance(number, int))
        ):
            raise InputError(f"A04 policy: invalid finite positive {key}")
    if value["attempts_per_url"] > 2 or value["max_redirects"] > 3:
        raise InputError("A04 policy: retries/redirects cannot exceed shared transport limits")
    return {k: v for k, v in value.items() if k != "schema_version"}


def run(request, execute):
    root = Path(request["root"])
    policy = load_policy(root)
    limits = {
        **request["limits"],
        "max_download_bytes": min(
            request["limits"]["max_download_bytes"], policy["max_download_bytes"]
        ),
    }
    directory = root / "data/runs/evaluation"
    with project_lock(root, ".a04-worker.lock"):
        budget = CatalogueBudget(root, limits)
        ledger = Ledger(directory, budget, policy, "a04-ledger-1")
        remaining = (
            ledger.value["ceilings"]["worker_seconds"] - ledger.value["charged_worker_seconds"]
        )
        seconds = min(limits["max_seconds"], remaining)
        if seconds < 2:
            raise ResourceError(
                "A04 lifetime worker allowance exhausted; "
                "preserve ledger and inspect completed artifacts"
            )
        ledger.begin_worker(seconds)
    started = time.monotonic()
    try:
        result = execute(
            {
                **request,
                "command": "evaluation_step",
                "policy": policy,
                "limits": {**limits, "max_seconds": seconds},
            }
        )
    finally:
        with project_lock(root, ".a04-worker.lock"):
            budget = CatalogueBudget(root, limits)
            ledger = Ledger(directory, budget, policy, "a04-ledger-1")
            ledger.end_worker(time.monotonic() - started)
    result["ledger"] = ledger.value
    result["resume"] = (
        "Repeat the same explicit command; completed verified assets reuse; budgets never reset"
    )
    return result


def worker(request, budget):
    from .artifacts import charge_generation
    from .published import inspect_dataset, validate_downloads
    from .scoring import known_answers, score_file
    from .suite import build, mapping_diagnostics, validate

    directory = budget.root / "data/runs/evaluation"
    action = request["evaluation_action"]
    with project_lock(budget.root, ".a04-worker.lock"):
        ledger = Ledger(directory, budget, request["policy"], "a04-ledger-1")
        if action == "acquire":
            return inspect_dataset(budget, ledger)
        if action == "generate":
            return build(budget, request["policy"], directory, request.get("pilot", False))
        if action == "validate":
            result = validate(budget, request["split"])
            path = directory / "published/dataset.json"
            result["published"] = (
                validate_downloads(budget) if path.exists() else {"availability": "not_imported"}
            )
            return result
        if action == "maps":
            # Conservative per-attempt cap for six small mapping bundles, including reuse.
            charge_generation(directory, budget, request["policy"], 6 * 262144, 8)
            return mapping_diagnostics(budget)
        if action == "known-answer":
            return known_answers(budget)
        if action == "score":
            if not request.get("input"):
                raise InputError("evaluation score: explicit prediction JSON required")
            if request["split"] == "all":
                raise InputError("evaluation score: choose one split explicitly")
            choice = read_json(request["final_choice"]) if request.get("final_choice") else None
            return score_file(budget, read_json(request["input"]), request["split"], choice)
        raise InputError(f"evaluation: unsupported action {action}")
