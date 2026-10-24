"""Explicit preflight/generate/audit/index/query/run/score/report commands; no hidden scores."""

import argparse
import json
import shutil
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.storage import InputError

from . import contracts, jobs
from .context import MIB, Context


def preflight(root, limits):
    owner = Context(root)
    contracts.consumer(owner)
    budget = CatalogueBudget(root, limits)
    budget.cap("max_managed_bytes", budget.managed_bytes() + 1024 * MIB, "D02 complete path")
    if shutil.disk_usage(root).free < limits["min_free_bytes"] + 1024 * MIB:
        raise InputError("D02 full managed allowance cannot retain starter free-space headroom")
    # Protect later stages first; no per-case allocations or replenishment.
    for name, size in (
        ("confirmation", 56),
        ("delivery", 28),
        ("report", 12),
        ("prepare", 24),
        ("development", 72),
    ):
        owner.admit(name, size * MIB, acceptance=name in {"confirmation", "delivery", "report"})
    owner.allocation = "prepare"
    path = owner.directory / "preflight.json"
    if path.exists():
        return record(path)
    owner.charge(budget, managed_output_bytes=64 * MIB)
    value = dict(
        schema_version="d02-preflight-1",
        protocol=owner.protocol["record_hash"],
        consumer=contracts.consumer(owner),
        managed_before=budget.managed_bytes(),
        qa_reserved_bytes=64 * MIB,
        prospective=dict(
            candidate_recordings=64,
            query_cases=40,
            initial_executions=80,
            technical_executions=8,
            maximum_executions=112,
            feature_windows_bound=1400,
            feature_bytes_bound=20 * MIB,
            audio_bytes_bound=110 * MIB,
            metadata_reserved=192 * MIB,
            protected_metadata=32 * MIB,
        ),
        pilot=record(root / "manifests/assessment/pilot.json")["record_hash"],
        policy=(
            "One pool; no resets/refunds/old-owner encodes; cold/reuse pilot before remaining index"
        ),
    )
    return owner.publish(budget, path, value, immutable=True)


def cases(owner):
    return owner.protocol["splits"][owner.split]["cases"]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "command",
        choices=[
            "preflight",
            "generate",
            "validate",
            "index",
            "queries",
            "run",
            "replay",
            "score",
            "report",
            "resume",
            "serve",
        ],
    )
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--split", choices=["development", "confirmation"], default="development")
    p.add_argument(
        "--ordinals", help="Comma-separated source or query ordinals; omitted uses declared split"
    )
    p.add_argument(
        "--tag", default="initial", help="Explicit technical cache pilot/replay identity"
    )
    p.add_argument("--job")
    p.add_argument("--skip-product", action="store_true")
    args = p.parse_args(argv)
    root = args.root.resolve()
    limits = {
        **load_limits(root / "config/resource_limits.json", "starter"),
        "max_download_bytes": 0,
        "max_model_candidates": 0,
    }
    owner = Context(root, split=args.split)
    if args.command == "preflight":
        answer = preflight(root, limits)
    elif args.command == "serve":
        from similar_sound_search.application.server import serve

        from .runtime import Runtime

        return serve(root, limits, owner.cfg["port"], Runtime(root, args.split))
    elif args.command == "resume":
        if not args.job:
            p.error("resume requires --job")
        answer = jobs.run(root, limits, args.job, args.split)
    else:
        if not (owner.directory / "preflight.json").exists():
            raise InputError("D02 explicit complete-path preflight required")
        ords = list(map(int, args.ordinals.split(","))) if args.ordinals else None
        kind = {"validate": "audit", "run": "batch"}.get(args.command, args.command)
        stage = (
            "prepare"
            if kind in {"generate", "audit"}
            else "report"
            if kind in {"score", "report"}
            else args.split
        )
        if kind == "generate":
            if ords is not None:
                raise InputError("D02 generation always follows the whole frozen split")
            units = ["source:" + str(i) for i in range(32)] + [
                "query:" + str(i) for i in range(len(cases(owner)))
            ]
        elif kind == "index":
            if args.split == "confirmation":
                record(root / "manifests/assessment/candidate.json")
            units = list(map(str, ords if ords is not None else range(32)))
        elif kind in {"queries", "batch", "replay"}:
            units = [
                c["case_id"]
                for c in cases(owner)
                if (ords is None or c["ordinal"] in ords)
                and not (
                    args.skip_product
                    and args.split == "development"
                    and c["ordinal"] in {0, 16, 20}
                )
            ]
            if args.split == "confirmation":
                record(root / "manifests/assessment/candidate.json")
        else:
            units = [kind]
        if not units or len(set(units)) != len(units):
            raise InputError("D02 explicit nonempty distinct unit list required")
        key = jobs.submit(root, limits, stage, args.split, kind, units, dict(tag=args.tag))
        print(json.dumps(dict(job_id=key, operation=kind, units=len(units))), flush=True)
        answer = jobs.run(root, limits, key, args.split)
    print(json.dumps(answer, allow_nan=False), flush=True)
    if isinstance(answer, dict) and answer.get("state") in {
        "failed",
        "blocked",
        "cancelled",
        "interrupted",
    }:
        return 1
    return 0
