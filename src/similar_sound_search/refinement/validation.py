"""Independent exhaustive frame/float64 scoring oracles; no delivery mutations."""

import math

import numpy as np

from ..storage import InputError
from .geometry import choose, positions, scores


def known_answer():
    checks = 0
    for rate in (7, 8000, 22050, 44100):
        for first, frames, width in (
            (0, 40000, 12000),
            (10000, 40000, 12000),
            (28000, 40000, 12000),
            (0, 37, 37),
        ):
            original = [first, first + width]
            expected = []
            for ms in range(-500, 501, 125):
                n = math.floor(abs(ms) * rate / 1000 + 0.5)
                s = max(0, min(frames - width, first + (-n if ms < 0 else n)))
                expected.append([s, s + width])
            actual = positions(original, frames, rate, list(range(-500, 501, 125)))
            if actual != sorted({tuple(v) for v in expected}):
                if actual != [list(v) for v in sorted({tuple(v) for v in expected})]:
                    raise InputError("C03 independent native offset oracle differs")
            if actual[choose(actual, [1.0] * len(actual), original)] != original:
                raise InputError("C03 exact equal-score original control tie differs")
            checks += 1
    q = np.array([[1.0, 2.0, 3.0], [-2.0, 1.0, 4.0]], dtype=np.float32)
    x = np.array([[2.0, 2.0, 1.0], [1.0, 0.0, 3.0], [-3.0, 2.0, 1.0]], dtype=np.float32)
    per, mean = scores(q, x, {"kind": "mean"}, ["a", "b"])
    for i in range(2):
        for j in range(3):
            scalar = 1 - sum(float(a) * float(b) for a, b in zip(q[i], x[j])) / (
                math.sqrt(sum(float(a) ** 2 for a in q[i]))
                * math.sqrt(sum(float(b) ** 2 for b in x[j]))
            )
            if abs(scalar - per[i, j]) > 1e-15:
                raise InputError("C03 scalar cosine oracle differs")
    if not np.array_equal(mean, np.mean(per, axis=0)):
        raise InputError("C03 scalar objective differs")
    return {
        "status": "ok",
        "passed": True,
        "native_geometries": checks,
        "scalar_distances": 6,
        "ties": "exact original interval retained",
    }
