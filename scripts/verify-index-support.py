"""Geometry-only verification of C01's predeclared full-2.4s support denominator."""

import json
import os
import subprocess
import sys
from pathlib import Path


def support_table(fixtures, protocol):
    """Independent integer enumeration; never reads features, scores or waveforms."""
    tables = {}
    for milliseconds, hop_ms in protocol["development"]["grids_milliseconds"]:
        opportunities = []
        for case in fixtures["queries"]:
            if case["stratum"] != "alternate" or case["support"] != "full":
                continue
            for item in fixtures["sources"]:
                a = item["source"]["source"]
                lo, hi = item["truth"]
                if (
                    item["family"] != case["family"]
                    or (hi - lo) * 1000 != 2400 * a["sample_rate_hz"]
                ):
                    continue
                size = (milliseconds * a["sample_rate_hz"] + 999) // 1000
                step = max(1, (hop_ms * a["sample_rate_hz"] + 500) // 1000)
                frames = a["sample_count"]
                windows = []
                if frames <= size:
                    windows.append([0, frames])
                else:
                    start = 0
                    while start <= frames - size:
                        windows.append([start, start + size])
                        start += step
                    if windows[-1][1] != frames:
                        windows.append([frames - size, frames])
                opportunities.append(
                    {
                        "case_id": case["id"],
                        "recording_id": item["source"]["recording_id"],
                        "truth": [lo, hi],
                        "contains": any(x <= lo and hi <= y for x, y in windows),
                    }
                )
        tables[str(milliseconds)] = {
            "full_2400ms_support": [sum(v["contains"] for v in opportunities), len(opportunities)],
            "opportunities": opportunities,
        }
    return tables


def verify(request):
    from similar_sound_search.evaluation.artifacts import record
    from similar_sound_search.indexing.context import Context
    from similar_sound_search.matchers.job import offline_network
    from similar_sound_search.matchers.runner import memory_check
    from similar_sound_search.resources import CatalogueBudget
    from similar_sound_search.storage import InputError, project_lock, sha256

    root = Path(request["root"])
    with project_lock(root, ".c01-worker.lock"), offline_network():
        budget, owner = CatalogueBudget(root, request["limits"]), Context(root)
        fixtures = record(owner.directory / "development/fixtures.json")
        geometry = record(owner.directory / "development/geometry.json")
        comparison = record(owner.directory / "development/comparison.json")
        decision = record(owner.directory / "admission.json")
        if (
            not geometry["passed"]
            or geometry["fixtures_hash"] != fixtures["record_hash"]
            or comparison["fixtures_hash"] != fixtures["record_hash"]
        ):
            raise InputError(
                "C01 support verification: inspected fixture/closed-batch identity differs"
            )
        tables = support_table(fixtures, owner.protocol)
        eligible = [v for v in decision["candidates"] if v["eligible"]]
        durations = {"short": "1200", "long": "4800"}

        def order(candidate):
            n, total = tables[durations[candidate["label"]]]["full_2400ms_support"]
            return (
                n / total,
                candidate["summary"]["hit1"],
                candidate["summary"]["hit3"],
                -candidate["projected_remaining"]["worker_seconds"],
                -candidate["projected_remaining"]["feature_audio_seconds"],
                1 if candidate["label"] == "short" else 0,
            )

        chosen = max(eligible, key=order)["label"] if eligible else None
        if chosen != decision["admitted_label"]:
            raise InputError(
                "C01 support verification changed admission; stop expansion for an explicit decision"
            )
        value = {
            "schema_version": "c01-support-verification-1",
            "status": "ok",
            "passed": True,
            "geometry_hash": geometry["record_hash"],
            "comparison_hash": comparison["record_hash"],
            "decision_hash": decision["record_hash"],
            "script_sha256": sha256(Path(__file__), budget),
            "raw_support_counts": {
                k: v["full_event_support"] for k, v in comparison["summary"].items()
            },
            "strict_full_2400ms": tables,
            "admission_unchanged": True,
            "admitted_label": chosen,
            "retained_cases": [v["case_id"] for v in comparison["cases"]],
            "interpretation": "Raw tally included the .3s short-file source in full-query cases. "
            "Strict full-2.4s geometry excludes it only from this denominator; every case, "
            "ranking, failure, localization result and cost remains in the closed batch. "
            "No features, scores, queries, thresholds, source choices or admission changed.",
            "peak_working_bytes": memory_check(budget),
        }
        owner.publish(budget, owner.directory / "support-verification.json", value, immutable=True)
        budget.check_time("C01 support verification", str(root))
        return value


def main():
    if sys.argv[1:] == ["_worker"]:
        try:
            result = verify(json.load(sys.stdin))
        except Exception as exc:
            result = {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}
        print(json.dumps(result, allow_nan=False))
        return int(result["status"] != "ok")
    from similar_sound_search.indexing.job import run
    from similar_sound_search.resources import Budget, load_limits
    from similar_sound_search.storage import atomic_json, project_lock

    root = Path(__file__).resolve().parents[1]
    limits = load_limits(root / "config/resource_limits.json", "starter")
    request = {"root": str(root), "limits": limits, "indexing_action": "support-verification"}

    def execute(value):
        environment = {
            **os.environ,
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        try:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "_worker"],
                input=json.dumps(value),
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                timeout=value["limits"]["max_seconds"],
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "error": "C01 support verification exceeded deadline; retain charges",
            }
        result = json.loads(completed.stdout)
        if completed.returncode and result.get("status") != "failed":
            raise RuntimeError("geometry worker exited without explicit failure")
        return result

    with project_lock(root):
        result = run(request, execute)
        Budget(root, limits).reserve(65536)
        atomic_json(root / "reports/local/c01/support-command.json", result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"signals", "ledger", "work"}}, indent=2
        )
    )
    return int(result["status"] != "ok")


if __name__ == "__main__":
    raise SystemExit(main())
