"""Fixed B01 accounting/output owner supplied explicitly to shared search primitives."""

from ..evaluation.artifacts import record
from ..search.job import charge_work
from ..storage import InputError, contained, digest, read_json


def configuration(root):
    cfg = read_json(root / "config/events.json")
    if cfg.get("schema_version") != "b01-events-1":
        raise InputError("events configuration: expected b01-events-1")
    for key, value in cfg["policy"].items():
        if (
            not key.startswith("max_")
            or isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise InputError("B01 requires complete nonnegative integer ceilings: " + key)
    if cfg["policy"]["max_job_seconds"] > 3600 or cfg["policy"]["max_workers"] > 256:
        raise InputError("B01 outer worker ceilings exceeded")
    if cfg["policy"]["max_download_bytes"] or cfg["policy"]["max_http_attempts"]:
        raise InputError("B01 is offline and cannot acquire inputs")
    return cfg


class Context:
    """There is one B01 namespace; callers cannot choose a job or redirect A06 writes."""

    def __init__(self, root, receipt=None):
        self.root = root.resolve()
        self.cfg = configuration(self.root)
        self.directory = self.root / "data/runs/events"
        self.queries = self.directory / "queries"
        self.results = self.directory / "results"
        self.progress = self.directory / "rank-progress"
        self.reports = self.root / "reports/local/b01"
        self.receipt_path = receipt

    def charge(self, budget, **amounts):
        output = sum(
            amounts.get(k, 0)
            for k in ("feature_bytes", "query_preparation_bytes", "preparation_bytes", "clip_bytes")
        )
        if output:
            amounts["managed_output_bytes"] = amounts.get("managed_output_bytes", 0) + output
        return charge_work(
            budget, self.directory, self.cfg["policy"], "b01-work-1", "B01", **amounts
        )

    def query_binding(self, spec):
        binding = spec.get("b01_binding")
        if not isinstance(binding, dict):
            raise InputError("B01 query requires the explicit event/manual selection handoff")
        return {
            "version": "b01-query-consumer-1",
            "configuration": digest(self.cfg),
            "selection": binding,
        }

    def validate_query(self, value):
        binding = value["identity"].get("consumer", {})
        if binding.get("version") != "b01-query-consumer-1" or binding.get(
            "configuration"
        ) != digest(self.cfg):
            raise InputError("B01 query: event configuration/consumer changed")

    def validate_index(self, budget, path, value, desc, cfg):
        from .compatibility import validate_receipt

        if self.receipt_path is None:
            raise InputError(
                "B01 rank requires --receipt from events compatibility; no rebuild/fallback"
            )
        receipt = record(contained(self.receipt_path, self.directory / "compatibility"))
        validate_receipt(budget, path, value, desc, cfg, receipt)
        self.receipt = receipt
        return True

    def result_binding(self):
        return {"version": "b01-result-consumer-1", "receipt": self.receipt["record_hash"]}
