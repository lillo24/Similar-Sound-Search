"""B02-only feature misses; frozen adapter and array contracts are shared unchanged."""

import hashlib
import time

import numpy as np

from ..matchers.acoustic import checked
from ..matchers.models import adapter
from ..matchers.runner import memory_check
from ..search.contracts import load_array, save_array
from ..storage import digest


class Features:
    def __init__(self, budget, context, desc):
        self.budget, self.context, self.desc = budget, context, desc
        self.model = None
        self.created = self.reused = 0
        self.load_seconds = self.encode_seconds = 0
        self.peak = 0

    def get(self, samples, rate):
        x = np.ascontiguousarray(samples, dtype=np.float32)
        if np.sqrt(np.mean(x.astype(float) ** 2)) < 1e-7:
            return None
        identity = {
            "version": "b02-feature-1",
            "pcm": hashlib.sha256(x.tobytes()).hexdigest(),
            "shape": list(x.shape),
            "rate": rate,
            "representation": self.desc,
            "dimension": self.desc["dimension"],
        }
        directory = self.budget.root / "data/features/separation"
        path = directory / digest(identity)
        if path.exists():
            self.reused += 1
            return load_array(path, identity, self.budget)[0][0]
        self.context.charge(
            self.budget,
            feature_windows=1,
            feature_bytes=self.desc["dimension"] * 4 + 65536,
            processed_window_seconds=len(x) / rate,
        )
        self.budget.reserve(self.desc["dimension"] * 4 + 65536, 768 * 1024**2 + x.nbytes * 3)
        if self.model is None:
            self.model, self.load_seconds = adapter(self.budget, "efficientat", self.desc)
        started = time.perf_counter()
        vector = checked(self.model.encode(x, rate), self.desc["dimension"])
        self.encode_seconds += time.perf_counter() - started
        save_array(directory, identity, vector[None], self.budget)
        self.created += 1
        self.peak = max(self.peak, memory_check(self.budget))
        return vector

    def stats(self):
        return {
            "new": self.created,
            "reused": self.reused,
            "load_seconds": self.load_seconds,
            "encode_seconds": self.encode_seconds,
            "peak_working_bytes": self.peak,
        }
