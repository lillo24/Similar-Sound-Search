"""Optional conservative classical pitch preference; ambiguous audio abstains."""

import numpy as np
from scipy.signal import correlate

from ..matchers.acoustic import waveform
from ..storage import InputError


def estimate(samples, rate):
    x = waveform(samples, rate, 8000).astype(np.float64)
    if np.max(np.abs(x)) < 1e-6:
        return {"hz": None, "reason": "silent", "reliable_blocks": 0}
    notes = []
    for start in range(0, len(x) - 2048 + 1, 1024):
        block = x[start : start + 2048]
        block = (block - block.mean()) * np.hanning(len(block))
        if np.sqrt(np.mean(block * block)) < 1e-5:
            continue
        power = np.abs(np.fft.rfft(block)) ** 2
        # A narrow dominant fundamental is a deliberately conservative monophonic gate.
        peak = int(np.argmax(power[13:257]) + 13)
        concentration = np.sum(power[max(0, peak - 2) : peak + 3]) / max(np.sum(power), 1e-30)
        if concentration < 0.75:
            continue
        ac = correlate(block, block, mode="full", method="fft")[len(block) - 1 :]
        lo, hi = 16, 161  # 50..500 Hz at 8 kHz; higher/low notes deliberately abstain.
        lag = int(np.argmax(ac[lo:hi]) + lo)
        if ac[lag] / max(ac[0], 1e-30) < 0.9:
            continue
        hz = 8000 / lag
        spectral_hz = peak * 8000 / 2048
        if abs(12 * np.log2(hz / spectral_hz)) > 0.5:
            continue
        notes.append(float(69 + 12 * np.log2(hz / 440)))
    if len(notes) < 2 or np.ptp(notes) > 0.5:
        return {
            "hz": None,
            "reason": "ambiguous/polyphonic/unstable or outside 50..500Hz",
            "reliable_blocks": len(notes),
        }
    return {
        "hz": float(440 * 2 ** ((np.median(notes) - 69) / 12)),
        "reason": "stable narrow monophonic fundamental",
        "reliable_blocks": len(notes),
    }


def penalty(query_estimates, candidate, weight):
    if not np.isfinite(weight) or not 0 <= weight <= 0.05:
        raise InputError("pitch preference: explicit weight must be in 0..0.05")
    if weight == 0 or candidate["hz"] is None or any(q["hz"] is None for q in query_estimates):
        return 0.0
    mismatch = np.mean(
        [min(1, abs(12 * np.log2(q["hz"] / candidate["hz"])) / 12) for q in query_estimates]
    )
    return float(weight * mismatch)
