"""Fixed B01 accounting/output owner supplied explicitly to shared search primitives."""

from ..evaluation.artifacts import record
from ..search.job import charge_work
from ..storage import InputError, contained, digest, read_json


def configuration(root):
    cfg = read_json(root / "config/events.json")
    if cfg.get("schema_version") != "b01-events-1":
        raise InputError("events configuration: expected b01-events-1")
    expected = {
        "job_seconds",
        "http_attempts",
        "download_bytes",
        "workers",
        "feature_windows",
        "processed_window_seconds",
        "read_audio_seconds",
        "feature_bytes",
        "query_jobs",
        "query_preparation_bytes",
        "clips",
        "clip_bytes",
        "proposal_inputs",
        "proposed_events",
        "preparation_bytes",
        "managed_output_bytes",
        "comparisons",
        "comparison_cases",
        "comparison_queries",
    }
    if set(cfg["policy"]) != {"max_" + k for k in expected}:
        raise InputError("B01 policy: complete finite ceilings required")
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
    caps = {
        "feature_windows": 4096,
        "query_jobs": 16,
        "read_audio_seconds": 90000,
        "feature_bytes": 64 * 1024**2,
        "clips": 128,
        "clip_bytes": 128 * 1024**2,
    }
    if any(cfg["policy"]["max_" + key] > v for key, v in caps.items()):
        raise InputError("B01 outer feature/query/audio/clip ceilings exceeded")
    for key in (
        "frame_milliseconds",
        "hop_milliseconds",
        "attack_lead_milliseconds",
        "release_hold_milliseconds",
        "minimum_gap_milliseconds",
        "minimum_event_milliseconds",
        "maximum_event_milliseconds",
        "max_region_seconds",
        "max_events_per_input",
        "max_selected_events",
    ):
        value = cfg.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= 8000:
            raise InputError("events configuration: invalid " + key)
    if (
        cfg["max_region_seconds"] > 30
        or cfg["max_events_per_input"] > 32
        or cfg["max_selected_events"] > 3
        or cfg["hop_milliseconds"] > cfg["frame_milliseconds"]
        or cfg["minimum_event_milliseconds"] > cfg["maximum_event_milliseconds"]
    ):
        raise InputError("events configuration: conservative geometry exceeded")
    for key in (
        "edge_energy_ratio",
        "novelty_peak_ratio",
        "absolute_rms_floor",
        "comparison_tolerance",
    ):
        value = cfg.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < 1:
            raise InputError("events configuration: invalid ratio " + key)
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
        if (
            not isinstance(binding, dict)
            or binding.get("version") != "b01-handoff-1"
            or not isinstance(binding.get("events"), list)
            or not binding["events"]
            or binding["events"] != sorted(set(binding["events"]))
        ):
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
