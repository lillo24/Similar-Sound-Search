"""D01-owned B03 recipe/library adapter; historical revisions remain read-only."""

from ..evaluation.artifacts import record
from ..queries import assets, library, materialization
from ..queries.context import Context as QueryContext
from ..retrieval.context import load_query
from ..storage import InputError, digest


class QueryOwner(QueryContext):
    def __init__(self, owner):
        super().__init__(owner.root)
        self.owner = owner
        self.directory = owner.directory / "library"
        self.queries = self.directory / "materialized"
        self.feature_root = owner.features / "queries"
        self.reports = owner.reports

    def charge(self, *args, **kwargs):
        # Shared A02/query/array writers publish their own receipts directly. Prepay
        # those bounded serialized records as metadata as well as their output bytes.
        if kwargs.get("query_preparation_bytes"):
            kwargs["metadata_bytes"] = kwargs.get("metadata_bytes", 0) + 65536
        if kwargs.get("feature_windows"):
            kwargs["metadata_bytes"] = (
                kwargs.get("metadata_bytes", 0) + 65536 * kwargs["feature_windows"]
            )
        return self.owner.charge(*args, **kwargs)

    def publish(self, *args, **kwargs):
        return self.owner.publish(*args, **kwargs)


def save(budget, owner, spec):
    if set(spec) - {"examples", "label", "query_id", "expected"}:
        raise InputError("D01 query: unsupported setting; original audio and pitch off only")
    view = QueryOwner(owner)
    value = dict(schema_version="b03-query-input-1", examples=spec["examples"], pitch=library.OFF)
    result = library.save(
        budget, view, value, spec["label"], spec.get("query_id"), spec.get("expected")
    )
    return result


def rename(budget, owner, spec):
    if set(spec) != {"query_id", "expected", "label"}:
        raise InputError("D01 rename requires exact query, expected name version and label")
    return library.change_name(
        budget, QueryOwner(owner), spec["query_id"], spec["expected"], spec["label"]
    )


def load(budget, owner, selection):
    if selection.get("historical"):
        if selection != dict(historical=True, **owner.protocol["delivery"]):
            raise InputError("D01 historical query requires the exact original saved revision")
        rev, saved, q, matrix = load_query(budget, owner)
        return dict(
            query=q,
            feature_hash=q["feature_hash"],
            revision=rev["revision_id"],
            materialization=saved["materialization_id"],
            new_encodes=0,
            saved_input=dict(
                kind="saved",
                revision=rev["revision_id"],
                materialization=saved["materialization_id"],
            ),
        ), matrix
    if set(selection) - {"revision", "materialization", "historical"}:
        raise InputError("D01 query selection requires immutable revision/materialization")
    view = QueryOwner(owner)
    rev = library.revision(view, selection["revision"])
    if rev["recipe"]["pitch"] != library.OFF or any(
        e["kind"] != "asset" for e in rev["recipe"]["examples"]
    ):
        raise InputError("D01 unsupported pitch/transform; explicitly select original audio")
    if selection.get("materialization") is None:
        owner.charge(budget, metadata_bytes=256 * 1024)
        materialization.materialize(budget, view, rev)
    saved, q, matrix = materialization.load(budget, view, rev, selection.get("materialization"))
    return dict(
        query=q,
        feature_hash=q["feature_hash"],
        revision=rev["revision_id"],
        materialization=saved["materialization_id"],
        new_encodes=view.feature_stats.get("new", 0),
    ), matrix


def register(budget, owner, path, label):
    result = assets.register(budget, QueryOwner(owner), path)
    key = result["asset_id"]
    owner.publish(
        budget,
        owner.directory / "reference-labels" / (key + ".json"),
        dict(asset_id=key, label=library.label(label)),
    )
    from .media import overview

    result["overview"] = overview(budget, owner, key)
    owner.publish(
        budget,
        owner.directory / "reference-overviews" / (key + ".json"),
        dict(asset_id=key, overview=result["overview"]),
        immutable=True,
    )
    return result


def copy_historical(budget, owner, revision):
    """Explicit import of existing registered originals; no B03 head/budget changes."""
    from ..retrieval.context import QueryView
    from .media import overview

    old, target = QueryView(owner), QueryOwner(owner)
    rev = library.revision(old, revision)
    if rev["recipe"]["pitch"] != library.OFF or any(
        e["kind"] != "asset" for e in rev["recipe"]["examples"]
    ):
        raise InputError("D01 historical edit import supports original/pitch-off revisions only")
    refs = []
    for key in rev["recipe"]["assets"]:
        assets.read_asset(budget, old, key)
        value = record(assets.asset_path(old, key))
        bound = assets.read_binding(old, key)
        owner.publish(budget, assets.asset_path(target, key), value, immutable=True)
        owner.publish(budget, assets.binding_path(target, key), bound, immutable=True)
        wave = overview(budget, owner, key)
        owner.publish(
            budget,
            owner.directory / "reference-overviews" / (key + ".json"),
            dict(asset_id=key, overview=wave),
            immutable=True,
        )
        refs.append(dict(asset_id=key, overview=wave))
    return dict(revision=revision, recipe=rev["recipe"], references=refs)


def inventory(owner):
    """Metadata only. Availability is explicit and no inference is dispatched."""
    view = QueryOwner(owner)
    names = [record(p) for p in sorted((view.directory / "names").glob("*.json"))][:64]
    references = []
    for path in sorted((view.directory / "assets").glob("*.json"))[:64]:
        value = record(path)
        key = value["asset_id"]
        label = owner.directory / "reference-labels" / (key + ".json")
        references.append(
            dict(
                asset_id=key,
                audio=value["identity"]["audio"],
                label=record(label)["label"] if label.exists() else "Saved reference",
            )
        )
        wave = owner.directory / "reference-overviews" / (key + ".json")
        if wave.exists():
            references[-1]["overview"] = record(wave)["overview"]
    historical = dict(
        label="Loulou 3:38–4:00 · original mixture",
        historical=True,
        **owner.protocol["delivery"],
        event=[9613800, 10584000],
        context=[9569700, 10628100],
        rate=44100,
        provenance="Identity, rights, version/master alignment and intended layer unverified",
    )
    try:
        from ..retrieval.context import QueryView

        old = QueryView(owner)
        rev = library.revision(old, historical["revision"])
        historical["recipe"] = rev["recipe"]
        historical["available"] = all(
            (owner.root / assets.read_binding(old, k)["path"]).is_file()
            for k in rev["recipe"]["assets"]
        )
        asset_id = next(iter(rev["recipe"]["assets"]))
        historical["asset_id"] = asset_id
        wave = owner.directory / "reference-overviews" / (asset_id + ".json")
        historical["overview"] = record(wave)["overview"] if wave.exists() else None
        historical["preview_url"] = (
            "/historical/media/b91a8bffd1e5170651feaa874190096201a2df647833d41a621a5e09ef07bf79.wav"
        )
    except (InputError, OSError, KeyError) as exc:
        historical.update(available=False, error=str(exc))
    return dict(
        names=names,
        references=references,
        historical=historical,
        unavailable=dict(
            pitch="No validated D01 pitch route",
            transform="No D01 transform route",
            automatic_selection="Select native intervals explicitly",
            new_query_refinement="C03 belongs only to its exact historical chain",
        ),
    )


def exact_revision(owner, key):
    view = QueryOwner(owner)
    value = library.revision(view, key)
    state = materialization.state_path(view, key)
    return dict(
        revision=value,
        materialization=materialization.receipt(view, value)["materialization_id"]
        if state.exists() and record(state).get("state") == "ready"
        else None,
        version=digest(value),
    )
