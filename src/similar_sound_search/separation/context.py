"""Fixed B02 output/accounting owner and validated derivative ancestry extension."""

from ..evaluation.artifacts import record
from ..events.compatibility import validate_receipt
from ..search.job import charge_work
from ..storage import InputError, contained, digest, read_json

CAPS = {
    "job_seconds": 3600,
    "workers": 256,
    "http_attempts": 0,
    "download_bytes": 0,
    "separator_input_seconds": 1200,
    "processing_inputs": 192,
    "feature_windows": 4096,
    "processed_window_seconds": 12000,
    "read_audio_seconds": 90000,
    "feature_bytes": 64 * 1024**2,
    "query_jobs": 16,
    "query_preparation_bytes": 64 * 1024**2,
    "preparation_bytes": 256 * 1024**2,
    "clips": 128,
    "clip_bytes": 128 * 1024**2,
    "managed_output_bytes": 512 * 1024**2,
    "comparisons": 1,
    "comparison_cases": 24,
    "comparison_queries": 192,
}


def configuration(root):
    cfg = read_json(root / "config/separation.json")
    if cfg.get("schema_version") != "b02-separation-1":
        raise InputError("B02 configuration: expected b02-separation-1")
    if set(cfg["policy"]) != {"max_" + k for k in CAPS}:
        raise InputError("B02 policy: complete finite ceilings required")
    for key, cap in CAPS.items():
        value = cfg["policy"]["max_" + key]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= cap:
            raise InputError("B02 outer ceiling invalid: " + key)
    expected = {
        "fft_frames": 1024,
        "hop_frames": 256,
        "median_frames": 17,
        "cue_templates": 4,
        "background_templates": 8,
        "iterations": 25,
        "max_region_seconds": 12,
        "max_cue_seconds": 4,
        "max_components": 2,
        "max_chunks": 1,
        "max_temporary_bytes": 128 * 1024**2,
        "broad_route": "harmonic",
        "default_route": "original",
        "method_version": "b02-dsp-1",
    }
    if any(cfg.get(k) != v for k, v in expected.items()):
        raise InputError("B02 fixed DSP configuration differs; declare a new experiment")
    return cfg


class Context:
    def __init__(self, root, receipt=None):
        self.root = root.resolve()
        self.cfg = configuration(self.root)
        self.directory = self.root / "data/runs/separation"
        self.queries = self.directory / "queries"
        self.results = self.directory / "results"
        self.progress = self.directory / "rank-progress"
        self.reports = self.root / "reports/local/b02"
        self.receipt_path = receipt

    def charge(self, budget, **amounts):
        output = sum(
            amounts.get(k, 0)
            for k in ("feature_bytes", "query_preparation_bytes", "preparation_bytes", "clip_bytes")
        )
        amounts["managed_output_bytes"] = amounts.get("managed_output_bytes", 0) + output
        return charge_work(
            budget, self.directory, self.cfg["policy"], "b02-work-1", "B02", **amounts
        )

    def resolve_example(self, budget, item):
        from .artifacts import validate

        if set(item) != {"b02_record", "component"}:
            raise InputError("B02 query example requires transformation receipt and component only")
        value = validate(budget, self.root / item["b02_record"], self)
        component = value["outputs"].get(item["component"])
        if component is None or component["state"] != "ok":
            raise InputError(
                "B02 query: absent/near-silent component; no implicit original fallback"
            )
        from ..events.selection import frame_seconds

        first, last = value["identity"]["spec"]["event"]
        region = value["identity"]["spec"]["region"]
        start, end = frame_seconds(
            first - region[0], last - region[0], component["audio"]["sample_rate_hz"]
        )
        return {"path": component["path"], "start": start, "end": end}, value["excluded_groups"]

    def query_binding(self, spec):
        if spec.get("schema_version") != "a06-query-input-1" or not spec.get("examples"):
            raise InputError("B02 query: explicit transformation examples required")
        return {
            "version": "b02-query-consumer-1",
            "configuration": digest(self.cfg),
            "examples": [v for _, v in sorted({digest(v): v for v in spec["examples"]}.items())],
        }

    def validate_query(self, value):
        binding = value["identity"].get("consumer", {})
        if binding.get("version") != "b02-query-consumer-1" or binding.get(
            "configuration"
        ) != digest(self.cfg):
            raise InputError("B02 query: stale consumer/configuration")

    def validate_query_audio(self, budget, value):
        self.validate_query(value)
        excluded = set()
        for item in value["identity"]["consumer"]["examples"]:
            _, groups = self.resolve_example(budget, item)
            excluded.update(groups)
        if not excluded.issubset(value["identity"]["excluded_groups"]):
            raise InputError("B02 query: original/cue exclusions lost")

    def validate_index(self, budget, path, value, desc, cfg):
        if self.receipt_path is None:
            raise InputError("B02 rank requires --receipt from separation compatibility")
        receipt = record(contained(self.receipt_path, self.directory / "compatibility"))
        validate_receipt(budget, path, value, desc, cfg, receipt)
        self.receipt = receipt
        return True

    def result_binding(self):
        return {"version": "b02-result-consumer-1", "receipt": self.receipt["record_hash"]}
