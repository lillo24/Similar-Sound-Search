"""C03 publication/accounting, separate from historical C02 configuration and reads."""

from ..retrieval.context import Context as RetrievalContext
from ..storage import InputError, read_json

CEILINGS = dict(
    job_seconds=3600,
    workers=256,
    http_attempts=0,
    download_bytes=0,
    read_audio_seconds=90000,
    feature_windows=4096,
    processed_window_seconds=20000,
    feature_bytes=32 * 1024**2,
    query_jobs=64,
    clips=64,
    clip_bytes=128 * 1024**2,
    metadata_bytes=96 * 1024**2,
    query_preparation_bytes=64 * 1024**2,
    preparation_bytes=128 * 1024**2,
    managed_output_bytes=512 * 1024**2,
    comparison_batches=1,
    case_policy_evaluations=48,
    processing_inputs=32,
    separator_input_seconds=240,
    real_regions=4,
)


class Context(RetrievalContext):
    def __init__(self, root):
        self.root = root.resolve()
        self.cfg = read_json(root / "config/refinement.json")
        fixed = dict(
            schema_version="c03-refinement-1",
            anchors_per_group=2,
            offset_milliseconds=list(range(-500, 501, 125)),
            selection="preserve-c02-order-original-control-tie",
            extraction="omitted",
        )
        if set(self.cfg) != {*fixed, "policy"} or any(self.cfg[k] != v for k, v in fixed.items()):
            raise InputError("C03 fixed policy differs")
        if set(self.cfg["policy"]) != {"max_" + k for k in CEILINGS}:
            raise InputError("C03 complete finite allowance required")
        for k, cap in CEILINGS.items():
            v = self.cfg["policy"]["max_" + k]
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= cap:
                raise InputError("C03 invalid/increased ceiling: " + k)
        self.protocol = read_json(root / "manifests/refinement/protocol.json")
        self.directory = root / "data/runs/refinement"
        self.features = root / "data/features/refinement"
        self.reports = root / "reports/local/c03"

    def charge(self, budget, **amounts):
        from ..search.job import charge_work

        amounts["managed_output_bytes"] = amounts.get("managed_output_bytes", 0) + sum(
            amounts.get(k, 0)
            for k in ("feature_bytes", "query_preparation_bytes", "preparation_bytes", "clip_bytes")
        )
        return charge_work(
            budget, self.directory, self.cfg["policy"], "c03-work-1", "C03", **amounts
        )


class Historical(RetrievalContext):
    """C02 paths/configuration retained; no C02 publication or allowance use."""

    def __init__(self, owner):
        super().__init__(owner.root)
        self.owner = owner

    def charge(self, budget, **amounts):
        return self.owner.charge(budget, **amounts)

    def publish(self, *args, **kwargs):
        raise InputError("C03 historical C02 view is read-only")
