"""PCM/representation feature blobs shared across provenance and pitch revisions."""

import time

import numpy as np

from ..inputs import decode
from ..matchers.acoustic import checked
from ..matchers.models import adapter
from ..matchers.runner import memory_check
from ..search.contracts import load_array, save_array
from ..storage import digest


class Features:
    def __init__(self, budget, owner, desc):
        self.budget, self.owner, self.desc = budget, owner, desc
        self.model = None
        self.new = self.reused = 0
        self.load_seconds = self.encode_seconds = 0

    def get(self, samples, audio):
        identity = {
            "version": "b03-feature-1",
            "pcm": audio["canonical_pcm"],
            "representation": self.desc,
            "dimension": self.desc["dimension"],
        }
        root = self.owner.root / "data/features/queries"
        path = root / digest(identity)
        if path.exists():
            self.reused += 1
            return load_array(path, identity, self.budget)[0][0]
        self.owner.charge(
            self.budget,
            feature_windows=1,
            feature_bytes=self.desc["dimension"] * 4 + 65536,
            processed_window_seconds=audio["duration_seconds"],
        )
        self.budget.reserve(65536 + self.desc["dimension"] * 4, 768 * 1024**2 + samples.nbytes * 3)
        if self.model is None:
            self.model, self.load_seconds = adapter(self.budget, "efficientat", self.desc)
        started = time.perf_counter()
        vector = checked(
            self.model.encode(samples, audio["sample_rate_hz"]), self.desc["dimension"]
        )
        self.encode_seconds += time.perf_counter() - started
        save_array(root, identity, vector[None], self.budget)
        self.new += 1
        memory_check(self.budget)
        return vector

    def stats(self):
        return {
            "new": self.new,
            "reused": self.reused,
            "load_seconds": self.load_seconds,
            "encode_seconds": self.encode_seconds,
        }


def collection(budget, owner, examples, desc):
    cache = Features(budget, owner, desc)
    vectors = []
    for example in examples:
        owner.charge(budget, read_audio_seconds=example["audio"]["duration_seconds"])
        samples, audio = decode(budget.root / example["prepared"]["artifact"]["local_path"], budget)
        vectors.append(cache.get(samples, audio))
    owner.feature_stats = cache.stats()
    return np.stack(vectors), cache.stats()
