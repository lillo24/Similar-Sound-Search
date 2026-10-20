"""Independent, pre-inference B03 geometry audit in the fixed charged worker owner."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def verify(request):
    import numpy as np
    import soundfile as sf

    from similar_sound_search.evaluation.artifacts import record
    from similar_sound_search.matchers.job import offline_network
    from similar_sound_search.matchers.runner import memory_check
    from similar_sound_search.queries.context import Context
    from similar_sound_search.resources import CatalogueBudget
    from similar_sound_search.storage import InputError, contained, project_lock, sha256

    root = Path(request["root"])
    started = time.monotonic()
    with project_lock(root, ".b03-worker.lock"), offline_network():
        budget = CatalogueBudget(root, request["limits"])
        owner = Context(root)
        plan = record(owner.directory / "development.json")
        counts = record(owner.directory / "work.json")["counts"]
        if counts["feature_windows"] or counts["comparisons"]:
            raise InputError("B03 geometry audit must precede matcher/comparison inference")
        references = [*plan["candidates"], *plan["signals"]]
        unique = {v["path"]: v for v in references}
        answers = []
        harmonics = ((1, 0.12, 0, 0), (1, 0.38, 0.10, 0), (1, 0, 0.12, 0), (1, 0.25, 0.15, 0.08))
        for relative, item in sorted(unique.items()):
            path = contained(root / relative, root / "data/audio/queries/development")
            expected = item["audio"]
            owner.charge(budget, read_audio_seconds=2 * expected["duration_seconds"])
            budget.input_file(path)
            budget.reserve(
                65536, expected["sample_count"] * expected["channels"] * 32 + 32 * 1024**2
            )
            if (
                sha256(path, budget) != item["sha256"]
                or path.stat().st_size != expected["file_bytes"]
            ):
                raise InputError("B03 geometry source hash/bytes changed: " + relative)
            x, rate = sf.read(path, dtype="float32", always_2d=True)
            a, b = item["event"]
            left, right = item["context"]
            if (
                rate != expected["sample_rate_hz"]
                or x.shape != (expected["sample_count"], expected["channels"])
                or not np.isfinite(x).all()
            ):
                raise InputError("B03 geometry native dimensions/nonfinite samples: " + relative)
            if not 0 < left <= a < b <= right <= len(x) or b - a != 57600 or rate != 24000:
                raise InputError("B03 geometry actual nonzero native support differs: " + relative)
            if np.any(x[:a]) or np.any(x[b:]):
                raise InputError("B03 geometry: actual source extends beyond declared insertion")
            selected = x[a:b, 0].astype(np.float64)
            present = bool(np.any(selected))
            if present != item["geometry"]["full_generated_attack_release"]:
                raise InputError("B03 geometry presence/full-support flag is incorrect")
            peak_hz = None
            if present:
                owner.charge(budget, pitch_audio_seconds=len(selected) / rate)
                peak_hz = float(np.argmax(np.abs(np.fft.rfft(selected))) * rate / len(selected))
            family = item.get("family")
            if family is not None:
                hz = item["frequency_truth_hz"]
                if peak_hz is None or abs(peak_hz - hz) > 1:
                    raise InputError("B03 geometry: candidate frequency truth differs")
                t = np.arange(len(selected), dtype=np.float64) / rate
                amplitudes = np.array(
                    [
                        abs(np.mean(selected * np.exp(-2j * np.pi * hz * n * t)))
                        for n in (1, 2, 3, 4)
                    ]
                )
                ratios = amplitudes / amplitudes[0]
                if np.max(np.abs(ratios - harmonics[family])) > 0.035:
                    raise InputError("B03 geometry: candidate harmonic-family truth differs")
            answers.append(
                {
                    "path": relative,
                    "event": [a, b],
                    "context": [left, right],
                    "frames": len(x),
                    "rate": rate,
                    "source_present": present,
                    "outside_insertion_exact_zero": True,
                    "peak_frequency_hz": peak_hz,
                }
            )
        by_asset = {v["asset_id"]: v for v in plan["signals"]}
        if len(plan["candidates"]) != 16 or len({v["group"] for v in plan["candidates"]}) != 16:
            raise InputError("B03 geometry: complete sixteen-group candidate support required")
        for case in plan["cases"]:
            for example in case["input"]["examples"]:
                source = by_asset[example["asset_id"]]
                if example["event"] != source["event"] or example["context"] != source["context"]:
                    raise InputError("B03 geometry: query/source selection support differs")
                if (
                    case["stratum"] == "primary"
                    and not source["geometry"]["full_generated_attack_release"]
                ):
                    raise InputError("B03 geometry: primary reference unexpectedly absent")
                if case["stratum"] == "absent_diagnostic" and example["selection"]["complete"]:
                    raise InputError("B03 geometry: absent control cannot claim a complete event")
        result = {
            "status": "ok",
            "schema_version": "b03-independent-geometry-1",
            "plan_hash": plan["record_hash"],
            "script_sha256": sha256(Path(__file__), budget),
            "signals": answers,
            "cases": len(plan["cases"]),
            "primary_full_support": 6,
            "candidate_groups": 16,
            "wall_seconds": time.monotonic() - started,
            "peak_working_bytes": memory_check(budget),
            "method": "independent SoundFile read/hash and record-derived insertion/zero-support "
            "checks; FFT/projection generator-truth audit; "
            "no operational pitch estimator or matcher",
        }
        path = owner.directory / ("independent-geometry-" + result["script_sha256"] + ".json")
        result["audit"] = path.relative_to(root).as_posix()
        owner.publish(budget, path, result, immutable=True)
        return result


def main():
    if sys.argv[1:] == ["_worker"]:
        try:
            result = verify(json.load(sys.stdin))
        except Exception as exc:
            result = {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}
        print(json.dumps(result, allow_nan=False))
        return int(result["status"] != "ok")
    from similar_sound_search.queries.job import run
    from similar_sound_search.resources import Budget, load_limits
    from similar_sound_search.storage import atomic_json, project_lock

    root = Path(__file__).resolve().parents[1]
    limits = load_limits(root / "config/resource_limits.json", "starter")
    request = {"root": str(root), "limits": limits, "queries_action": "geometry-audit"}

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
                "error": "B03 independent geometry exceeded deadline; retain charges",
            }
        result = json.loads(completed.stdout)
        if completed.returncode and result.get("status") != "failed":
            raise RuntimeError("geometry worker exited without explicit failure")
        return result

    with project_lock(root):
        result = run(request, execute)
        Budget(root, limits).reserve(65536)
        atomic_json(root / "reports/local/b03-geometry-command.json", result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"signals", "ledger", "work"}}, indent=2
        )
    )
    return int(result["status"] != "ok")


if __name__ == "__main__":
    raise SystemExit(main())
