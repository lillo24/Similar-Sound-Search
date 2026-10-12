"""Procedural sound identities and independently parameterised target insertion."""

import numpy as np
from scipy.signal import butter, sosfilt

from ..storage import InputError

RATE = 24000
FRAMES = 57600  # 2.4 seconds; includes the entire final 1.1-second release.
MIX_FRAMES = 192000
PHRASES = ((0, 4, 7), (7, 0, 4), (4, 7, 0))


def presets(seed):
    result = []
    for mechanism in ("harmonic", "pluck", "fm", "noise"):
        families = [f"procedural:{mechanism}:{n}" for n in range(2)]
        from ..storage import digest

        development = min(families, key=lambda f: digest([seed, f]))
        for n, family in enumerate(families):
            for variant in range(2):
                result.append(
                    {
                        "family": family,
                        "mechanism": mechanism,
                        "variant": variant,
                        "colour": n,
                        "split": "development" if family == development else "held_out",
                        "preset_id": digest(["a04-preset-1", mechanism, n, variant]),
                        "parameters": {
                            "spectral_slope": 1.0 + n * 0.6 + variant * 0.15,
                            "fm_ratio": 1.414 + n * 0.317 + variant * 0.08,
                            "cutoff_hz": 900 + n * 1600 + variant * 180,
                        },
                    }
                )
    return result


def render_tone(preset, phrase, pitch, seed):
    """All identities share note/level/duration conditions; no waveform labels are human ratings."""
    output = np.zeros(FRAMES, dtype=np.float64)
    rng = np.random.default_rng(seed)
    events = []
    length = 26400
    t = np.arange(length) / RATE
    # Linear attack/release ramps define the full 1.1-second event window.
    envelope = np.minimum(1, t / 0.025) * np.minimum(1, (1.1 - t) / 0.2)
    envelope = np.clip(envelope, 0, 1)
    for note_index, relative in enumerate(PHRASES[phrase]):
        start = int(note_index * 0.65 * RATE)
        frequency = 440 * 2 ** ((60 + pitch + relative - 69) / 12)
        p = preset["parameters"]
        mechanism = preset["mechanism"]
        if mechanism in {"harmonic", "pluck"}:
            signal = sum(
                np.sin(2 * np.pi * frequency * harmonic * t) / harmonic ** p["spectral_slope"]
                for harmonic in range(1, 9)
            )
            env = envelope if mechanism == "harmonic" else envelope * np.exp(-t * 5.5)
        elif mechanism == "fm":
            signal = np.sin(
                2 * np.pi * frequency * t
                + (2.0 + preset["variant"] * 0.4)
                * np.exp(-t * 2)
                * np.sin(2 * np.pi * frequency * p["fm_ratio"] * t)
            )
            env = envelope * np.exp(-t * 1.8)
        elif mechanism == "noise":
            sos = butter(2, p["cutoff_hz"], fs=RATE, output="sos")
            noise = sosfilt(sos, rng.standard_normal(length))
            signal = 0.8 * noise + 0.2 * np.sin(2 * np.pi * frequency * t)
            env = envelope * np.exp(-t * 3)
        else:
            raise InputError("renderer: unknown sound mechanism")
        output[start : start + length] += signal * env
        events.append(
            {"start_frame": start, "end_frame": start + length, "midi_note": 60 + pitch + relative}
        )
    output *= 0.08 / np.sqrt(np.mean(output * output))
    if np.max(np.abs(output)) > 0.9:
        raise InputError("renderer: fixed RMS policy would clip; change the reviewed recipe")
    return output, {
        "events": events,
        "level_policy": "whole-render RMS 0.08; peak <=0.9",
        "source_identity_proxy": True,
    }


def mix(target, background, positions, ratio_db):
    """TBR uses RMS of the summed target and background over the union of active spans.

    Final common scaling preserves their ratio. Target truth comes only from insertion.
    The caller must supply a different designated source for absent-target mixtures.
    """
    background = np.asarray(background, dtype=float).reshape(-1)
    if len(background) != MIX_FRAMES or not np.isfinite(background).all():
        raise InputError("mixture: invalid background samples")
    stem = np.zeros(MIX_FRAMES)
    active = np.zeros(MIX_FRAMES, dtype=bool)
    intervals = []
    for position in positions:
        if (
            not isinstance(position, int)
            or not 0 <= position < position + len(target) <= MIX_FRAMES
        ):
            raise InputError("mixture: target insertion out of sample bounds")
        stem[position : position + len(target)] += target
        active[position : position + len(target)] = True
        intervals.append([position, position + len(target)])
    background_gain = 1.0
    target_gain = 0.0
    achieved = None
    if positions:
        b_rms = np.sqrt(np.mean(background[active] ** 2))
        t_rms = np.sqrt(np.mean(stem[active] ** 2))
        if min(b_rms, t_rms) <= 1e-12:
            raise InputError("mixture: silent active target/background; TBR undefined")
        target_gain = b_rms / t_rms * 10 ** (ratio_db / 20)
        achieved = float(20 * np.log10(np.sqrt(np.mean((stem[active] * target_gain) ** 2)) / b_rms))
    combined = background * background_gain + stem * target_gain
    peak = np.max(np.abs(combined))
    if peak <= 1e-12:
        raise InputError("mixture: silent output")
    common = min(1.0, 0.9 / peak)
    return combined * common, {
        "insertions": intervals,
        "target_gain": float(target_gain),
        "background_gain": background_gain,
        "common_gain": float(common),
        "requested_tbr_db": ratio_db if positions else None,
        "achieved_tbr_db": achieved,
        "ratio_interval": "union of complete inserted renders (including release); "
        "no outer silence",
    }
