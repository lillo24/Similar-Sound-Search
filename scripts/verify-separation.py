"""Independent native-to-player answers in one charged, deadline-bound B02 worker."""

import json
import os
import subprocess
import sys
from pathlib import Path


def verify(request):
    import numpy as np
    import soundfile as sf

    from similar_sound_search.evaluation.artifacts import record
    from similar_sound_search.matchers.job import offline_network
    from similar_sound_search.resources import CatalogueBudget
    from similar_sound_search.search.report import verify_bundle
    from similar_sound_search.separation.context import Context
    from similar_sound_search.storage import InputError, contained, project_lock, read_json, sha256

    root = Path(request["root"])
    with project_lock(root, ".b02-worker.lock"), offline_network():
        budget = CatalogueBudget(root, request["limits"])
        owner = Context(root)
        summary = read_json(contained(root / request["summary"], root / "reports/local"))
        directory = contained(root / summary["report"], owner.reports).parent
        value = record(directory / "bundle.json")
        owner.charge(
            budget, read_audio_seconds=sum(v["clip"]["duration_seconds"] for v in value["items"])
        )
        verify_bundle(root, directory, owner.reports)
        groups = {}
        for item in value["items"]:
            groups.setdefault(item["source_audio"]["local_path"], []).append(item)
        answers = []
        for relative, items in groups.items():
            path = contained(root / relative, root / "data")
            expected = items[0]["source_audio"]
            owner.charge(budget, read_audio_seconds=2 * expected["duration_seconds"])
            budget.input_file(path)
            if sha256(path, budget) != expected["sha256"]:
                raise InputError("B02 native QA: source bytes changed: " + relative)
            budget.reserve(
                65536, expected["sample_count"] * expected["channels"] * 16 + 32 * 1024**2
            )
            samples, rate = sf.read(path, dtype="float32", always_2d=True)
            if rate != expected["sample_rate_hz"] or samples.shape != (
                expected["sample_count"],
                expected["channels"],
            ):
                raise InputError("B02 native QA: source geometry differs: " + relative)
            for item in items:
                c = item["clip"]
                a, b = c["source_start_frame"], c["source_end_frame"]
                selected = samples[a:b].astype(np.float64)
                peak = float(np.max(np.abs(selected)))
                gain = min(1.0, (32767 / 32768) / peak) if peak else 1.0
                if gain != c["gain"] or b - a != c["frames"]:
                    raise InputError("B02 native QA: playback gain/support differs")
                integers = np.rint(selected * gain * 32768).astype(np.int16)
                owner.charge(budget, read_audio_seconds=c["duration_seconds"])
                media = contained(directory / c["path"], directory / "media")
                actual, media_rate = sf.read(media, dtype="int16", always_2d=True)
                if media_rate != rate or not np.array_equal(actual, integers):
                    raise InputError("B02 native QA: sample conversion differs: " + c["path"])
                receipt = record(directory / c["receipt"])
                if receipt["identity"]["source_sha256"] != expected["sha256"]:
                    raise InputError("B02 native QA: conversion source identity differs")
                zero = item["source_origin_seconds"] + a / rate
                if abs(zero - item["available_file_zero_seconds"]) > 1e-10:
                    raise InputError("B02 native QA: player zero/source timestamp differs")
                if item["signal_role"] == "Original candidate mixture" and not relative.startswith(
                    "data/audio/catalogue/originals/"
                ):
                    raise InputError("B02 native QA: candidate playback is not an original")
                answers.append(
                    {
                        "label": item["label"],
                        "media": c["path"],
                        "native_frames": [a, b],
                        "rate": rate,
                        "available_file_zero_seconds": zero,
                        "samples_equal": True,
                        "gain": gain,
                    }
                )
                budget.check_time("verify B02 media", c["path"])
        return {
            "status": "ok",
            "native_clips": len(answers),
            "unique_source_files": len(groups),
            "bundle_hash": value["record_hash"],
            "answers": answers,
            "method": "independent SoundFile int16 read and explicit rounding; "
            "no shared clip/pcm16 implementation",
        }


def main():
    if sys.argv[1:] == ["_worker"]:
        try:
            result = verify(json.load(sys.stdin))
        except Exception as exc:
            result = {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}
        print(json.dumps(result, allow_nan=False))
        return int(result["status"] != "ok")
    from similar_sound_search.resources import Budget, load_limits
    from similar_sound_search.separation.job import run
    from similar_sound_search.storage import atomic_json, project_lock

    root = Path(__file__).resolve().parents[1]
    limits = load_limits(root / "config/resource_limits.json", "starter")
    request = {
        "root": str(root),
        "limits": limits,
        "separation_action": "verify-native",
        "summary": sys.argv[1] if len(sys.argv) > 1 else "reports/local/b02-report.json",
    }

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
                "error": "B02 native QA exceeded worker deadline; retain charges",
            }
        result = json.loads(completed.stdout)
        if completed.returncode and result.get("status") != "failed":
            raise RuntimeError("B02 native QA worker failed without failure result")
        return result

    with project_lock(root):
        result = run(request, execute)
        path = root / "reports/local/b02-native-verification.json"
        Budget(root, limits).reserve(len(json.dumps(result).encode()) + 4096)
        atomic_json(path, result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"work", "ledger", "answers"}}, indent=2
        )
    )
    return int(result["status"] != "ok")


if __name__ == "__main__":
    raise SystemExit(main())
