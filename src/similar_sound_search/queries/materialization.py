"""Compose validated revisions with the existing native query/preparation pipeline."""

from ..evaluation.artifacts import record
from ..search import query
from ..search.contracts import frozen
from ..storage import InputError, digest
from . import library


def input_for(recipe):
    examples = recipe["examples"]
    return {
        "schema_version": "a06-query-input-1",
        "label": "B03 explicit sound examples; relevance unverified",
        "examples": examples,
        "b03_binding": {"version": "b03-materialization-1", "examples": examples},
    }


def state_path(owner, revision_id):
    return owner.directory / "revision-state" / (revision_id + ".json")


def materialize(budget, owner, value):
    library.validate_recipe(value["recipe"])
    spec = input_for(value["recipe"])
    path = owner.directory / "inputs" / (digest(spec) + ".json")
    from ..storage import bounded_json, read_json

    if not path.exists():
        owner.charge(budget, metadata_bytes=65536)
        bounded_json(path, spec, budget)
    elif read_json(path) != spec:
        raise InputError("B03 materialization: changed saved input")
    owner.publish(
        budget,
        state_path(owner, value["revision_id"]),
        {"state": "in_progress", "revision_id": value["revision_id"]},
    )
    result = query.prepare_query(budget, path, "efficientat", context=owner)
    saved = record(budget.root / result["query"])
    binding = {
        "revision_id": value["revision_id"],
        "query_id": saved["query_id"],
        "query_hash": saved["record_hash"],
    }
    key = digest(binding)
    materialized = {
        "schema_version": "b03-materialization-1",
        "materialization_id": key,
        "identity": binding,
        "query": result["query"],
        "state": "ready",
        "feature_stats": owner.feature_stats,
        "initial_query_reused": result["reused"],
    }
    output = owner.directory / "materializations" / (key + ".json")
    # Reuse retains the cold statistics in the immutable receipt, while this call
    # separately reports current cache behavior.
    if not output.exists():
        owner.publish(budget, output, materialized, immutable=True)
    else:
        old = record(output)
        if old["identity"] != binding or old["query"] != result["query"]:
            raise InputError("B03 materialization: conflicting immutable receipt")
    owner.publish(
        budget,
        state_path(owner, value["revision_id"]),
        {
            "state": "ready",
            "revision_id": value["revision_id"],
            "materialization": output.relative_to(owner.root).as_posix(),
        },
    )
    return {
        "status": "ok",
        "revision_id": value["revision_id"],
        "materialization": output.relative_to(owner.root).as_posix(),
        **result,
        "cache": owner.feature_stats if not result["reused"] else {"query_reused": True, "new": 0},
    }


def receipt(owner, value, materialization_id=None):
    from ..storage import contained
    from .contracts import identifier

    if materialization_id is None:
        state = record(state_path(owner, value["revision_id"]))
        if state.get("state") != "ready":
            raise InputError("B03 materialization interrupted; resume the same revision")
        path = contained(
            owner.root / state["materialization"], owner.directory / "materializations"
        )
    else:
        path = owner.directory / "materializations" / (identifier(materialization_id) + ".json")
    saved = record(path)
    if (
        saved.get("schema_version") != "b03-materialization-1"
        or saved["identity"]["revision_id"] != value["revision_id"]
        or digest(saved["identity"]) != saved["materialization_id"]
    ):
        raise InputError("B03 materialization: invalid revision/artifact binding")
    return saved


def load(budget, owner, value, materialization_id=None):
    saved = receipt(owner, value, materialization_id)
    _, _, _, _, desc = frozen(budget)
    query_value, array = query.load_query(budget, owner.root / saved["query"], desc, context=owner)
    if (
        query_value["record_hash"] != saved["identity"]["query_hash"]
        or query_value["identity"]["consumer"]["examples"] != value["recipe"]["examples"]
    ):
        raise InputError("B03 materialization: revision/query identity changed")
    return saved, query_value, array


def validate(budget, owner, value):
    # Resolve every contribution, including cues and duplicated PCM parents, even
    # when no feature blob exists. Missing dependencies never become cached success.
    try:
        for item in value["recipe"]["examples"]:
            owner.resolve_example(budget, item)
        state = state_path(owner, value["revision_id"])
        if not state.exists():
            return {
                "status": "ok",
                "availability_state": "valid_recipe; not materialized",
                "ready": False,
            }
        load(budget, owner, value)
        return {"status": "ok", "availability_state": "ready", "ready": True}
    except FileNotFoundError as exc:
        return {"status": "failed", "availability_state": "missing", "error": str(exc)}
    except InputError as exc:
        message = str(exc)
        state = (
            "interrupted"
            if "interrupted" in message
            else "incompatible"
            if any(v in message for v in ("version", "configuration", "representation", "decoder"))
            else "corrupt"
        )
        return {"status": "failed", "availability_state": state, "error": message}
