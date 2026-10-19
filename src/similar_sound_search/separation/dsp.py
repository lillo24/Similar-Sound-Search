"""Deterministic HPSS and audio-template activation masks; no labels or truth input."""

import math

import numpy as np
from scipy.fft import irfft, rfft
from scipy.ndimage import median_filter
from scipy.signal import resample_poly

from ..storage import InputError, ResourceError


def checked(samples):
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim != 2 or not len(x) or x.shape[1] > 2 or not np.isfinite(x).all():
        raise InputError("separation: finite nonempty mono/stereo samples required")
    return x


def stft(samples, cfg):
    x = checked(samples)
    n, hop = cfg["fft_frames"], cfg["hop_frames"]
    # Centre every window on its source coordinate. Explicit zeros at both ends;
    # pad right to the hop grid and undo exactly this padding after overlap-add.
    right = n // 2 + (-len(x)) % hop
    padded = np.pad(x, ((n // 2, right), (0, 0)))
    frames = np.lib.stride_tricks.sliding_window_view(padded, n, axis=0)[::hop]
    window = np.hanning(n + 1)[:-1].astype(np.float32)
    z = rfft(frames * window, axis=-1).transpose(1, 2, 0)
    return z, window, len(padded)


def inverse(z, window, padded_frames, frames, cfg):
    n, hop = len(window), cfg["hop_frames"]
    blocks = irfft(z.transpose(2, 0, 1), n=n, axis=-1)
    result = np.zeros((padded_frames, z.shape[0]), dtype=np.float64)
    weight = np.zeros(padded_frames, dtype=np.float64)
    for i, block in enumerate(blocks):
        first = i * hop
        result[first : first + n] += block.T * window[:, None]
        weight[first : first + n] += window.astype(np.float64) ** 2
    selected = slice(n // 2, n // 2 + frames)
    if np.any(weight[selected] < 1e-8):
        raise InputError("separation reconstruction: uncovered native frames")
    return checked((result[selected] / weight[selected, None]).astype(np.float32))


def convert_cue(cue, rate, cue_rate):
    cue = checked(cue)
    factor = math.gcd(rate, cue_rate)
    # Zero-phase polyphase conversion; no cue timeline is attached to the source.
    return resample_poly(cue, rate // factor, cue_rate // factor, axis=0).astype(np.float32)


def summaries(x, original):
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    base = float(np.sqrt(np.mean(original.astype(np.float64) ** 2)))
    return {
        "rms": rms,
        "peak": float(np.max(np.abs(x))),
        "overload_samples": int(np.count_nonzero(np.abs(x) > 1)),
        "energy_ratio_to_mixture": float(
            np.sum(x.astype(float) ** 2) / max(float(np.sum(original.astype(float) ** 2)), 1e-30)
        ),
        "state": "near_silence" if rms < max(1e-7, base * 1e-4) else "ok",
    }


def process(samples, rate, mode, cfg, cue=None, cue_rate=None):
    x = checked(samples)
    if mode == "original":
        return {"original": x.copy()}, {"delay_frames": 0, "processing_gain": 1.0}
    if mode not in {"broad", "guided"}:
        raise InputError("separation: choose original, broad or guided")
    if isinstance(rate, bool) or not isinstance(rate, int) or not 8000 <= rate <= 96000:
        raise InputError("processed separation requires a native rate of 8000..96000 Hz")
    if len(x) / rate > cfg["max_region_seconds"]:
        raise ResourceError("separation: region exceeds 12 seconds; no hidden chunking")
    n, hop = cfg["fft_frames"], cfg["hop_frames"]
    estimate = (len(x) // hop + 5) * (n // 2 + 1) * x.shape[1] * 64 + x.nbytes * 8
    if estimate > cfg["max_temporary_bytes"]:
        raise ResourceError("separation: temporary STFT allocation exceeds fixed ceiling")
    z, window, padded = stft(x, cfg)
    magnitude = np.mean(np.abs(z), axis=0).astype(np.float64)
    if mode == "broad":
        h = median_filter(magnitude, size=(1, cfg["median_frames"]), mode="nearest")
        p = median_filter(magnitude, size=(cfg["median_frames"], 1), mode="nearest")
        mask = h * h / np.maximum(h * h + p * p, 1e-30)
        names = ("harmonic", "percussive")
    else:
        if cue is None or cue_rate is None:
            raise InputError(
                "guided extraction: explicit audio cue required; no hidden-truth fallback"
            )
        if len(cue) / cue_rate > cfg["max_cue_seconds"] or not 8000 <= cue_rate <= 96000:
            raise InputError("guided extraction: cue exceeds duration/rate bounds")
        cue = convert_cue(cue, rate, cue_rate)
        if np.sqrt(np.mean(cue.astype(float) ** 2)) < 1e-7:
            raise InputError("guided extraction: silent cue is unavailable")
        cz, _, _ = stft(cue, cfg)
        cm = np.mean(np.abs(cz), axis=0)

        def templates(m, count):
            return np.stack(
                [np.mean(part, axis=1) for part in np.array_split(m, count, axis=1)], axis=1
            )

        k = cfg["cue_templates"]
        if cm.shape[1] < k or magnitude.shape[1] < cfg["background_templates"]:
            raise InputError("guided extraction: insufficient source/cue STFT frames")
        # Only operational audio enters: fixed chronological cue templates and
        # eight mixture templates. W stays fixed; deterministic all-one H, no RNG.
        profile = np.mean(cm, axis=1)
        profile /= max(float(np.max(profile)), 1e-20)
        background = templates(magnitude, cfg["background_templates"])
        # A cue-derived exclusion prior prevents the background dictionary from
        # explaining all cue energy using identical mixture templates. It cannot
        # distinguish two timbres sharing the same spectral support.
        background *= (1 - profile[:, None]) ** 2
        w = np.maximum(np.column_stack((templates(cm, k), background)), 1e-12)
        w /= np.sum(w, axis=0, keepdims=True)
        activation = np.ones((w.shape[1], magnitude.shape[1]))
        numerator, gram = w.T @ magnitude, w.T @ w
        for _ in range(cfg["iterations"]):
            activation *= numerator / np.maximum(gram @ activation, 1e-20)
        target = w[:, :k] @ activation[:k]
        residual = w[:, k:] @ activation[k:]
        mask = target**2 / np.maximum(target**2 + residual**2, 1e-30)
        names = ("extracted", "residual")
    a = inverse(z * mask[None], window, padded, len(x), cfg)
    b = inverse(z * (1 - mask)[None], window, padded, len(x), cfg)
    error = float(np.max(np.abs((a + b).astype(float) - x)))
    return dict(zip(names, (a, b), strict=True)), {
        "delay_frames": 0,
        "processing_gain": 1.0,
        "reconstruction_max_error": error,
        "temporary_preflight_bytes": estimate,
        "chunks": 1,
        "channel_policy": "shared mean-magnitude mask; preserve native phase/channels",
        "padding": "centred FFT/2 zeros each edge, right hop-grid zeros; exact native-length trim",
        "iterations": cfg["iterations"] if mode == "guided" else 0,
    }
