"""Independent impulse/geometry answers and a single charged feasibility pilot."""

import time

import numpy as np

from ..storage import InputError
from . import dsp


def run(budget, context, pilot=False):
    rate = 24000
    x = np.zeros((rate * 3, 2), np.float32)
    t = np.arange(len(x)) / rate
    target = (
        0.1
        * np.sin(2 * np.pi * 440 * t)
        * (np.minimum(t / 0.025, 1))
        * np.minimum((3 - t) / 0.2, 1)
    )
    x[:, 0] = target + 0.03 * np.sin(2 * np.pi * 523.25 * t)
    x[:, 1] = -target + 0.03 * np.sin(2 * np.pi * 523.25 * t)
    cue = target[: rate * 2, None].astype(np.float32)
    context.charge(budget, processing_inputs=2, separator_input_seconds=8)
    budget.reserve(131072, context.cfg["max_temporary_bytes"])
    started = time.perf_counter()
    broad, bm = dsp.process(x, rate, "broad", context.cfg)
    guided, gm = dsp.process(x, rate, "guided", context.cfg, cue, rate)
    if max(bm["reconstruction_max_error"], gm["reconstruction_max_error"]) > 1e-6:
        raise InputError("B02 pilot: reconstruction exceeds fixed float32 tolerance")
    impulse = np.zeros((8193, 2), np.float32)
    impulse[[0, 255, 256, 4096, 8192], :] = 0.5
    z, w, p = dsp.stft(impulse, context.cfg)
    roundtrip = dsp.inverse(z, w, p, len(impulse), context.cfg)
    if not np.allclose(roundtrip, impulse, atol=1e-7) or np.argmax(roundtrip[:, 0]) not in [
        0,
        255,
        256,
        4096,
        8192,
    ]:
        raise InputError("B02 known answer: centred STFT introduced delay/seam")
    return {
        "schema_version": "b02-pilot-1" if pilot else "b02-known-answer-1",
        "seconds": time.perf_counter() - started,
        "learned_separator_ran": False,
        "processing_gain": 1,
        "native_frames": len(x),
        "channels": 2,
        "impulse_max_error": float(np.max(np.abs(roundtrip - impulse))),
        "broad": bm,
        "guided": gm,
        "guided_energy_ratio": dsp.summaries(guided["extracted"], x)["energy_ratio_to_mixture"],
        "interpretation": "feasibility/correctness only; "
        "no target-quality promotion from reconstruction",
    }
