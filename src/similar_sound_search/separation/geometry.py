"""Independent pre-inference audit of saved native insertions, complete support and cues."""

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..inputs import decode
from ..storage import InputError
from .protocol import load


def validate(budget, context):
    plan = record(context.directory / "preflight.json")
    answers = []
    for case in plan["cases"]:
        signal = next(v for v in plan["signals"] if v["spec"]["sha256"] == case["source_sha256"])
        context.charge(budget, read_audio_seconds=signal["audio"]["duration_seconds"] + 8 + 2.4)
        mixture, meta = decode(budget.root / signal["spec"]["path"], budget)
        exact, em = decode(budget.root / case["evaluator_target"]["path"], budget)
        cue, cm = decode(budget.root / case["cue"]["path"], budget)
        target, asset = load(budget, context, case["target_asset"])
        if (
            meta["sha256"] != case["source_sha256"]
            or em["sha256"] != case["evaluator_target"]["sha256"]
            or cm["sha256"] != case["cue"]["sha256"]
            or len(mixture) != case["source_frames"]
            or len(exact) != len(mixture)
            or len(cue) != 57600
            or meta["sample_rate_hz"] != case["rate"]
        ):
            raise InputError(
                "B02 geometry: actual source/cue identity/support changed: " + case["case_id"]
            )
        expected = np.zeros_like(exact)
        if case["insertion"]:
            a, b = case["insertion"]
            if b - a != len(target):
                raise InputError("B02 geometry: complete rendered insertion length differs")
            expected[a:b] = (
                target.astype(float) * case["target_gain"] * case["common_gain"]
            ).astype(np.float32)
        quantization_error = float(np.max(np.abs(expected.astype(float) - exact)))
        # Construction multiplies native float32 target samples before the common
        # float64 gain. Audit independently in float64 with a two-ULP allowance;
        # the saved inserted float32 component remains the evaluator's exact truth.
        if not np.allclose(expected, exact, atol=2e-8, rtol=1e-7):
            raise InputError(
                "B02 geometry: inserted exact component/gains differ: " + case["case_id"]
            )
        first, last = case["event"]
        full = (
            case["insertion"] is not None
            and first <= case["insertion"][0]
            and last >= case["insertion"][1]
        )
        if full != case["complete_target_support"] or (
            case["stratum"].startswith("positive") and not full
        ):
            raise InputError("B02 geometry: unexpected absent/truncated positive")
        background = mixture[first:last].astype(float) - exact[first:last]
        tp = float(np.mean(exact[first:last].astype(float) ** 2))
        bp = float(np.mean(background**2))
        achieved = float(10 * np.log10(tp / bp)) if tp and bp > 1e-20 else None
        if case["region_tbr_db"] is not None and (
            achieved is None or abs(achieved - case["region_tbr_db"]) > 1e-4
        ):
            raise InputError("B02 geometry: actual selected-region target/background ratio differs")
        # Each A04 event includes its full decay; only the declared censored stratum
        # may lose support. These notes never enter the operational DSP interface.
        notes = []
        if case["insertion"]:
            for note in asset["events"]:
                a = case["insertion"][0] + note["start_frame"]
                b = case["insertion"][0] + note["end_frame"]
                notes.append({"first": a, "last": b, "complete": first <= a and b <= last})
        answers.append(
            {
                "case_id": case["case_id"],
                "actual_source_sha256": meta["sha256"],
                "target_gain_quantization_max_error": quantization_error,
                "insertion": case["insertion"],
                "event": [first, last],
                "rate": meta["sample_rate_hz"],
                "full_target": full,
                "notes": notes,
                "actual_selected_tbr_db": achieved,
                "cue_sha256": cm["sha256"],
                "cue_is_different_performance": True,
                "candidate_truth_checked": bool(case["truth_assets"]) if tp else "declared-absent",
            }
        )
    value = {
        "schema_version": "b02-geometry-1",
        "preflight_hash": plan["record_hash"],
        "cases": answers,
        "positive_full_support": all(
            v["complete_target_support"]
            for v in plan["cases"]
            if v["stratum"].startswith("positive")
        ),
        "input_to_region": "native integer translation; no source resampling or time shift",
        "cue_conversion": "native24k; real44.1k; any cue-rate change is explicit polyphase; "
        "output remains source-native",
    }
    write_record(context.directory / "geometry.json", value, budget)
    return value
