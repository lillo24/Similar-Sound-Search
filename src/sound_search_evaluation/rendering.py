"""Single full-release event from the reviewed A04 mechanism equations."""

import numpy as np
from scipy.signal import butter, sosfilt


def single_event(preset, pitch, seed):
    """A04's first 1.1s note, without later-note overlap; a declared new construction."""
    rate = 24000
    t = np.arange(26400) / rate
    frequency = 440 * 2 ** ((60 + pitch - 69) / 12)
    p, mechanism = preset["parameters"], preset["mechanism"]
    envelope = np.clip(np.minimum(1, t / 0.025) * np.minimum(1, (1.1 - t) / 0.2), 0, 1)
    if mechanism in {"harmonic", "pluck"}:
        signal = sum(
            np.sin(2 * np.pi * frequency * h * t) / h ** p["spectral_slope"] for h in range(1, 9)
        )
        env = envelope if mechanism == "harmonic" else envelope * np.exp(-t * 5.5)
    elif mechanism == "fm":
        signal = np.sin(
            2 * np.pi * frequency * t
            + 2 * np.exp(-t * 2) * np.sin(2 * np.pi * frequency * p["fm_ratio"] * t)
        )
        env = envelope * np.exp(-t * 1.8)
    else:
        noise = sosfilt(
            butter(2, p["cutoff_hz"], fs=rate, output="sos"),
            np.random.default_rng(seed).standard_normal(len(t)),
        )
        signal = 0.8 * noise + 0.2 * np.sin(2 * np.pi * frequency * t)
        env = envelope * np.exp(-t * 3)
    result = signal * env
    return result * (0.08 / np.sqrt(np.mean(result * result)))
