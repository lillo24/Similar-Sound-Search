"""C04 owned publication and a single durable pool, shared by every revision."""

import math

from ..evaluation.artifacts import record, write_record
from ..storage import InputError, ResourceError, canonical, contained, digest, read_json

CEILINGS = dict(
    job_seconds=3600,
    workers=256,
    read_audio_seconds=90000,
    feature_windows=4096,
    processed_window_seconds=20000,
    feature_bytes=32 * 1024**2,
    query_jobs=64,
    clips=64,
    clip_bytes=128 * 1024**2,
    metadata_bytes=128 * 1024**2,
    preparation_bytes=64 * 1024**2,
    managed_output_bytes=512 * 1024**2,
)


class Context:
    def __init__(self, root):
        self.root = root.resolve()
        self.cfg = read_json(root / "config/processing.json")
        if (
            self.cfg.get("schema_version") != "c04-processing-1"
            or self.cfg.get("max_sources") != 80
            or self.cfg.get("rows_per_bundle") != 128
            or set(self.cfg.get("policy", {})) != {"max_" + k for k in CEILINGS}
        ):
            raise InputError("C04 configuration: fixed roots, policy and complete pool required")
        for key, cap in CEILINGS.items():
            value = self.cfg["policy"]["max_" + key]
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= cap:
                raise InputError("C04 invalid/increased ceiling: " + key)
        self.protocol = read_json(root / "manifests/processing/protocol.json")
        self.directory = root / "data/runs/processing"
        self.features = root / "data/features/processing"
        self.indexes = root / "data/indexes/processing"
        self.audio = root / "data/audio/processing"
        self.reports = root / "reports/local/c04"

    def pool(self):
        path = self.directory / "pool.json"
        if path.exists():
            value = record(path)
            if (
                value.get("schema_version") != "c04-pool-1"
                or set(value["counts"]) != set(CEILINGS)
                or set(value["ceilings"]) != set(CEILINGS)
            ):
                raise InputError("C04 pool schema/counters differ; never replace the ledger")
        else:
            value = dict(
                schema_version="c04-pool-1",
                counts={k: 0 for k in CEILINGS},
                ceilings={k: self.cfg["policy"]["max_" + k] for k in CEILINGS},
                measured_worker_seconds=0,
                uncertain_worker_seconds=0,
                pending_worker_seconds=0,
                pending_worker_id=None,
                last_settled_worker=0,
            )
            value["counts"]["managed_output_bytes"] = CEILINGS["metadata_bytes"]
        for key in CEILINGS:
            value["ceilings"][key] = min(value["ceilings"][key], self.cfg["policy"]["max_" + key])
            n = value["counts"][key]
            if (
                isinstance(n, bool)
                or not isinstance(n, (int, float))
                or not math.isfinite(n)
                or n < 0
            ):
                raise InputError("C04 pool invalid counter: " + key)
        return {k: v for k, v in value.items() if k != "record_hash"}

    def charge(self, budget, **amounts):
        amounts["preparation_bytes"] = amounts.get("preparation_bytes", 0) + amounts.pop(
            "query_preparation_bytes", 0
        )
        amounts["processed_window_seconds"] = amounts.get(
            "processed_window_seconds", 0
        ) + amounts.pop("pitch_audio_seconds", 0)
        # Include both pool writes and formatting/filesystem overhead before any work.
        value = self.pool()
        if set(amounts) - set(CEILINGS):
            raise InputError("C04 unknown accounting counter")
        amounts["metadata_bytes"] = amounts.get("metadata_bytes", 0) + 8192
        amounts["managed_output_bytes"] = amounts.get("managed_output_bytes", 0) + sum(
            amounts.get(k, 0) for k in ("feature_bytes", "preparation_bytes", "clip_bytes")
        )
        # Persist lowered ceilings even on refusal. No old allowance can increase.
        self.save_pool(budget, value)
        for key, n in amounts.items():
            if (
                isinstance(n, bool)
                or not isinstance(n, (float, int))
                or not math.isfinite(n)
                or n < 0
                or value["counts"][key] + n > value["ceilings"][key]
            ):
                raise ResourceError(
                    "C04 cumulative " + key + " exhausted; retain plan and reservations"
                )
        for key, n in amounts.items():
            value["counts"][key] += n
        self.save_pool(budget, value)
        return value

    def save_pool(self, budget, value):
        write_record(self.directory / "pool.json", value, budget)

    def publish(self, budget, path, value, immutable=False):
        path = contained(path, self.root)
        if not any(path.is_relative_to(p) for p in (self.directory, self.indexes, self.reports)):
            raise InputError("C04 publication outside owned namespace")
        value = {k: v for k, v in value.items() if k != "record_hash"}
        if len(canonical(value)) * 2 + 8192 > 1024**2:
            raise InputError("C04 metadata too large; use compact references")
        if immutable and path.exists():
            old = record(path)
            if {k: v for k, v in old.items() if k != "record_hash"} != value:
                raise InputError("C04 immutable publication conflict: " + str(path))
            return old
        self.charge(budget, metadata_bytes=len(canonical(value)) * 2 + 4096)
        write_record(path, value, budget)
        return record(path)

    def put(self, budget, kind, value):
        value = {k: v for k, v in value.items() if k != "record_hash"}
        path = self.directory / kind / (digest(value) + ".json")
        saved = self.publish(budget, path, value, immutable=True)
        return dict(path=path.relative_to(self.root).as_posix(), record_hash=saved["record_hash"])

    def get(self, ref, kind):
        path = contained(self.root / ref["path"], self.directory / kind)
        value = record(path)
        if value["record_hash"] != ref["record_hash"] or path.stem != value["record_hash"]:
            raise InputError("C04 immutable reference differs: " + str(path))
        return value

    def model(self, budget, desc):
        from ..matchers.models import adapter

        if not hasattr(self, "feature_model"):
            self.feature_model = desc, adapter(budget, "efficientat", desc)[0]
        if self.feature_model[0] != desc:
            raise InputError("C04 worker representation changed")
        return self.feature_model[1]
