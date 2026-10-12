"""Finite acquisition coordinator; bounded workers share durable receipts and one project lock."""

import re
import time
from collections import Counter
from pathlib import Path

from ..resources import Budget
from ..storage import (
    InputError,
    ResourceError,
    bounded_json,
    contained,
    digest,
    project_lock,
    read_json,
)
from .transfer import Ledger, utc_now

POLICY_FIELDS = {
    "schema_version",
    "source",
    "query",
    "search_rows",
    "max_source_items",
    "max_requested_recordings",
    "max_tracks_per_artist",
    "max_audio_bytes",
    "min_duration_seconds",
    "max_duration_seconds",
    "analysis_rate_hz",
    "analysis_seconds",
    "analysis_channels",
    "max_http_attempts",
    "max_job_seconds",
    "max_invocation_seconds",
    "max_operations_per_invocation",
    "request_timeout_seconds",
    "attempts_per_url",
    "max_redirects",
    "backoff_seconds",
}


def load_policy(path):
    policy = read_json(path)
    if (
        not isinstance(policy, dict)
        or set(policy) != POLICY_FIELDS
        or policy.get("schema_version") != "a03-policy-1"
    ):
        raise InputError("catalogue policy: expected complete a03-policy-1 contract")
    if (
        policy["source"] != "internet_archive"
        or not isinstance(policy["query"], str)
        or not policy["query"]
    ):
        raise InputError("catalogue policy: Internet Archive query required")
    bounds = {
        "search_rows": (1, 1000),
        "max_source_items": (1, 100),
        "max_requested_recordings": (1, 300),
        "max_tracks_per_artist": (1, 10),
        "max_audio_bytes": (1, 268435456),
        "min_duration_seconds": (0, 900),
        "max_duration_seconds": (1, 900),
        "analysis_rate_hz": (1, 192000),
        "analysis_seconds": (1, 900),
        "max_http_attempts": (1, 1200),
        "max_job_seconds": (1, 3600),
        "max_invocation_seconds": (1, 600),
        "max_operations_per_invocation": (1, 64),
        "request_timeout_seconds": (0.01, 30),
        "attempts_per_url": (1, 3),
        "max_redirects": (0, 3),
        "backoff_seconds": (0, 2),
    }
    for key, (low, high) in bounds.items():
        value = policy[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not low <= value <= high
        ):
            raise InputError(f"catalogue policy: invalid {key}")
        if key not in {"request_timeout_seconds", "backoff_seconds"} and not isinstance(value, int):
            raise InputError(f"catalogue policy: {key} must be an integer")
    if (
        policy["analysis_channels"] != "preserve"
        or policy["min_duration_seconds"] >= policy["max_duration_seconds"]
    ):
        raise InputError(
            "catalogue policy: preserve mixture channels and ordered durations required"
        )
    return policy


def job_paths(root, name, local=False):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", name) or name in {"con", "prn", "aux", "nul"}:
        raise InputError("catalogue job: use a safe lowercase name (1–40 letters/digits/hyphens)")
    directory = contained(root / "data/runs/catalogue" / name, root)
    output = contained(
        root / ("manifests/private/catalogue" if local else "manifests/catalogue") / name, root
    )
    return directory, output


def write_manifest(path, value, budget):
    document = {**value, "record_hash": digest(value)}
    bounded_json(path, document, budget)


def manifest(path):
    value = read_json(path)
    if value.get("record_hash") != digest({k: v for k, v in value.items() if k != "record_hash"}):
        raise InputError(f"catalogue manifest {path.name}: integrity mismatch")
    return value


def worker(request, budget):
    """The extra worker lock prevents a parent crash from allowing an orphan budget race."""
    from .ingestion import ingest
    from .source import release, search

    directory = contained(budget.root / request["directory"], budget.root / "data/runs/catalogue")
    output = contained(budget.root / request["output"], budget.root)
    with project_lock(budget.root, ".a03-worker.lock"):
        ledger = Ledger(directory, budget, request["policy"])
        operation = request["operation"]
        if operation == "search":
            return {"status": "ok", "payload": search(directory, ledger)}
        if operation == "release":
            return {"status": "ok", "payload": release(request["item"], directory, ledger)}
        if operation == "ingest":
            descriptor_path = directory / "selection" / (request["entry_id"] + ".json")
            if not descriptor_path.exists():
                restored = manifest(output / "sources" / (request["entry_id"] + ".json"))
                write_manifest(
                    descriptor_path,
                    {k: v for k, v in restored.items() if k != "record_hash"},
                    budget,
                )
            descriptor = manifest(descriptor_path)
            descriptor = {k: v for k, v in descriptor.items() if k != "record_hash"}
            return ingest(
                descriptor,
                directory,
                ledger,
                output,
                request.get("local_input"),
                request.get("refresh", False),
            )
        raise InputError(f"catalogue worker: unsupported operation {operation}")


def run(request, execute):
    """Caller holds the A02 project lock. Never reset lifetime allowances on resumption."""
    root = Path(request["root"])
    limits = request["limits"]
    policy = load_policy(request.get("catalogue_policy") or root / "config/catalogue.json")
    action = request["catalogue_action"]
    local = action == "import"
    reselect = request.get("reselect", False)
    if reselect and action != "acquire":
        raise InputError("catalogue --reselect: only acquisition coverage can be revised")
    directory, output = job_paths(root, request["job"], local)
    if action == "verify" and (directory / "job.json").exists():
        local = manifest(directory / "job.json")["identity"]["source"] == "local"
        directory, output = job_paths(root, request["job"], local)
    if action == "verify" and not directory.exists():
        raise InputError("catalogue verify: job does not exist")
    started = time.monotonic()
    operations = 0
    results = []
    stop = None

    def budget():
        return Budget(root, limits)

    with project_lock(root, ".a03-worker.lock"):
        state_path = directory / "job.json"
        identity = {"policy": policy, "source": "local" if local else policy["source"]}
        if state_path.exists():
            state = manifest(state_path)
            if state["identity"] != identity:
                before = state["identity"]
                frozen = ("source", "query", "search_rows")
                if (
                    not reselect
                    or before["source"] != identity["source"]
                    or any(before["policy"][key] != policy[key] for key in frozen)
                ):
                    raise InputError(
                        "catalogue resume: policy changed; use --reselect for explicit coverage "
                        "revision; provider/query/search snapshot cannot change"
                    )
                write_manifest(
                    directory / "policy-history" / (digest(before) + ".json"), before, budget()
                )
                state = {k: v for k, v in state.items() if k != "record_hash"}
                state["identity"] = identity
                write_manifest(state_path, state, budget())
        else:
            state = {"schema_version": "a03-job-1", "identity": identity, "created_at": utc_now()}
            write_manifest(state_path, state, budget())
        Ledger(directory, budget(), policy)

    def step(operation, **arguments):
        nonlocal operations, stop
        remaining = policy["max_invocation_seconds"] - (time.monotonic() - started)
        if operations >= policy["max_operations_per_invocation"] or remaining < 2:
            stop = "bounded invocation ended; rerun the same command to resume"
            return None
        with project_lock(root, ".a03-worker.lock"):
            ledger = Ledger(directory, budget(), policy)
            seconds = min(
                limits["max_seconds"],
                remaining,
                ledger.value["ceilings"]["worker_seconds"] - ledger.value["charged_worker_seconds"],
            )
            if seconds < 2:
                stop = "durable catalogue job time allowance exhausted"
                return None
            ledger.begin_worker(seconds)
        clock = time.monotonic()
        result = execute(
            {
                "command": "catalogue_step",
                "root": str(root),
                "limits": {**limits, "max_seconds": seconds},
                "policy": policy,
                "directory": directory.relative_to(root).as_posix(),
                "output": output.relative_to(root).as_posix(),
                "operation": operation,
                **arguments,
            }
        )
        with project_lock(root, ".a03-worker.lock"):
            ledger = Ledger(directory, budget(), policy)
            ledger.end_worker(time.monotonic() - clock)
        operations += 1
        results.append({"operation": operation, **arguments, **result})
        if result["status"] != "ok" and result.get("error_type") == "ResourceError":
            stop = result["error"]
        return result

    selection_path = output / "selection.json"

    def process_selection(selection, take, refresh):
        # A capped invocation must resume after its last completed asset, rather than
        # repeatedly verifying the first batch and starving every later recording.
        for item in selection["selected"]:
            key = item["entry_id"]
            private_path = directory / "selection" / (key + ".json")
            public_path = output / "sources" / (key + ".json")
            descriptor = manifest(private_path if private_path.exists() else public_path)
            raw = {k: v for k, v in descriptor.items() if k != "record_hash"}
            if digest(raw) != item["descriptor_sha256"]:
                raise InputError("catalogue descriptor differs from frozen selection")
            if not public_path.exists():
                write_manifest(public_path, raw, budget())
        selected = selection["selected"][:take]
        pass_key = digest([selection["record_hash"], take, refresh, action])
        progress_path = directory / "passes" / (pass_key + ".json")
        progress = manifest(progress_path) if progress_path.exists() else {"next_index": 0}
        for index in range(progress["next_index"], len(selected)):
            result = step("ingest", entry_id=selected[index]["entry_id"], refresh=refresh)
            if result is None or stop:
                break
            write_manifest(
                progress_path,
                {"next_index": 0 if index + 1 == len(selected) else index + 1},
                budget(),
            )

    if action == "import":
        from .ingestion import entry_key, local_descriptor

        descriptor = local_descriptor(
            request["input"],
            read_json(request["context"]),
            request.get("data_role", "real_recording_discovery"),
        )
        key = entry_key(descriptor)
        # Original explicit path/access evidence stays in ignored job metadata and child requests.
        write_manifest(directory / "selection" / (key + ".json"), descriptor, budget())
        selected = manifest(selection_path)["selected"] if selection_path.exists() else []
        selected = [item for item in selected if item["entry_id"] != key]
        selected.append({"entry_id": key, "descriptor_sha256": digest(descriptor)})
        if len(selected) > policy["max_requested_recordings"]:
            raise ResourceError("catalogue import: job entry count cap exceeded")
        write_manifest(
            selection_path,
            {
                "schema_version": "a03-selection-1",
                "selected": selected,
                "requested_count": len(selected),
                "source": "explicit_local_import",
            },
            budget(),
        )
        step("ingest", entry_id=key, local_input=request["input"], refresh=request["refresh"])
    elif action == "acquire":
        discovery_path = directory / "discovery.json"
        if reselect:
            if selection_path.exists():
                prior = manifest(selection_path)
                write_manifest(
                    output / "selection-history" / (prior["record_hash"] + ".json"),
                    {k: v for k, v in prior.items() if k != "record_hash"},
                    budget(),
                )
                selection_path.unlink()
            result = step("search")
            if result and result["status"] == "ok":
                write_manifest(discovery_path, result["payload"], budget())
            else:
                stop = result.get("error") if result else stop
        if not discovery_path.exists():
            result = step("search")
            if result and result["status"] == "ok":
                write_manifest(discovery_path, result["payload"], budget())
            elif result:
                stop = result.get("error", "source discovery failed")
        if discovery_path.exists() and not selection_path.exists() and not stop:
            discovery = manifest(discovery_path)
            for item in discovery["item_ids"]:
                path = directory / "releases" / (digest(item) + ".json")
                if path.exists() and not (reselect and manifest(path).get("failure")):
                    continue
                result = step("release", item=item)
                if result is None or stop:
                    break
                payload = (
                    result["payload"]
                    if result["status"] == "ok"
                    else {
                        "item_id": item,
                        "candidates": [],
                        "exclusions": {"source_fetch_failure": 1},
                        "failure": result.get("error"),
                    }
                )
                write_manifest(path, payload, budget())
            paths = [
                directory / "releases" / (digest(item) + ".json") for item in discovery["item_ids"]
            ]
            if all(path.exists() for path in paths) and not stop:
                from .ingestion import entry_key
                from .source import select

                releases = [manifest(path) for path in paths]
                selection = select(releases, policy)
                entries = selection.pop("entries")
                selected = []
                for entry in entries:
                    key = entry_key(entry)
                    write_manifest(directory / "selection" / (key + ".json"), entry, budget())
                    write_manifest(output / "sources" / (key + ".json"), entry, budget())
                    selected.append({"entry_id": key, "descriptor_sha256": digest(entry)})
                exclusions = Counter()
                for release_record in releases:
                    exclusions.update(release_record["exclusions"])
                selection.update(
                    {
                        "selected": selected,
                        "discovery": discovery,
                        "exclusions": dict(exclusions),
                        "policy": policy,
                    }
                )
                write_manifest(selection_path, selection, budget())
        if selection_path.exists() and not stop:
            selection = manifest(selection_path)
            if selection.get("policy") != policy:
                raise InputError(
                    "catalogue: published selection policy changed; use --reselect explicitly"
                )
            take = request.get("take") or policy["max_requested_recordings"]
            if not 1 <= take <= policy["max_requested_recordings"]:
                raise InputError("catalogue --take: must be within the configured requested count")
            process_selection(selection, take, request["refresh"])
    elif action == "verify":
        if not selection_path.exists():
            raise InputError("catalogue verify: no frozen selection")
        selection = manifest(selection_path)
        process_selection(selection, len(selection["selected"]), False)
    if selection_path.exists():
        selection = manifest(selection_path)
        records = []
        states = Counter()
        for item in selection["selected"]:
            path = output / "entries" / (item["entry_id"] + ".json")
            if not path.exists():
                states["not_ready"] += 1
                continue
            record = read_json(path)
            if record["state"] == "ready":
                if record.get("record_hash") != digest(
                    {k: v for k, v in record.items() if k != "record_hash"}
                ):
                    raise InputError("catalogue ready record integrity failed")
                private_path = directory / "entries" / (item["entry_id"] + ".json")
                local_state = read_json(private_path) if private_path.exists() else None
                if (
                    not local_state
                    or local_state["state"] != "ready"
                    or local_state["record"]["record_hash"] != record["record_hash"]
                ):
                    states["not_locally_ready"] += 1
                    continue
                paths = [
                    (root / record[area]["local_path"], record[area]["file_bytes"])
                    for area in ("source_asset", "analysis_derivative")
                ]
                if any(not path.is_file() or path.stat().st_size != size for path, size in paths):
                    states["missing_or_changed_local_asset"] += 1
                    continue
                records.append(record)
            states[record["state"]] += 1
        from .ingestion import duplicate_groups

        groups = duplicate_groups(records)
        write_manifest(output / "groups.json", groups, budget())
        requested = selection["requested_count"]
        distinct = len(groups["groups"])
        counts = {
            "requested": requested,
            "selected": len(selection["selected"]),
            "ready_assets": len(records),
            "distinct_recordings": distinct,
            "artists": len(
                {r["recording"]["artist"].casefold() for r in records if r["recording"]["artist"]}
            ),
            "usable_original_seconds": sum(r["source_asset"]["duration_seconds"] for r in records),
            "analysis_seconds": sum(r["analysis_derivative"]["duration_seconds"] for r in records),
            "source_kinds": dict(Counter(r["source_asset"]["kind"] for r in records)),
            "known_original_offsets": sum(
                r["timestamp_mapping"]["original_recording_offset_seconds"] is not None
                for r in records
            ),
            "duplicate_assets": len(records) - distinct,
            "data_roles": dict(Counter(r["data_role"] for r in records)),
            "real_ready_assets": sum(r["data_role"] == "real_recording_discovery" for r in records),
            "states": dict(states),
            "genres": dict(
                Counter(
                    manifest(directory / "selection" / (r["entry_id"] + ".json"))["genre"]
                    or "unspecified"
                    for r in records
                )
            ),
        }
    else:
        counts = {
            "requested": policy["max_requested_recordings"],
            "selected": 0,
            "ready_assets": 0,
            "distinct_recordings": 0,
        }
    with project_lock(root, ".a03-worker.lock"):
        ledger = Ledger(directory, budget(), policy)
    failed = [r for r in results if r["status"] != "ok"]
    complete = counts["distinct_recordings"] >= counts["requested"]
    result = {
        "status": "failed" if stop or failed or not counts["ready_assets"] else "ok",
        "assessment": "complete" if complete and not stop and not failed else "partial",
        "job": request["job"],
        "counts": counts,
        "stop_reason": stop,
        "operations_this_invocation": operations,
        "reused_this_invocation": sum(r.get("reused", False) for r in results),
        "failures_this_invocation": [
            {
                k: v
                for k, v in r.items()
                if k in {"operation", "entry_id", "item", "error", "error_type"}
            }
            for r in failed
        ],
        "ledger": ledger.value,
        "managed_bytes": budget().managed_bytes(),
        "invocation_seconds": time.monotonic() - started,
        "catalogue_path": output.relative_to(root).as_posix(),
        "resume": (
            "Repeat the same command; policy/source selection and cumulative allowances are pinned"
        ),
        "retrieval_quality": "not_measured",
    }
    sanitized = {
        **result,
        "stop_reason": "See private CLI report for step/resource details" if stop else None,
        "failures_this_invocation": [
            {k: v for k, v in failure.items() if k != "error"}
            for failure in result["failures_this_invocation"]
        ],
    }
    write_manifest(output / "summary.json", sanitized, budget())
    return result
