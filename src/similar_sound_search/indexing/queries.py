"""Pinned saved-query consumption and explicit owned materialization derivatives."""

from ..evaluation.artifacts import record
from ..queries import assets, library, materialization
from ..storage import InputError, digest
from .context import DerivedQueryContext, QueryView


def load(budget, owner, revision_id=None, materialization_id=None, derived=False):
    delivery = owner.protocol["delivery"]
    revision_id = revision_id or delivery["revision"]
    view = DerivedQueryContext(owner) if derived else QueryView(owner)
    revision = library.revision(view, revision_id)
    # A stored pitch preference does not change the verification bank: the query
    # example features/exclusions remain exact and C01 always uses pitch zero.
    exact = materialization_id or (
        delivery["materialization"] if revision_id == delivery["revision"] and not derived else None
    )
    try:
        saved, value, array = materialization.load(budget, view, revision, exact)
    except FileNotFoundError as exc:
        raise InputError(
            "C01 saved query materialization missing; run indexing derive-query explicitly"
        ) from exc
    return revision, saved, value, array


def derive(budget, owner, revision_id):
    old, target = QueryView(owner), DerivedQueryContext(owner)
    value = library.revision(old, revision_id)
    dependencies = library.inventory(value["recipe"])
    bindings = {}
    for key in dependencies:
        bound = assets.read_binding(old, key)
        bindings[key] = {k: bound[k] for k in ("path", "parent_record") if k in bound}
    export = {
        "schema_version": "b03-query-export-1",
        "revision_id": revision_id,
        "recipe": value["recipe"],
        "dependencies": dependencies,
        "availability": "explicit C01-owned derivative; source/cue bindings must validate",
    }
    path = target.directory / "imports" / (digest(export) + ".json")
    owner.publish(budget, path, export, immutable=True)
    library.import_recipe(budget, target, record(path), bindings)
    owner.charge(budget, query_jobs=1)
    result = materialization.materialize(budget, target, library.revision(target, revision_id))
    result["owner"] = "C01 derivative; B03 artifacts unchanged"
    return result
