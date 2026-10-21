"""One finite C02 allowance, owned publication and explicit query adapters."""

from ..evaluation.artifacts import record, write_record
from ..indexing.context import DerivedQueryContext as HistoricalDerivative
from ..indexing.context import QueryView as HistoricalQueryView
from ..search.job import charge_work
from ..storage import InputError, canonical, contained, digest, read_json

CEILINGS = dict(
    job_seconds=3600,
    workers=256,
    http_attempts=0,
    download_bytes=0,
    read_audio_seconds=120000,
    feature_windows=2048,
    processed_window_seconds=12000,
    feature_bytes=8 * 1024**2,
    query_jobs=64,
    clips=64,
    clip_bytes=96 * 1024**2,
    metadata_bytes=64 * 1024**2,
    query_preparation_bytes=64 * 1024**2,
    preparation_bytes=64 * 1024**2,
    managed_output_bytes=384 * 1024**2,
    comparison_batches=1,
    case_policy_evaluations=48,
)


def configuration(root):
    cfg = read_json(root / "config/retrieval.json")
    fixed = dict(
        shortlist=20,
        display=10,
        raw_support_cap=16,
        passages_per_track=3,
        rrf_constant=60,
        overlap_fraction=0.5,
        max_span_seconds=8,
        default="legacy-mean",
        schema_version="c02-retrieval-1",
    )
    if set(cfg) != {*fixed, "policy"} or any(cfg[k] != v for k, v in fixed.items()):
        raise InputError("C02 configuration: expected fixed declared retrieval policy")
    if set(cfg["policy"]) != {"max_" + k for k in CEILINGS}:
        raise InputError("C02 configuration: complete lifetime ceilings required")
    for k, cap in CEILINGS.items():
        v = cfg["policy"]["max_" + k]
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= cap:
            raise InputError("C02 configuration: invalid/increased ceiling: " + k)
    return cfg


class Context:
    def __init__(self, root):
        self.root = root.resolve()
        self.cfg = configuration(self.root)
        self.protocol = read_json(self.root / "manifests/retrieval/protocol.json")
        self.directory = self.root / "data/runs/retrieval"
        self.features = self.root / "data/features/retrieval"
        self.reports = self.root / "reports/local/c02"

    def charge(self, budget, **amounts):
        amounts["managed_output_bytes"] = amounts.get("managed_output_bytes", 0) + sum(
            amounts.get(k, 0)
            for k in ("feature_bytes", "query_preparation_bytes", "preparation_bytes", "clip_bytes")
        )
        return charge_work(
            budget, self.directory, self.cfg["policy"], "c02-work-1", "C02", **amounts
        )

    def publish(self, budget, path, value, immutable=False):
        path = contained(path, self.root)
        if not any(path.is_relative_to(p) for p in (self.directory, self.reports)):
            raise InputError("C02 publication outside owned namespace")
        if immutable and path.exists():
            old = record(path)
            if {k: v for k, v in old.items() if k != "record_hash"} != value:
                raise InputError("C02 immutable record conflicts: " + str(path))
            return old
        if len(canonical(value)) + 1024 > 1024**2:
            raise InputError("C02 metadata exceeds 1 MiB; publish compact references")
        self.charge(budget, metadata_bytes=len(canonical(value)) * 2 + 4096)
        write_record(path, value, budget)
        return record(path)

    def put(self, budget, kind, value):
        value = {k: v for k, v in value.items() if k != "record_hash"}
        path = self.directory / kind / (digest(value) + ".json")
        saved = self.publish(budget, path, value, immutable=True)
        return {"path": path.relative_to(self.root).as_posix(), "record_hash": saved["record_hash"]}

    def get(self, ref, kind):
        path = contained(self.root / ref["path"], self.directory / kind)
        value = record(path)
        if value["record_hash"] != ref["record_hash"] or path.stem != value["record_hash"]:
            raise InputError("C02 immutable reference changed: " + str(path))
        return value

    def model(self, budget, desc):
        from ..matchers.models import adapter

        if not hasattr(self, "feature_model"):
            self.feature_model = (desc, adapter(budget, "efficientat", desc)[0])
        if self.feature_model[0] != desc:
            raise InputError("C02 worker representation changed")
        return self.feature_model[1]


class QueryView(HistoricalQueryView):
    """B03 roots stay read-only; validation charges the explicit C02 owner."""

    def publish(self, *args, **kwargs):
        raise InputError("C02 read-only B03 view: use retrieval derive-query explicitly")

    def resolve_example(self, budget, item):
        from ..queries import assets
        from ..queries.context import Context as QueryContext

        if item["kind"] == "asset":
            identity = record(assets.asset_path(self, item["asset_id"]))["identity"]
            binding = assets.read_binding(self, item["asset_id"])
            if not binding["parent_record"]:
                target = self.directory / "contexts" / (digest(identity["context"]) + ".json")
                if not target.exists():
                    raise InputError("C02 B03 context missing; use retrieval derive-query")
        return QueryContext.resolve_example(self, budget, item)


class DerivedQueryContext(HistoricalDerivative):
    """Inherited recipe validators, with all new roots beneath C02."""

    def __init__(self, owner):
        super().__init__(owner)
        self.directory = owner.directory / "query-derived"
        self.queries = self.directory / "materialized"


def load_query(budget, owner, revision=None, materialization_id=None, derived=False):
    from ..queries import library, materialization

    cfg = owner.protocol["delivery"]
    view = DerivedQueryContext(owner) if derived else QueryView(owner)
    rev = library.revision(view, revision or cfg["revision"])
    exact = materialization_id or (
        cfg["materialization"] if not derived and rev["revision_id"] == cfg["revision"] else None
    )
    try:
        saved, query, features = materialization.load(budget, view, rev, exact)
    except FileNotFoundError as exc:
        raise InputError(
            "C02 query dependency missing; use explicit retrieval derive-query"
        ) from exc
    return rev, saved, query, features


def derive_query(budget, owner, revision):
    from ..queries import assets, library, materialization

    old, target = QueryView(owner), DerivedQueryContext(owner)
    value = library.revision(old, revision)
    dependencies = library.inventory(value["recipe"])
    bindings = {}
    for key in dependencies:
        bound = assets.read_binding(old, key)
        bindings[key] = {k: bound[k] for k in ("path", "parent_record") if k in bound}
    export = {
        "schema_version": "b03-query-export-1",
        "revision_id": revision,
        "recipe": value["recipe"],
        "dependencies": dependencies,
        "availability": "explicit C02-owned derivative; every source/cue binding must validate",
    }
    exported = owner.put(budget, "query-derived/imports", export)
    library.import_recipe(budget, target, owner.get(exported, "query-derived/imports"), bindings)
    owner.charge(budget, query_jobs=1)
    return materialization.materialize(budget, target, library.revision(target, revision))
