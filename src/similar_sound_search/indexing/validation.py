"""Independent native geometry, brute-force ranking oracle and bounded admission."""

import math

import numpy as np
from scipy.io.wavfile import read as read_wav
from scipy.signal import correlate, correlation_lags

from ..evaluation.artifacts import record
from ..search.contracts import grid
from ..search.ranking import distances, timbre_key
from ..storage import InputError, digest, read_json
from . import banks, build


def geometry(budget, owner, fixtures):
    """Read actual saved samples without using the operational row mapper/grid."""
    answers = []
    for source in fixtures["sources"]:
        actual = []
        for key in ("source", "target", "background", "isolated"):
            audio = source[key]["source"] if key == "source" else source[key]
            if audio is None:
                actual.append(None)
                continue
            path = owner.root / audio["local_path"]
            budget.input_file(path)
            owner.charge(budget, read_audio_seconds=audio["duration_seconds"])
            rate, samples = read_wav(path)
            if samples.ndim == 1:
                samples = samples[:, None]
            if (
                rate != 24000
                or samples.dtype != np.float32
                or samples.ndim != 2
                or samples.shape[1] != 1
            ):
                raise InputError("C01 independent truth: native WAV dimensions differ")
            actual.append(samples[:, 0].astype(np.float64))
        mixture, target, background, isolated = actual
        lo, hi = source["truth"]
        if len(isolated) != hi - lo or lo < 0 or hi > len(mixture):
            raise InputError("C01 independent truth: insertion support outside saved recording")
        expected = np.zeros(len(mixture))
        expected[lo:hi] = isolated
        if not np.array_equal(expected, target) or (
            background is not None
            and np.max(np.abs(mixture - background - target)) > 2 * np.finfo(np.float32).eps
        ):
            raise InputError(
                "C01 independent truth: target/background samples do not match insertion"
            )
        cross = correlate(target, isolated, mode="full", method="fft")
        lag = int(correlation_lags(len(target), len(isolated), mode="full")[int(np.argmax(cross))])
        if lag != lo:
            raise InputError("C01 independent FFT lag differs from declared native insertion")
        answers.append(
            {
                "recording_id": source["source"]["recording_id"],
                "declared_bounds": [lo, hi],
                "independent_fft_lag": lag,
                "saved_sample_reconstruction": True,
                "actual_frames": len(mixture),
                "rate": rate,
            }
        )
    value = {
        "schema_version": "c01-geometry-1",
        "fixtures_hash": fixtures["record_hash"],
        "passed": True,
        "sources": answers,
        "independence": "actual WAV samples + isolated waveform FFT correlation; "
        "no operational grid/row mapping",
    }
    path = owner.directory / "development/geometry.json"
    owner.publish(budget, path, value, immutable=True)
    return {"status": "ok", "geometry": path.relative_to(owner.root).as_posix(), "passed": True}


def oracle_bounds(frames, rate, duration_ms, hop_ms):
    size = math.ceil(duration_ms * rate / 1000)
    step = max(1, math.floor(hop_ms * rate / 1000 + 0.5))
    if frames <= size:
        return [(0, frames)]
    result, start = [], 0
    while start + size <= frames:
        result.append((start, start + size))
        start += step
    if result[-1][1] != frames:
        result.append((frames - size, frames))
    return result


def known_answer():
    checked_rows = 0
    for rate in (8000, 11025, 24000, 44100):
        for duration, hop in ((1200, 500), (2400, 250), (4800, 1000)):
            for frames in (1, rate // 3, rate * 8, rate * 8 + 1, math.ceil(duration * rate / 1000)):
                actual = grid(
                    frames, rate, {"window_milliseconds": duration, "hop_milliseconds": hop}
                )
                expected = oracle_bounds(frames, rate, duration, hop)
                if actual != expected or len(set(actual)) != len(actual) or actual[-1][1] != frames:
                    raise InputError(
                        "C01 known-answer: independent grid/tail/short-file oracle differs"
                    )
                checked_rows += len(actual)
    examples = np.asarray([[1.0, 0.0, 0.0], [1.0, 1.0, 0.0]])
    vectors = np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    per, scores = distances(examples, vectors, "cosine")
    expected = np.asarray(
        [
            [
                1
                - sum(float(x) * float(y) for x, y in zip(a, b, strict=True))
                / (
                    math.sqrt(sum(float(x) ** 2 for x in a))
                    * math.sqrt(sum(float(y) ** 2 for y in b))
                )
                for b in vectors
            ]
            for a in examples
        ]
    )
    if not np.allclose(per, expected, atol=1e-15, rtol=0):
        raise InputError("C01 known-answer: independent scalar cosine direction differs")
    hits = [
        {
            "recording_id": str(i),
            "group": str(i // 2),
            "start_frame": i * 3,
            "end_frame": i * 3 + 2,
            "timbre_distance": float(s),
        }
        for i, s in enumerate(scores)
    ]
    operational = {}
    for h in hits:
        if h["group"] not in operational or timbre_key(h) < timbre_key(operational[h["group"]]):
            operational[h["group"]] = h
    brute = [
        min(
            [h for h in hits if h["group"] == group],
            key=lambda h: (
                h["timbre_distance"],
                h["recording_id"],
                h["start_frame"],
                h["end_frame"],
            ),
        )
        for group in sorted({h["group"] for h in hits})
    ]
    if sorted(operational.values(), key=timbre_key) != sorted(
        brute,
        key=lambda h: (h["timbre_distance"], h["recording_id"], h["start_frame"], h["end_frame"]),
    ):
        raise InputError("C01 known-answer: complete group winners/ties differ")
    return {
        "status": "ok",
        "passed": True,
        "independent_grid_rows": checked_rows,
        "distance_direction": "lower-better",
        "complete_group_winners": len(brute),
    }


def admit(budget, owner, preflight):
    output = owner.directory / "admission.json"
    if output.exists():
        raise InputError("C01 admission already frozen; no result-dependent reselection")
    comparison = record(owner.directory / "development/comparison.json")
    work = record(owner.directory / "work.json")["counts"]
    ledger = read_json(owner.directory / "ledger.json")
    timing = record(owner.directory / "timing.json")
    baseline = comparison["summary"]["2400"]
    reserve = owner.protocol["admission"]["reserve"]
    candidates = []
    for label, path in preflight["plans"].items():
        plan = banks.validate_plan(owner, owner.root / path)
        state = build.progress(owner, plan)
        pilot = build.selected_units(owner, plan, "pilot")
        if any(u["unit_id"] not in state["committed"] for u in pilot):
            raise InputError("C01 admission: real pilot incomplete: " + label)
        reuse_key = digest(
            {
                "plan_hash": plan["record_hash"],
                "scope": "pilot",
                "units": [u["unit_id"] for u in pilot],
            }
        )
        reuse = record(owner.directory / "reuse" / (reuse_key + ".json"))
        if reuse["state"] != "complete":
            raise InputError("C01 admission: real pilot reuse measurement incomplete")
        elapsed = timing["worker_seconds_by_action"]["build:" + label + ":pilot"]
        seconds_per_unit = elapsed / len(pilot)
        remaining = [u for u in banks.units(plan) if u["unit_id"] not in state["committed"]]
        windows = sum(len(u["identity"]["bounds"]) for u in remaining)
        audio_seconds = sum(
            sum(b - a for a, b in u["identity"]["bounds"])
            / plan["signals"][u["signal_id"]]["audio"]["sample_rate_hz"]
            for u in remaining
        )
        reads = sum(plan["signals"][u["signal_id"]]["audio"]["duration_seconds"] for u in remaining)
        projected = {
            "worker_seconds": len(remaining) * seconds_per_unit * 1.5,
            "workers": len(remaining),
            "read_audio_seconds": reads,
            "feature_windows": windows,
            "feature_audio_seconds": audio_seconds,
            "feature_bytes": windows * 384 * 4 + len(remaining) * 65536,
        }
        counters = {"feature_audio_seconds": "processed_window_seconds"}
        caps = {
            "worker_seconds": 7200,
            "workers": 512,
            "read_audio_seconds": 180000,
            "feature_windows": 26000,
            "feature_audio_seconds": 65000,
            "feature_bytes": 128 * 1024**2,
        }
        used = {
            k: ledger["charged_worker_seconds"]
            if k == "worker_seconds"
            else work[counters.get(k, k)]
            for k in projected
        }
        fits = all(used[k] + projected[k] + reserve[k] <= caps[k] for k in projected)
        summary = comparison["summary"][
            str(plan["bank"]["identity"]["grid"]["window_milliseconds"])
        ]
        eligible = fits and summary["hit1"] >= baseline["hit1"] - 1
        candidates.append(
            {
                "label": label,
                "plan_hash": plan["record_hash"],
                "eligible": eligible,
                "fits_caps_with_delivery_reserve": fits,
                "projected_remaining": projected,
                "used_before_admission": used,
                "pilot_cold_seconds_per_unit": seconds_per_unit,
                "summary": summary,
                "reason": "eligible"
                if eligible
                else "projected cap or source-consistency guard refused",
            }
        )
    eligible = [v for v in candidates if v["eligible"]]
    chosen = (
        max(
            eligible,
            key=lambda c: (
                c["summary"]["full_event_support"][0] / c["summary"]["full_event_support"][1],
                c["summary"]["hit1"],
                c["summary"]["hit3"],
                -c["projected_remaining"]["worker_seconds"],
                -c["projected_remaining"]["feature_audio_seconds"],
                1 if c["label"] == "short" else 0,
            ),
        )
        if eligible
        else None
    )
    value = {
        "schema_version": "c01-admission-1",
        "protocol_hash": digest(owner.protocol),
        "comparison_hash": comparison["record_hash"],
        "candidates": candidates,
        "admitted_plan": chosen["plan_hash"] if chosen else None,
        "admitted_label": chosen["label"] if chosen else None,
        "state": "one-experimental-policy-admitted" if chosen else "partial-pilot-only",
        "default": "legacy-original",
        "production_attribution": "duration and hop combined; no human quality claim",
    }
    owner.publish(budget, output, value, immutable=True)
    return {"status": "ok", **value}
