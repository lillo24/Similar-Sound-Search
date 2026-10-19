"""Small independent B01 boundary signals and expected native sample positions."""

import numpy as np


def boundary_cases(rate=8000):
    """Recipes are engineering probes, not additional independent timbre families."""
    frames = rate * 3

    def tone(first, last, hz=220, attack=0.025, vibrato=False, noise=False):
        n = last - first
        t = np.arange(n) / rate
        envelope = np.minimum(1, t / attack) * np.minimum(1, (n / rate - t) / 0.2)
        phase = 2 * np.pi * hz * t + (0.4 * np.sin(2 * np.pi * 5 * t) if vibrato else 0)
        wave = np.random.default_rng(910).normal(size=n) * 0.2 if noise else np.sin(phase) * 0.2
        result = np.zeros(frames, np.float32)
        result[first:last] = wave * np.clip(envelope, 0, 1)
        return result

    def event(first, last):
        return {"start_frame": round(first * rate), "end_frame": round(last * rate)}

    specifications = [
        ("isolated", [event(0.2, 1.3)], {}),
        ("overlap_release", [event(0.2, 1.5), event(0.7, 2)], {}),
        ("slow_attack", [event(0.2, 1.8)], {"attack": 0.3}),
        ("short_transient", [event(0.2, 0.28)], {"attack": 0.003}),
        ("noise", [event(0.25, 1)], {"noise": True}),
        ("vibrato", [event(0.3, 1.6)], {"vibrato": True}),
        ("close_notes", [event(0.2, 0.8), event(0.35, 0.95)], {}),
        ("stereo_cancellation", [event(0.2, 1.3)], {}),
        ("censored_sustain", [event(0, 3)], {}),
        ("silence", [], {}),
    ]
    result = []
    for name, truth, options in specifications:
        x = np.zeros(frames, np.float32)
        for i, e in enumerate(truth):
            x += tone(e["start_frame"], e["end_frame"], hz=220 + i * 137, **options)
        if name == "censored_sustain":
            x = (0.2 * np.sin(2 * np.pi * 220 * np.arange(frames) / rate)).astype(np.float32)
        samples = np.stack([x, -x], axis=1) if name == "stereo_cancellation" else x[:, None]
        result.append(
            {
                "case": name,
                "samples": samples,
                "rate": rate,
                "truth": truth,
                "truth_end_observed": name != "censored_sustain",
            }
        )
    return result
