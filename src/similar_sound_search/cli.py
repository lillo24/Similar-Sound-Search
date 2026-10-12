"""CLI boundary: one locked worker with a hard wall-time deadline and JSON failures."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .resources import Budget, CatalogueBudget, load_limits
from .storage import InputError, ResourceError, atomic_json, contained, project_lock, read_json


def parser():
    command = argparse.ArgumentParser(description="Bounded audio runtime and discovery catalogue")
    command.add_argument(
        "--root", type=Path, default=Path.cwd(), help="project root (default: current directory)"
    )
    command.add_argument(
        "--profile", type=Path, help="resource JSON (default: ROOT/config/resource_limits.json)"
    )
    command.add_argument("--tier", choices=("smoke", "starter"), default="smoke")
    command.add_argument(
        "--report", type=Path, help="owned JSON report under reports/local (atomically replaced)"
    )
    subcommands = command.add_subparsers(dest="command", required=True)
    subcommands.add_parser("smoke", help="offline deterministic WAV/FLAC plumbing diagnostic")
    inspect = subcommands.add_parser(
        "inspect", help="register explicit file or bounded data/audio directory"
    )
    inspect.add_argument("input", type=Path)
    inspect.add_argument("--context", type=Path, help="optional a02-input-1 evidence JSON")
    preparation = subcommands.add_parser(
        "prepare", help="immutable channel/crop/resample derivative"
    )
    preparation.add_argument("input", type=Path)
    preparation.add_argument(
        "--rate", type=int, required=True, help="explicit output sample rate in Hz"
    )
    preparation.add_argument(
        "--channels", required=True, help="preserve, mean, or channel:N (zero-based)"
    )
    preparation.add_argument(
        "--start", help="crop start in current input-file seconds (floor to sample)"
    )
    preparation.add_argument(
        "--end", help="crop end in current input-file seconds (ceil to sample)"
    )
    preparation.add_argument("--context", type=Path)
    preparation.add_argument(
        "--parent-record", type=Path, help="previous A02 bundle record for composed lineage"
    )
    catalogue = subcommands.add_parser("catalogue", help="bounded real-audio acquisition/import")
    catalogue.add_argument("catalogue_action", choices=("acquire", "import", "verify"))
    catalogue.add_argument("input", type=Path, nargs="?", help="explicit local import file only")
    catalogue.add_argument(
        "--context", type=Path, help="A02 context with permitted-use evidence for local import"
    )
    catalogue.add_argument("--job", default="starter", help="stable job name; repeat to resume")
    catalogue.add_argument("--take", type=int, help="process first N selected recordings (pilot)")
    catalogue.add_argument(
        "--reselect",
        action="store_true",
        help="explicitly revise coverage policy using the frozen search; keeps cumulative budget",
    )
    catalogue.add_argument(
        "--data-role",
        choices=("real_recording_discovery", "engineering"),
        default="real_recording_discovery",
        help="role of an explicit local import",
    )
    catalogue.add_argument(
        "--refresh", action="store_true", help="explicitly re-download/check pinned remote payloads"
    )
    catalogue.add_argument("--catalogue-policy", type=Path, help="explicit finite catalogue policy")
    return command


def _worker(request):
    """Broad catches belong here, at the process boundary, and always return failure."""
    try:
        root = Path(request["root"])
        budget_type = CatalogueBudget if request["command"] == "catalogue_step" else Budget
        budget = budget_type(root, request["limits"])
        context = read_json(request["context"]) if request.get("context") else None
        if request["command"] == "smoke":
            from .diagnostics import smoke

            result = smoke(budget)
        elif request["command"] == "inspect":
            from .inputs import inventory

            result = inventory(request["input"], budget, context)
        elif request["command"] == "prepare":
            from .preparation import prepare

            parent = read_json(request["parent_record"]) if request.get("parent_record") else None
            result = prepare(
                request["input"],
                budget,
                request["rate"],
                request["channels"],
                request["start"],
                request["end"],
                context,
                parent,
            )
        elif request["command"] == "catalogue_step":
            from .catalogue.job import worker

            result = worker(request, budget)
        else:
            raise InputError(f"unknown worker operation {request['command']!r}")
        budget.check_time("complete", request["command"])
    except Exception as exc:
        result = {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": f"{request['command']} {request.get('input', '')}: {exc}",
        }
    print(json.dumps(result, allow_nan=False))
    return 0 if result["status"] == "ok" else 1


def execute(request):
    """No NumPy/SciPy import before the bounded child; timeout includes library startup."""
    environment = os.environ.copy()
    environment.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "similar_sound_search", "_worker"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=request["limits"]["max_seconds"],
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "error_type": "ResourceError",
            "error": (
                f"{request['command']}: worker exceeded "
                f"max_seconds={request['limits']['max_seconds']} and was terminated"
            ),
            "resume": (
                "rerun the same command after inspecting limits; completed bundles are retained, "
                ".a02-partial-* directories are incomplete"
            ),
        }
    try:
        result = json.loads(completed.stdout)
    except ValueError as exc:
        raise InputError(
            f"worker {request['command']}: invalid JSON; exit={completed.returncode}; "
            f"stderr={completed.stderr[-2000:]}"
        ) from exc
    if completed.returncode != 0 and result.get("status") != "failed":
        raise InputError(f"worker exited {completed.returncode} without an explicit failure result")
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["_worker"]:
        return _worker(json.load(sys.stdin))
    args = parser().parse_args(argv)
    started = time.monotonic()
    report = None
    try:
        root = args.root.resolve()
        if not (root / "config/resource_limits.json").is_file():
            raise InputError(
                f"root {root}: expected project config/resource_limits.json; use --root"
            )
        report_candidate = args.report or root / "reports/local" / (args.command + ".json")
        if not report_candidate.is_absolute():
            report_candidate = root / report_candidate
        report_candidate = contained(report_candidate, contained(root / "reports/local", root))
        if report_candidate.suffix.lower() != ".json":
            raise InputError("report: expected owned .json path under reports/local")
        report = report_candidate
        profile = args.profile or root / "config/resource_limits.json"
        limits = load_limits(profile, args.tier)
        request = {
            key: str(value.absolute()) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        }
        request.update({"root": str(root), "limits": limits})
        with project_lock(root):
            # Refuse an orphaned A03 child before touching its ledger or starting any operation.
            with project_lock(root, ".a03-worker.lock"):
                pass
            Budget(root, limits).reserve(65536)
            if args.command == "catalogue":
                from .catalogue.job import run

                if args.catalogue_action == "import" and (
                    args.input is None or args.context is None
                ):
                    raise InputError("catalogue import: explicit input file and --context required")
                if args.catalogue_action != "import" and (
                    args.input is not None or args.context is not None
                ):
                    raise InputError("catalogue: input/--context belong to explicit local import")
                result = run(request, execute)
            else:
                result = execute(request)
            result.update(
                {
                    "command": args.command,
                    "tier": args.tier,
                    "wall_seconds": time.monotonic() - started,
                    "report_written": True,
                }
            )
            # Reports are bounded independently of decoded audio; a large inventory fails visibly.
            size = len(json.dumps(result, allow_nan=False).encode("utf-8")) + 4096
            Budget(root, limits).reserve(size)
            atomic_json(report, result)
    except (InputError, OSError, ValueError) as exc:
        result = {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "report_written": False,
        }
        # Never write outside the checked report boundary or mask a disk/concurrency refusal.
        if report is not None and not isinstance(exc, ResourceError):
            try:
                result["report_written"] = True
                atomic_json(report, result)
            except OSError:
                result["report_written"] = False
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["status"] == "ok" else 1
