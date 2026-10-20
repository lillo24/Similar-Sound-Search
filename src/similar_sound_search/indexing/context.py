"""Fixed C01 policy, publication boundary, model lifetime and read-only query view."""

from ..evaluation.artifacts import record, write_record
from ..queries.context import Context as QueryContext
from ..search.job import charge_work
from ..storage import InputError, canonical, contained, digest, read_json

CEILINGS = {
    "job_seconds": 7200,
    "workers": 512,
    "http_attempts": 0,
    "download_bytes": 0,
    "read_audio_seconds": 180000,
    "feature_windows": 26000,
    "processed_window_seconds": 65000,
    "feature_bytes": 128 * 1024**2,
    "query_jobs": 16,
    "clips": 64,
    "clip_bytes": 128 * 1024**2,
    "metadata_bytes": 32 * 1024**2,
    "query_preparation_bytes": 32 * 1024**2,
    "preparation_bytes": 32 * 1024**2,
    "managed_output_bytes": 512 * 1024**2,
    "pilot_windows": 2048,
    "comparison_batches": 1,
    "case_bank_queries": 48,
    "real_regions": 4,
    "processing_inputs": 32,
    "separator_input_seconds": 240,
    "component_windows": 512,
}


def configuration(root):
    cfg = read_json(root / "config/indexing.json")
    if cfg.get("schema_version") != "c01-indexing-1":
        raise InputError("C01 configuration: expected c01-indexing-1")
    if cfg.get("default") != "legacy-original" or cfg.get("results") != 10:
        raise InputError("C01 configuration: original default and ten results required")
    if (
        isinstance(cfg.get("rows_per_shard"), bool)
        or not isinstance(cfg.get("rows_per_shard"), int)
        or not 1 <= cfg["rows_per_shard"] <= 128
    ):
        raise InputError("C01 configuration: bounded 1..128 rows required")
    expected = {"max_" + k for k in CEILINGS}
    if set(cfg.get("policy", {})) != expected:
        raise InputError("C01 configuration: complete fixed finite policy required")
    for key, cap in CEILINGS.items():
        value = cfg["policy"]["max_" + key]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= cap:
            raise InputError("C01 configuration: invalid/increased ceiling: " + key)
    for grid in [*cfg["candidates"].values(), cfg["component_grid"]]:
        if (
            set(grid) != {"window_milliseconds", "hop_milliseconds"}
            or any(
                isinstance(v, bool) or not isinstance(v, int) or not 0 < v <= 4800
                for v in grid.values()
            )
            or grid["hop_milliseconds"] > grid["window_milliseconds"]
        ):
            raise InputError("C01 configuration: invalid native grid")
    if set(cfg["candidates"]) != {"short", "long"}:
        raise InputError("C01 configuration: only the two declared duration candidates")
    return cfg


class Context:
    def __init__(self, root, receipt=None):
        self.root = root.resolve()
        self.cfg = configuration(root)
        self.protocol = read_json(root / "manifests/indexing/protocol.json")
        self.directory = root / "data/runs/indexing"
        self.indexes = root / "data/indexes/c01"
        self.features = root / "data/features/indexing"
        self.reports = root / "reports/local/c01"
        self.receipt_path = receipt

    def charge(self, budget, **amounts):
        amounts["managed_output_bytes"] = amounts.get("managed_output_bytes", 0) + sum(
            amounts.get(k, 0)
            for k in ("feature_bytes", "preparation_bytes", "query_preparation_bytes", "clip_bytes")
        )
        return charge_work(
            budget, self.directory, self.cfg["policy"], "c01-work-1", "C01", **amounts
        )

    def publish(self, budget, path, value, immutable=False):
        path = contained(path, self.root)
        if not any(path.is_relative_to(p) for p in (self.directory, self.indexes, self.reports)):
            raise InputError("C01 publication outside owned roots")
        if immutable and path.exists():
            if {k: v for k, v in record(path).items() if k != "record_hash"} != value:
                raise InputError(
                    "C01 immutable record conflicts: " + path.relative_to(self.root).as_posix()
                )
            return record(path)
        self.charge(budget, metadata_bytes=len(canonical(value)) * 2 + 4096)
        write_record(path, value, budget)
        return record(path)

    def model(self, budget, desc):
        from ..matchers.models import adapter

        if not hasattr(self, "feature_model"):
            self.feature_model = (desc, adapter(budget, "efficientat", desc)[0])
        if self.feature_model[0] != desc:
            raise InputError("C01 worker representation changed")
        return self.feature_model[1]


class QueryView(QueryContext):
    """Existing B03 artifacts are read-only; every validation debit belongs to C01."""

    def __init__(self, owner):
        super().__init__(owner.root)
        self.owner = owner

    def charge(self, budget, **amounts):
        return self.owner.charge(budget, **amounts)

    def publish(self, *args, **kwargs):
        raise InputError(
            "C01 read-only B03 view: use indexing derive-query for new materialization"
        )

    def resolve_example(self, budget, item):
        from ..queries import assets

        # The shared resolver may create a context. Refuse that write before it
        # happens; cached feature/audio validation never authorizes old-root writes.
        if item["kind"] == "asset":
            identity = record(assets.asset_path(self, item["asset_id"]))["identity"]
            binding = assets.read_binding(self, item["asset_id"])
            if not binding["parent_record"]:
                path = self.directory / "contexts" / (digest(identity["context"]) + ".json")
                if not path.exists():
                    raise InputError(
                        "C01 B03 context missing; use explicit derive-query: " + str(path)
                    )
        return super().resolve_example(budget, item)


class DerivedQueryContext(QueryContext):
    """Same validated B03 recipe, with all new artifacts/features owned by C01."""

    def __init__(self, owner):
        super().__init__(owner.root)
        self.owner = owner
        self.directory = owner.directory / "query-derived"
        self.queries = self.directory / "materialized"
        self.reports = owner.reports
        self.feature_root = owner.features / "queries"

    def charge(self, budget, **amounts):
        # The unchanged materializer records pitch metadata even with scoring off.
        # Charge its estimator input within C01's bounded audio-processing cap.
        amounts["processed_window_seconds"] = amounts.get(
            "processed_window_seconds", 0
        ) + amounts.pop("pitch_audio_seconds", 0)
        return self.owner.charge(budget, **amounts)

    def publish(self, budget, path, value, immutable=False):
        return self.owner.publish(budget, path, value, immutable)

    @property
    def feature_model(self):
        if not hasattr(self.owner, "feature_model"):
            raise AttributeError("not initialized")
        return self.owner.feature_model

    @feature_model.setter
    def feature_model(self, value):
        self.owner.feature_model = value
