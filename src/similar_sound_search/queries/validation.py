"""Independent pitch answers and native-source/player checks in charged B03 workers."""

import numpy as np
import soundfile as sf

from ..evaluation.artifacts import record
from ..search.pitch import estimate
from ..search.report import verify_bundle
from ..storage import InputError, contained, read_json, sha256
from . import library, pitch


def known_answers(budget, owner):
    rate = 24000
    t = np.arange(2 * rate) / rate
    answers = []
    for hz in (110, 220, 440):
        x = (0.15 * np.sin(2 * np.pi * hz * t))[:, None].astype(np.float32)
        owner.charge(budget, pitch_audio_seconds=len(x) / rate)
        actual = estimate(x, rate)
        cents = None if actual["hz"] is None else float(abs(1200 * np.log2(actual["hz"] / hz)))
        if cents is None or cents > 50:
            raise InputError(
                "B03 known answer: reliable single tone failed within 50 cents: " + str(hz)
            )
        answers.append({"truth_hz": hz, "estimate": actual, "absolute_cents": cents})
    diagnostics = {
        "silence": np.zeros_like(t),
        "outside_880": 0.1 * np.sin(2 * np.pi * 880 * t),
        "chord": 0.1 * (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 330 * t)),
        "noise": np.random.default_rng(303).normal(0, 0.1, len(t)),
    }
    abstentions = {}
    for name, signal in diagnostics.items():
        owner.charge(budget, pitch_audio_seconds=len(signal) / rate)
        value = estimate(signal[:, None].astype(np.float32), rate)
        if value["hz"] is not None:
            raise InputError("B03 known answer: expected abstention for " + name)
        abstentions[name] = value
    reliable = [
        {"hz": v, "reason": "known-answer input estimate", "reliable_blocks": 2}
        for v in (220.0, 440.0)
    ]
    amount = pitch.contribution(reliable, reliable[0], owner.cfg["pitch"])
    if amount["value"] != 0.015 or not amount["different_query_notes"]:
        raise InputError("B03 multiple-note mean/register known answer failed")
    missing = {"hz": None, "reason": "ambiguous fixture", "reliable_blocks": 0}
    if pitch.contribution([missing], reliable[0], owner.cfg["pitch"])["value"] != 0:
        raise InputError("B03 missing query pitch must contribute zero")
    value = {
        "status": "ok",
        "schema_version": "b03-known-answer-1",
        "eligible": answers,
        "eligible_coverage": "3/3",
        "abstentions": abstentions,
        "multiple_notes": amount,
        "default": library.OFF,
        "limits": "50..500Hz conservative channel-mean monophonic estimator; "
        "diagnostics do not establish polyphonic accuracy",
    }
    owner.publish(budget, owner.directory / "known-answer.json", value, immutable=True)
    return value


def native(budget, owner, summary_path=None):
    summary = read_json(
        contained(
            summary_path or owner.root / "reports/local/b03-report.json",
            owner.root / "reports/local",
        )
    )
    directory = contained(owner.root / summary["report"], owner.reports).parent
    bundle = record(directory / "bundle.json")
    owner.charge(
        budget, read_audio_seconds=sum(v["clip"]["duration_seconds"] for v in bundle["items"])
    )
    verify_bundle(owner.root, directory, owner.reports)
    sources = {}
    for item in bundle["items"]:
        sources.setdefault(item["source_audio"]["local_path"], []).append(item)
    answers = []
    for relative, items in sources.items():
        path = contained(owner.root / relative, owner.root)
        meta = items[0]["source_audio"]
        owner.charge(budget, read_audio_seconds=2 * meta["duration_seconds"])
        budget.input_file(path)
        if sha256(path, budget) != meta["sha256"]:
            raise InputError("B03 native QA: original bytes changed: " + relative)
        budget.reserve(65536, meta["sample_count"] * meta["channels"] * 16 + 32 * 1024**2)
        samples, rate = sf.read(path, dtype="float32", always_2d=True)
        if rate != meta["sample_rate_hz"] or samples.shape != (
            meta["sample_count"],
            meta["channels"],
        ):
            raise InputError("B03 native QA: source shape/rate mismatch")
        for item in items:
            c = item["clip"]
            a, b = c["source_start_frame"], c["source_end_frame"]
            selected = samples[a:b].astype(np.float64)
            peak = float(np.max(np.abs(selected)))
            gain = min(1.0, (32767 / 32768) / peak) if peak else 1.0
            integers = np.rint(selected * gain * 32768).astype(np.int16)
            owner.charge(budget, read_audio_seconds=c["duration_seconds"])
            actual, media_rate = sf.read(
                contained(directory / c["path"], directory / "media"), dtype="int16", always_2d=True
            )
            if (
                gain != c["gain"]
                or media_rate != rate
                or not np.array_equal(actual, integers)
                or b - a != c["frames"]
            ):
                raise InputError("B03 native QA: gain/PCM16/native support mismatch: " + c["path"])
            conversion = record(directory / c["receipt"])
            if conversion["identity"]["source_sha256"] != meta["sha256"]:
                raise InputError("B03 native QA: conversion source identity differs")
            evidence = item["origin_evidence"]
            origin = 0
            if evidence["kind"] != "file":
                mapping_record = record(
                    contained(owner.root / evidence["record"], owner.root / "data")
                )
                if mapping_record["record_hash"] != evidence["record_hash"]:
                    raise InputError("B03 native QA: mapping receipt changed")
                if evidence["kind"] == "a02":
                    expected_source = mapping_record["artifact"]
                    origin = mapping_record["timestamp_mapping"]["segments"][0][
                        "source_start_seconds"
                    ]
                elif evidence["kind"] == "b02":
                    component = evidence["component"]
                    identity = mapping_record["identity"]
                    dependency = identity["cue"] if component == "cue" else identity["source"]
                    origin = dependency["parent"]["timestamp_mapping"]["segments"][0][
                        "source_start_seconds"
                    ]
                    expected_source = dependency["audio"]
                    if component not in {"source", "cue"}:
                        expected_source = mapping_record["outputs"][component]["audio"]
                        origin += (
                            identity["spec"]["region"][0]
                            / identity["source"]["audio"]["sample_rate_hz"]
                        )
                else:
                    raise InputError("B03 native QA: unknown source mapping kind")
                if expected_source["sha256"] != meta["sha256"]:
                    raise InputError("B03 native QA: map does not describe played source")
            if abs(origin - item["source_origin_seconds"]) > 1e-10:
                raise InputError("B03 native QA: origin disagrees with original receipt")
            zero = origin + a / rate
            if abs(zero - item["available_file_zero_seconds"]) > 1e-10:
                raise InputError("B03 native QA: player/source timestamp differs")
            if item["signal_role"] == "Original candidate mixture" and not relative.startswith(
                "data/audio/catalogue/originals/"
            ):
                raise InputError("B03 native QA: candidate is not original catalogue audio")
            answers.append(
                {
                    "label": item["label"],
                    "media": c["path"],
                    "native_frames": [a, b],
                    "rate": rate,
                    "gain": gain,
                    "available_file_zero_seconds": zero,
                    "samples_equal": True,
                }
            )
    result = {
        "status": "ok",
        "native_items": len(answers),
        "unique_source_files": len(sources),
        "bundle_hash": bundle["record_hash"],
        "answers": answers,
        "method": "independent SoundFile int16 read and explicit rounding; "
        "no shared clip/pcm16 conversion",
    }
    owner.publish(budget, owner.directory / "native-verification.json", result, immutable=True)
    return result
