"""Fixed-scale spectral/cepstral and envelope baseline; no learned fit or pitch term."""

import math

import numpy as np
from scipy.fft import dct
from scipy.signal import resample_poly

from ..storage import InputError


def waveform(samples, rate, output_rate):
    value = np.asarray(samples, dtype=np.float32)
    if value.ndim == 2:
        if not 1 <= value.shape[1] <= 8:
            raise InputError("representation: one to eight channels required")
        value = value.mean(axis=1)
    if (
        value.ndim != 1
        or not len(value)
        or not np.isfinite(value).all()
        or not isinstance(rate, int)
        or isinstance(rate, bool)
        or not 0 < rate <= 192000
        or len(value) > 30 * rate
    ):
        raise InputError(
            "representation: nonempty finite mono/stereo waveform and integer rate required"
        )
    divisor = math.gcd(rate, output_rate)
    if max(rate // divisor, output_rate // divisor) > 1024:
        raise InputError("representation: resampling factor exceeds 1024")
    if rate != output_rate:
        value = resample_poly(
            value,
            output_rate // divisor,
            rate // divisor,
            window=("kaiser", 5.0),
            padtype="constant",
        )
    return np.ascontiguousarray(value, dtype=np.float32)


def checked(feature, dimension):
    value = np.asarray(feature, dtype=np.float32)
    if value.shape != (dimension,) or not np.isfinite(value).all():
        raise InputError(f"representation: expected finite float32 vector of dimension {dimension}")
    return value


class Acoustic:
    dimension = 56
    input_rate = 24000

    def encode(self, samples, rate):
        x = waveform(samples, rate, self.input_rate).astype(float)
        x = np.pad(x, (0, max(0, 600 - len(x))))
        starts = list(range(0, len(x) - 600 + 1, 240))
        if starts[-1] != len(x) - 600:
            starts.append(len(x) - 600)
        frames = np.array([x[s : s + 600] for s in starts])
        power = np.abs(np.fft.rfft(frames * np.hanning(600), n=1024)) ** 2
        probability = power / np.maximum(power.sum(axis=1, keepdims=True), 1e-20)
        frequencies = np.fft.rfftfreq(1024, 1 / 24000)
        mel_edges = 700 * (np.exp(np.linspace(np.log1p(40 / 700), np.log1p(12000 / 700), 42)) - 1)
        filters = np.maximum(
            0,
            np.minimum(
                (frequencies[None, :] - mel_edges[:-2, None])
                / (mel_edges[1:-1, None] - mel_edges[:-2, None]),
                (mel_edges[2:, None] - frequencies[None, :])
                / (mel_edges[2:, None] - mel_edges[1:-1, None]),
            ),
        )
        filters /= np.maximum(filters.sum(axis=1, keepdims=True), 1e-20)
        cepstra = dct(
            np.log(np.maximum(probability @ filters.T, 1e-10)), type=2, norm="ortho", axis=1
        )[:, :13]
        centroid = (probability * frequencies).sum(axis=1)
        spread = np.sqrt((probability * (frequencies - centroid[:, None]) ** 2).sum(axis=1))
        flatness = np.exp(np.log(np.maximum(power, 1e-20)).mean(axis=1)) / np.maximum(
            power.mean(axis=1), 1e-20
        )
        rolloff = frequencies[np.argmax(np.cumsum(probability, axis=1) >= 0.85, axis=1)]
        zcr = np.mean(frames[:, 1:] * frames[:, :-1] < 0, axis=1)
        spectral = np.stack(
            [centroid / 12000, spread / 12000, flatness, rolloff / 12000, zcr], axis=1
        )
        rms = np.sqrt(np.mean(x * x))
        envelope = np.array([np.sqrt(np.mean(part * part)) for part in np.array_split(x, 16)])
        relative = envelope / max(rms, 1e-12)
        extra = [
            np.log10(max(rms, 1e-10)) / 10,
            np.max(np.abs(x)) / max(rms, 1e-12) / 10,
            float(np.argmax(envelope)) / 15,
            np.log10((envelope[-1] + 1e-10) / (envelope[0] + 1e-10)) / 10,
        ]
        return checked(
            np.r_[
                cepstra.mean(axis=0) / 10,
                cepstra.std(axis=0) / 10,
                spectral.mean(axis=0),
                spectral.std(axis=0),
                relative * 0.25,
                extra,
            ],
            self.dimension,
        )


def distance(a, b, kind):
    a, b = np.asarray(a), np.asarray(b)
    if a.ndim != 1 or a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise InputError("distance: equal finite vector shapes required")
    if kind == "euclidean":
        return float(np.linalg.norm(a - b))
    if kind != "cosine" or min(np.linalg.norm(a), np.linalg.norm(b)) <= 1e-12:
        raise InputError("distance: cosine requires nonzero embeddings and explicit metric")
    return float(1 - np.clip(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))
