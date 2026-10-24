"""Independent algebraic/native truth audit, before retrieval is admitted."""

import math

import numpy as np
from scipy.signal import correlate, resample_poly

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.inputs import decode
from similar_sound_search.storage import InputError, digest

from .dataset import RATE, background, performance


def check_audio(budget, owner, path, families, spec, query=False, kind=None):
    """Rebuild insertion/level algebra independently of the operational mix function."""
    target = performance(
        families[spec["family"]],
        spec,
        "absent-target" if kind == "absent-target" else spec.get("character", "positive"),
    )
    bg = background(spec["background_seed"])
    positions = [9600] if query else [round(v * RATE) for v in spec["positions"]]
    stem, mask = np.zeros(len(bg)), np.zeros(len(bg), dtype=bool)
    for a in positions:
        stem[a : a + len(target)] += target
        mask[a : a + len(target)] = True
    br = np.linalg.norm(bg[mask]) / np.sqrt(mask.sum())
    tr = np.linalg.norm(stem[mask]) / np.sqrt(mask.sum())
    gain = br / tr * 10 ** (spec["ratio_db"] / 20)
    unscaled = bg + gain * stem
    common = min(1.0, 0.9 / np.abs(unscaled).max())
    frames = round(spec["duration_seconds"] * RATE)
    expected = (unscaled * common)[:frames, None]
    if spec.get("channels", 1) == 2:
        right = 0.7 * expected[:, 0] + 0.01 * np.random.default_rng(
            spec["background_seed"] + 1
        ).standard_normal(frames)
        expected = np.column_stack([expected[:, 0], right])
    rate = spec.get("rate", RATE)
    if rate != RATE:
        d = math.gcd(rate, RATE)
        expected = resample_poly(expected, rate // d, RATE // d, axis=0)
    owner.charge(budget, read_audio_seconds=spec["duration_seconds"])
    actual, meta = decode(path, budget)
    if (
        actual.shape != expected.shape
        or meta["sample_rate_hz"] != rate
        or not np.allclose(actual, expected.astype(np.float32), rtol=0, atol=2e-7)
        or np.max(np.abs(actual)) >= 1
        or np.sqrt(np.mean(actual.astype(float) ** 2)) < 1e-5
    ):
        raise InputError(
            "D02 independent generated samples/rate/channel/clipping/silence audit failed: "
            + path.name
        )
    achieved = 20 * np.log10(np.linalg.norm(gain * stem[mask]) / np.linalg.norm(bg[mask]))
    if abs(achieved - spec["ratio_db"]) > 1e-10:
        raise InputError("D02 achieved target/background ratio differs")
    # Remove the independently reconstructed accompaniment before lag testing.
    left_bg = (bg * common)[:frames]
    probe = target * gain * common
    if rate != RATE:
        left_bg = resample_poly(left_bg, rate // d, RATE // d)
        probe = resample_poly(probe, rate // d, RATE // d)
    residual = actual[:, 0].astype(float) - left_bg
    correlations = correlate(residual, probe, mode="valid", method="fft")
    expected_lags = [round(a * rate / RATE) for a in positions]
    found = []
    for lag in expected_lags:
        first, last = max(0, lag - 2), min(len(correlations), lag + 3)
        if first >= last:
            raise InputError("D02 source lag outside actual decoded support")
        actual_lag = first + int(np.argmax(correlations[first:last]))
        if abs(actual_lag - lag) > 2 or correlations[actual_lag] <= 0:
            raise InputError("D02 independent insertion lag differs")
        found.append(actual_lag)
    return dict(
        bytes_pcm_verified=True,
        frames=len(actual),
        rate=rate,
        channels=actual.shape[1],
        maximum_error=float(np.max(np.abs(actual - expected))),
        achieved_db=float(achieved),
        expected_lags=expected_lags,
        measured_lags=found,
        pcm=meta["canonical_pcm"]["sha256"],
    )


def validate(budget, owner):
    cfg = owner.protocol["splits"][owner.split]
    sources, checks = [], []
    for spec in cfg["sources"]:
        generated = record(owner.directory / "generated" / (spec["source_id"] + ".json"))
        source = generated["source"]
        origin = cfg["sources"][spec["duplicate_of"]] if spec["duplicate_of"] is not None else spec
        checks.append(
            check_audio(
                budget, owner, owner.root / source["source"]["local_path"], cfg["families"], origin
            )
        )
        sources.append(source)
    for i, source in enumerate(sources):
        for prior in sources[:i]:
            same = (
                source["source"]["sha256"] == prior["source"]["sha256"]
                or source["source"]["canonical_pcm"] == prior["source"]["canonical_pcm"]
            )
            if same != (source["group"] == prior["group"]):
                raise InputError("D02 actual PCM/byte duplicate groups differ from ancestry")
    neutral = []
    truths = []
    for case in cfg["cases"]:
        value = record(owner.directory / "generated-queries" / (case["case_id"] + ".json"))
        for spec, example in zip(case["examples"], value["examples"], strict=True):
            if spec["source_ordinal"] is None:
                if any(
                    example["audio"]["canonical_pcm"] == s["source"]["canonical_pcm"]
                    or example["audio"]["sha256"] == s["source"]["sha256"]
                    for s in sources
                ):
                    raise InputError(
                        "D02 independent reference unexpectedly equals a candidate parent"
                    )
                checks.append(
                    check_audio(
                        budget,
                        owner,
                        owner.root / example["path"],
                        cfg["families"],
                        spec,
                        True,
                        case["kind"],
                    )
                )
        neutral.append(value)
        events = []
        if case["primary"]:
            for spec, source in zip(cfg["sources"], sources, strict=True):
                if (
                    spec["character"] != "positive"
                    or spec["family"] not in case["positive_characters"]
                ):
                    continue
                for position in spec["positions"]:
                    rate = source["source"]["sample_rate_hz"]
                    a = math.floor(round(position * RATE) * rate / RATE)
                    b = math.ceil(
                        (round(position * RATE) + round(spec["event_seconds"] * RATE)) * rate / RATE
                    )
                    events.append(
                        dict(
                            recording_id=source["recording_id"],
                            group=source["group"],
                            bounds=[a, b],
                            rate=rate,
                            family=spec["family"],
                        )
                    )
        truths.append(
            dict(
                case_id=case["case_id"],
                ordinal=case["ordinal"],
                kind=case["kind"],
                primary=case["primary"],
                condition=case["condition"],
                families=case["positive_characters"],
                events=events,
                positive_groups=sorted({e["group"] for e in events}),
                excluded_candidate_groups=sorted(
                    {
                        sources[e["source_ordinal"]]["group"]
                        for e in case["examples"]
                        if e["source_ordinal"] is not None
                    }
                ),
            )
        )
    population = dict(
        schema_version="d02-population-1",
        split=owner.split,
        sources=sources,
        protocol=owner.protocol["record_hash"],
        discovery=False,
    )
    owner.publish(
        budget,
        owner.directory / "populations" / (owner.split + ".json"),
        population,
        immutable=True,
    )
    owner.publish(
        budget,
        owner.directory / "inputs" / (owner.split + ".json"),
        dict(
            schema_version="d02-inputs-1",
            split=owner.split,
            protocol=owner.protocol["record_hash"],
            queries=neutral,
        ),
        immutable=True,
    )
    truth = dict(
        schema_version="d02-truth-1",
        split=owner.split,
        cases=truths,
        protocol=owner.protocol["record_hash"],
        ancestry=digest(
            [[s["recording_id"], s["group"], s["source"]["canonical_pcm"]] for s in sources]
        ),
    )
    owner.publish(
        budget, owner.directory / "truth" / (owner.split + ".json"), truth, immutable=True
    )
    return dict(
        passed=True,
        sources=len(sources),
        queries=len(neutral),
        checks=checks,
        native_mapping="floor start / ceil end of exact rational 24k-to-native construction map",
    )
