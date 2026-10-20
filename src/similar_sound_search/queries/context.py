"""One B03 accounting namespace and explicit read-only search/transform adapters."""

from ..evaluation.artifacts import record, write_record
from ..events.compatibility import validate_receipt
from ..search.job import charge_work
from ..separation.context import Context as SeparationContext
from ..storage import InputError, contained, digest
from .contracts import configuration


class TransformContext(SeparationContext):
    """Use exact B02 validators/settings; every operation is charged only to B03."""

    def __init__(self, owner, historical=False):
        super().__init__(owner.root)
        self.owner = owner
        if not historical:
            self.directory = owner.directory
        self.reports = owner.reports

    def charge(self, budget, **amounts):
        return self.owner.charge(budget, **amounts)


class Context:
    def __init__(self, root, receipt=None):
        self.root = root.resolve()
        self.cfg = configuration(self.root)
        self.directory = self.root / "data/runs/queries"
        self.queries = self.directory / "materialized"
        self.results = self.directory / "timbre-results"
        self.progress = self.directory / "rank-progress"
        self.reports = self.root / "reports/local/b03"
        self.receipt_path = receipt
        self.feature_stats = {}

    def charge(self, budget, **amounts):
        amounts["managed_output_bytes"] = amounts.get("managed_output_bytes", 0) + sum(
            amounts.get(k, 0)
            for k in ("feature_bytes", "preparation_bytes", "query_preparation_bytes", "clip_bytes")
        )
        return charge_work(
            budget, self.directory, self.cfg["policy"], "b03-work-1", "B03", **amounts
        )

    def publish(self, budget, path, value, immutable=False):
        path = contained(path, self.directory)
        if immutable and path.exists():
            if {k: v for k, v in record(path).items() if k != "record_hash"} != value:
                raise InputError(
                    "B03 immutable record conflicts: " + str(path.relative_to(self.root))
                )
            return
        from ..storage import canonical

        self.charge(budget, metadata_bytes=len(canonical(value)) * 2 + 4096)
        write_record(path, value, budget)

    def resolve_example(self, budget, item):
        from .assets import resolve_example

        return resolve_example(budget, self, item)

    def query_binding(self, spec):
        if spec.get("b03_binding") != {
            "version": "b03-materialization-1",
            "examples": spec["examples"],
        }:
            raise InputError("B03 materialization: explicit canonical recipe binding required")
        from .assets import read_binding

        keys = {
            v["asset_id"] if v["kind"] == "asset" else digest(v["transform"])
            for v in spec["examples"]
        }
        return {
            "version": "b03-query-consumer-1",
            "examples": spec["examples"],
            "local_bindings": {k: read_binding(self, k) for k in sorted(keys)},
        }

    def validate_query(self, value):
        binding = value["identity"].get("consumer", {})
        if binding.get("version") != "b03-query-consumer-1" or not binding.get("examples"):
            raise InputError("B03 materialized query: missing recipe binding")

    def validate_query_audio(self, budget, value):
        self.validate_query(value)
        groups = set()
        self.binding_snapshots = value["identity"]["consumer"]["local_bindings"]
        try:
            for item in value["identity"]["consumer"]["examples"]:
                _, ancestry = self.resolve_example(budget, item)
                groups.update(ancestry)
        finally:
            self.binding_snapshots = None
        if not groups.issubset(value["identity"]["excluded_groups"]):
            raise InputError("B03 materialized query: lost source/cue ancestry")

    def estimate_pitch(self, budget, samples, rate):
        from .pitch import cached_estimate

        return cached_estimate(budget, self, samples, rate)

    def encode_examples(self, budget, examples, desc):
        from .features import collection

        return collection(budget, self, examples, desc)

    def validate_index(self, budget, path, value, desc, cfg):
        if self.receipt_path is None:
            raise InputError("B03 search requires --receipt from queries compatibility")
        receipt = record(contained(self.receipt_path, self.directory / "compatibility"))
        validate_receipt(budget, path, value, desc, cfg, receipt)
        self.receipt = receipt
        return True

    def result_binding(self):
        return {"version": "b03-timbre-consumer-1", "receipt": self.receipt["record_hash"]}

    def save_winners(self, budget, identity, query, best, scored):
        from ..search.ranking import timbre_key

        value = {
            "schema_version": "b03-winners-1",
            "identity": identity,
            "query_hash": query["record_hash"],
            "winners": sorted(best.values(), key=timbre_key),
            "eligible_groups": len(best),
            "scored_windows": scored,
            "complete": True,
            "selection": "one timbre-best passage per eligible original group; before top ten",
        }
        self.publish(
            budget, self.directory / "winners" / (digest(identity) + ".json"), value, immutable=True
        )
        lookup = {
            "index_id": identity["index_id"],
            "query_id": query["query_id"],
            "receipt": self.receipt["record_hash"],
        }
        self.publish(
            budget,
            self.directory / "winner-bindings" / (digest(lookup) + ".json"),
            {
                "identity": lookup,
                "winners": "data/runs/queries/winners/" + digest(identity) + ".json",
            },
            immutable=True,
        )
