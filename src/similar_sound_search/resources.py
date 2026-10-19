"""Required tier configuration, preflight estimates, and monotonic deadlines."""

import math
import os
import shutil
import time
from pathlib import Path

from .storage import InputError, ResourceError, contained, is_link, read_json

LIMITS = {
    "max_input_bytes",
    "max_duration_seconds",
    "max_channels",
    "max_sample_rate_hz",
    "max_decoded_bytes",
    "max_working_bytes",
    "max_output_bytes",
    "max_managed_bytes",
    "min_free_bytes",
    "max_seconds",
    "max_inventory_files",
    "max_resample_factor",
    "concurrency",
    "max_download_bytes",
    "max_model_candidates",
}
MANAGED = (
    "data",
    "reports/local",
    "manifests/private",
    "manifests/catalogue",
    "manifests/evaluation",
    "manifests/matchers",
    "manifests/search",
    "manifests/events",
)


def load_limits(path, tier):
    document = read_json(path)
    if not isinstance(document, dict) or document.get("schema_version") != "a02-resources-1":
        raise InputError(f"resource profile {path}: expected schema a02-resources-1")
    if document.get("policy") != {
        "paid_services": False,
        "private_audio_uploads": False,
        "public_deployment": False,
    }:
        raise InputError(f"resource profile {path}: A02 requires local, unpaid, private operation")
    tiers = document.get("tiers")
    if not isinstance(tiers, dict):
        raise InputError(f"resource profile {path}: expected tiers object")
    limits = tiers.get(tier)
    if not isinstance(limits, dict) or set(limits) != LIMITS:
        raise InputError(f"resource profile {path}: tier {tier!r} requires {sorted(LIMITS)}")
    for key, value in limits.items():
        lower = 0 if key in {"max_download_bytes", "max_model_candidates"} else 1
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or abs(value) > 2**63 - 1
            or not math.isfinite(value)
            or value < lower
            or (key not in {"max_seconds", "max_duration_seconds"} and not isinstance(value, int))
        ):
            raise InputError(f"resource profile {path}: invalid numeric {key}={value!r}")
    if limits["concurrency"] != 1:
        raise InputError("resource profile: A02 supports concurrency=1 only")
    return limits


class Budget:
    def __init__(self, root, limits):
        self.root = Path(root).resolve()
        self.limits = limits
        self.started = time.monotonic()

    def check_time(self, step, target):
        elapsed = time.monotonic() - self.started
        if elapsed > self.limits["max_seconds"]:
            raise ResourceError(f"{step} {target}: elapsed {elapsed:.3f}s exceeds max_seconds")

    def cap(self, key, actual, target):
        if actual > self.limits[key]:
            raise ResourceError(f"{target}: {key}={self.limits[key]}, estimated/observed {actual}")

    def input_file(self, path):
        path = Path(path)
        if is_link(path) or not path.is_file():
            raise InputError(f"inspect {path}: expected an existing regular, non-symlink file")
        self.cap("max_input_bytes", path.stat().st_size, path)
        self.check_time("inspect", path)

    def managed_bytes(self):
        size = 0
        count = 0
        for relative in MANAGED:
            base = contained(self.root / relative, self.root)
            for directory, dirs, files in os.walk(base, followlinks=False):
                self.check_time("disk inventory", base)
                dirs[:] = [d for d in dirs if not is_link(Path(directory) / d)]
                for name in files:
                    path = Path(directory) / name
                    if not is_link(path):
                        size += path.stat().st_size
                    count += 1
                    if count % 256 == 0:
                        self.check_time("disk inventory", base)
                    if count > 100000:
                        raise ResourceError(
                            "disk inventory: exceeds 100000 managed files; prune locally"
                        )
        return size

    def reserve(self, output_bytes, working_bytes=0):
        self.cap("max_output_bytes", output_bytes, "output preflight")
        self.cap("max_working_bytes", working_bytes, "memory preflight")
        managed = self.managed_bytes()
        self.cap("max_managed_bytes", managed + output_bytes, "managed disk preflight")
        free = shutil.disk_usage(self.root).free
        if free - output_bytes < self.limits["min_free_bytes"]:
            raise ResourceError(
                f"disk preflight: free={free}, reserve={output_bytes}, "
                f"required headroom={self.limits['min_free_bytes']} bytes"
            )
        self.check_time("preflight", self.root)
        return {"managed_bytes_before": managed, "free_bytes_before": free}


class CatalogueBudget(Budget):
    """Locked worker disk inventory with explicit accounting for its owned file writes.

    Rewalking all catalogue files twice per ledger read/update is quadratic. The worker
    holds the exclusive project operation lock, tracks exact logical file sizes, and
    refreshes at A02 preparation boundaries. A crash discards this in-memory cache;
    the next worker scans actual disk,
    including abandoned partials. Free-space checks and all ceilings remain unchanged.
    """

    def __init__(self, root, limits):
        super().__init__(root, limits)
        self._managed = None
        self._files = {}

    def managed_bytes(self):
        if self._managed is None:
            self._managed = super().managed_bytes()
        return self._managed

    def track_file(self, path):
        self.managed_bytes()
        path = Path(path)
        if path not in self._files:
            self._files[path] = path.stat().st_size if path.exists() else 0

    def account_file(self, path, size):
        path = Path(path)
        self._managed += size - self._files[path]
        self._files[path] = size

    def refresh_disk(self):
        self._managed = None
        self._files = {}
