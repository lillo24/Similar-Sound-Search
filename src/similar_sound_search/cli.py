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
    evaluation = subcommands.add_parser(
        "evaluation", help="A04 benchmark/fixture/scoring operations"
    )
    evaluation.add_argument(
        "evaluation_action",
        choices=("acquire", "generate", "validate", "maps", "known-answer", "score"),
    )
    evaluation.add_argument("input", type=Path, nargs="?", help="prediction JSON for score only")
    evaluation.add_argument(
        "--split", choices=("development", "held_out", "all"), default="development"
    )
    evaluation.add_argument("--pilot", action="store_true", help="generate first two presets only")
    evaluation.add_argument(
        "--final-choice", type=Path, help="A06 frozen development model/config choice"
    )
    matchers = subcommands.add_parser("matchers", help="A05 bounded development comparison")
    matchers.add_argument(
        "matcher_action",
        choices=(
            "freeze",
            "validate",
            "acquire",
            "smoke",
            "run",
            "compare",
            "known-answer",
            "score",
        ),
    )
    matchers.add_argument("input", type=Path, nargs="?")
    matchers.add_argument("--method", choices=("acoustic", "efficientat"))
    matchers.add_argument("--split", choices=("development", "held_out"), default="development")
    search = subcommands.add_parser("search", help="A06 bounded exact search and original playback")
    search.add_argument(
        "search_action",
        choices=(
            "pilot",
            "demo-inputs",
            "diagnostic-inputs",
            "index",
            "prepare-query",
            "rank",
            "report",
            "declare",
            "final-run",
            "final-score",
            "known-answer",
            "serve",
        ),
    )
    search.add_argument("input", type=Path, nargs="?")
    search.add_argument("--method", choices=("efficientat", "acoustic"))
    search.add_argument("--engineering", type=Path, help="explicit generated diagnostic index JSON")
    search.add_argument("--index", type=Path)
    search.add_argument("--query", type=Path)
    search.add_argument(
        "--include-self", action="store_true", help="explicit self-match diagnostic"
    )
    search.add_argument("--allow-partial", action="store_true")
    search.add_argument("--pitch-weight", type=float, default=0)
    search.add_argument("--port", type=int, default=8766)
    events = subcommands.add_parser(
        "events", help="B01 bounded event selection and read-only catalogue search"
    )
    events.add_argument(
        "events_action",
        choices=(
            "inputs",
            "compatibility",
            "propose",
            "select",
            "extract",
            "prepare-query",
            "rank",
            "report",
            "event-report",
            "compare",
            "audit-boundaries",
            "known-answer",
            "serve",
        ),
    )
    events.add_argument("input", type=Path, nargs="?")
    events.add_argument("--index", type=Path)
    events.add_argument("--query", type=Path)
    events.add_argument("--receipt", type=Path)
    events.add_argument("--auto", action="store_true")
    events.add_argument("--ids", nargs="+")
    events.add_argument(
        "--intervals", nargs="+", help="explicit START:END native half-open frame pairs"
    )
    events.add_argument("--port", type=int, default=8767)
    separation = subcommands.add_parser(
        "separation", help="B02 optional DSP processing and comparison"
    )
    separation.add_argument(
        "separation_action",
        choices=(
            "pilot",
            "preflight",
            "process",
            "handoff",
            "prepare-query",
            "compatibility",
            "rank",
            "compare",
            "report",
            "known-answer",
            "serve",
        ),
    )
    separation.add_argument("input", type=Path, nargs="?")
    separation.add_argument("--mode", choices=("original", "broad", "guided"), default="original")
    separation.add_argument(
        "--component", choices=("original", "harmonic", "percussive", "extracted", "residual")
    )
    separation.add_argument("--index", type=Path)
    separation.add_argument("--query", type=Path)
    separation.add_argument("--receipt", type=Path)
    separation.add_argument("--port", type=int, default=8768)
    queries = subcommands.add_parser(
        "queries", help="B03 saved revisions and secondary pitch preference"
    )
    queries.add_argument(
        "queries_action",
        choices=(
            "register",
            "save",
            "revise",
            "list",
            "show",
            "rename",
            "select",
            "validate",
            "materialize",
            "load",
            "export",
            "import",
            "process",
            "compatibility",
            "search",
            "preflight",
            "compare",
            "known-answer",
            "report",
            "verify-native",
            "serve",
        ),
    )
    queries.add_argument("input", type=Path, nargs="?")
    queries.add_argument("--query-id")
    queries.add_argument("--revision")
    queries.add_argument("--expected")
    queries.add_argument("--name")
    queries.add_argument("--sha256")
    queries.add_argument("--context", type=Path)
    queries.add_argument("--parent-record", type=Path)
    queries.add_argument("--bindings", type=Path)
    queries.add_argument("--index", type=Path)
    queries.add_argument("--receipt", type=Path)
    queries.add_argument("--mode", choices=("original", "broad", "guided"), default="original")
    queries.add_argument("--port", type=int, default=8769)
    indexing = subcommands.add_parser("indexing", help="C01 versioned passage/component banks")
    indexing.add_argument(
        "indexing_action",
        choices=(
            "preflight",
            "generate",
            "geometry",
            "known-answer",
            "build",
            "verify",
            "compare",
            "admit",
            "components",
            "compatibility",
            "snapshot",
            "derive-query",
            "search",
            "report",
            "verify-native",
            "serve",
        ),
    )
    indexing.add_argument("input", type=Path, nargs="?")
    indexing.add_argument("--bank", choices=("short", "long"))
    indexing.add_argument("--scope", choices=("pilot", "full"), default="full")
    indexing.add_argument("--receipt", type=Path)
    indexing.add_argument("--revision")
    indexing.add_argument("--materialization")
    indexing.add_argument("--derived", action="store_true")
    indexing.add_argument("--allow-partial", action="store_true")
    indexing.add_argument("--port", type=int, default=8770)
    retrieval = subcommands.add_parser(
        "retrieval", help="C02 candidate retrieval and C03 shortlist"
    )
    retrieval.add_argument(
        "retrieval_action",
        choices=(
            "preflight",
            "known-answer",
            "generate",
            "geometry",
            "build-development",
            "compare",
            "diagnostics",
            "compatibility",
            "derive-query",
            "search",
            "verify",
            "report",
            "verify-native",
            "serve",
        ),
    )
    retrieval.add_argument("input", type=Path, nargs="?")
    retrieval.add_argument("--receipt", type=Path)
    retrieval.add_argument("--revision")
    retrieval.add_argument("--materialization")
    retrieval.add_argument("--derived", action="store_true")
    retrieval.add_argument("--port", type=int, default=8771)
    refinement = subcommands.add_parser("refinement", help="C03 bounded original timing refinement")
    refinement.add_argument(
        "refinement_action",
        choices=(
            "preflight",
            "known-answer",
            "geometry",
            "compare",
            "compatibility",
            "derive-query",
            "refine",
            "verify",
            "report",
            "verify-native",
            "repair-report",
            "verify-repaired-native",
            "serve",
        ),
    )
    refinement.add_argument("input", type=Path, nargs="?")
    refinement.add_argument("--execution", type=Path)
    refinement.add_argument("--arm", choices=("event-multi",))
    refinement.add_argument("--receipt", type=Path)
    refinement.add_argument(
        "--pilot", action="store_true", help="one bounded worker; retain progress"
    )
    refinement.add_argument("--port", type=int, default=8772)
    return command


def _worker(request):
    """Broad catches belong here, at the process boundary, and always return failure."""
    try:
        root = Path(request["root"])
        budget_type = (
            CatalogueBudget
            if request["command"]
            in {
                "catalogue_step",
                "evaluation_step",
                "matchers_step",
                "search_step",
                "events_step",
                "separation_step",
                "queries_step",
                "indexing_step",
                "retrieval_step",
                "refinement_step",
            }
            else Budget
        )
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
        elif request["command"] == "evaluation_step":
            from .evaluation.job import worker

            result = worker(request, budget)
        elif request["command"] == "matchers_step":
            from .matchers.job import worker

            result = worker(request, budget)
        elif request["command"] == "search_step":
            from .search.job import worker

            result = worker(request, budget)
        elif request["command"] == "events_step":
            from .events.job import worker

            result = worker(request, budget)
        elif request["command"] == "separation_step":
            from .separation.job import worker

            result = worker(request, budget)
        elif request["command"] == "queries_step":
            from .queries.job import worker

            result = worker(request, budget)
        elif request["command"] == "indexing_step":
            from .indexing.job import worker

            result = worker(request, budget)
        elif request["command"] == "refinement_step":
            from .refinement.job import worker

            result = worker(request, budget)
        elif request["command"] == "retrieval_step":
            from .retrieval.job import worker

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
        if args.command == "refinement" and args.report is None:
            args.report = root / "reports/local/c03/last-command.json"
        if args.command == "retrieval" and args.report is None:
            args.report = root / "reports/local/c02/last-command.json"
        default_report = (
            root / "reports/local/c01/last-command.json"
            if args.command == "indexing"
            else root / "reports/local" / (args.command + ".json")
        )
        report_candidate = args.report or default_report
        if not report_candidate.is_absolute():
            report_candidate = root / report_candidate
        report_candidate = contained(report_candidate, contained(root / "reports/local", root))
        if args.command == "indexing":
            report_candidate = contained(report_candidate, root / "reports/local/c01")
        if args.command == "retrieval":
            report_candidate = contained(report_candidate, root / "reports/local/c02")
        if args.command == "refinement":
            report_candidate = contained(report_candidate, root / "reports/local/c03")
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
        if args.command == "search" and args.search_action == "serve":
            from .search.report import serve

            if not args.input:
                raise InputError("search serve requires the owned report HTML or bundle directory")
            serve(root, args.input, args.port)
            return 0
        if args.command == "events" and args.events_action == "serve":
            from .search.report import serve

            if not args.input:
                raise InputError("events serve requires the owned B01 report bundle")
            serve(root, args.input, args.port, root / "reports/local/b01")
            return 0
        if args.command == "separation" and args.separation_action == "serve":
            from .search.report import serve

            if not args.input:
                raise InputError("separation serve requires the owned B02 report bundle")
            serve(root, args.input, args.port, root / "reports/local/b02")
            return 0
        if args.command == "queries" and args.queries_action == "serve":
            from .search.report import serve

            if not args.input:
                raise InputError("queries serve requires the owned B03 report bundle")
            serve(root, args.input, args.port, root / "reports/local/b03")
            return 0
        if args.command == "indexing" and args.indexing_action == "serve":
            from .search.report import serve

            if not args.input:
                raise InputError("indexing serve requires the owned C01 report bundle")
            serve(root, args.input, args.port, root / "reports/local/c01")
            return 0
        if args.command == "retrieval" and args.retrieval_action == "serve":
            from .search.report import serve

            if not args.input:
                raise InputError("retrieval serve requires the owned C02 bundle")
            serve(root, args.input, args.port, root / "reports/local/c02")
            return 0
        if args.command == "refinement" and args.refinement_action == "serve":
            from .search.report import serve

            if not args.input:
                raise InputError("refinement serve requires the owned C03 bundle")
            serve(root, args.input, args.port, root / "reports/local/c03")
            return 0
        with project_lock(root):
            # Refuse orphaned acquisition/evaluation children before starting an operation.
            with project_lock(root, ".a03-worker.lock"):
                pass
            with project_lock(root, ".a04-worker.lock"):
                pass
            with project_lock(root, ".a05-worker.lock"):
                pass
            with project_lock(root, ".a06-worker.lock"):
                pass
            with project_lock(root, ".b01-worker.lock"):
                pass
            with project_lock(root, ".b02-worker.lock"):
                pass
            with project_lock(root, ".b03-worker.lock"):
                pass
            with project_lock(root, ".c01-worker.lock"):
                pass
            with project_lock(root, ".c02-worker.lock"):
                pass
            with project_lock(root, ".c03-worker.lock"):
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
            elif args.command == "evaluation":
                from .evaluation.job import run

                if args.input is not None and args.evaluation_action != "score":
                    raise InputError("evaluation: input belongs to score only")
                if args.pilot and args.evaluation_action != "generate":
                    raise InputError("evaluation: --pilot belongs to generate only")
                result = run(request, execute)
            elif args.command == "matchers":
                from .matchers.job import run

                if args.input is not None and args.matcher_action != "score":
                    raise InputError("matchers: input belongs to score only")
                result = run(request, execute)
            elif args.command == "search":
                from .search.job import run

                result = run(request, execute)
            elif args.command == "events":
                from .events.job import run

                result = run(request, execute)
            elif args.command == "separation":
                from .separation.job import run

                result = run(request, execute)
            elif args.command == "queries":
                from .queries.job import run

                result = run(request, execute)
            elif args.command == "indexing":
                from .indexing.job import run

                result = run(request, execute)
            elif args.command == "refinement":
                from .refinement.job import run

                result = run(request, execute)
            elif args.command == "retrieval":
                from .retrieval.job import run

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
