"""Local B03 command routing; metadata operations never instantiate a matcher."""

from pathlib import Path

from ..evaluation.artifacts import record
from ..events import compatibility
from ..storage import InputError, read_json
from . import assets, library, materialization
from .context import TransformContext


def dispatch(request, budget, owner):
    action = request["queries_action"]
    path = Path(request["input"]) if request.get("input") else None
    if action == "list":
        return {
            "status": "ok",
            "queries": [record(p) for p in sorted((owner.directory / "names").glob("*.json"))],
        }
    if action == "register":
        if path is None:
            raise InputError("B03 register requires an explicit source file")
        context = read_json(request["context"]) if request.get("context") else None
        return assets.register(
            budget, owner, path, context, request.get("sha256"), request.get("parent_record")
        )
    if action in {"save", "revise"}:
        if path is None or request.get("name") is None:
            raise InputError("B03 save/revise requires input JSON and --name")
        if action == "revise" and not request.get("query_id"):
            raise InputError("B03 revise requires --query-id --expected")
        return library.save(
            budget,
            owner,
            read_json(path),
            request["name"],
            request.get("query_id"),
            request.get("expected"),
        )
    if action in {"rename", "select"}:
        if (
            not request.get("query_id")
            or (action == "rename" and request.get("name") is None)
            or (action == "select" and not request.get("revision"))
        ):
            raise InputError(
                "B03 rename/select requires --query-id, --expected and --name/--revision"
            )
        return library.change_name(
            budget,
            owner,
            request.get("query_id"),
            request.get("expected"),
            name=request.get("name") if action == "rename" else None,
            selected=request.get("revision") if action == "select" else None,
        )
    if action == "import":
        if path is None:
            raise InputError("B03 import requires an exported JSON")
        return library.import_recipe(
            budget,
            owner,
            record(path),
            read_json(request["bindings"]) if request.get("bindings") else None,
        )
    if action == "compatibility":
        return compatibility.step(request, budget, owner)
    if action == "process":
        if path is None:
            raise InputError("B03 process requires explicit unchanged B02 process input")
        from ..separation import artifacts

        return artifacts.process(budget, read_json(path), request["mode"], TransformContext(owner))
    if action in {"preflight", "compare", "known-answer", "report", "verify-native"}:
        from . import development, report, validation

        if action == "preflight":
            return development.preflight(budget, owner)
        if action == "compare":
            return development.step(budget, owner)
        if action == "known-answer":
            return validation.known_answers(budget, owner)
        if action == "verify-native":
            return validation.native(budget, owner, path)
        if path is None:
            raise InputError("B03 report requires explicit executions/revisions JSON")
        return report.build(budget, owner, read_json(path))
    value = library.resolve(owner, request.get("query_id"), request.get("revision"))
    if action == "show":
        output = {
            "status": "ok",
            "revision": value,
            "dependencies": library.inventory(value["recipe"]),
            "availability": "not validated; show performs no audio/model work",
        }
        if request.get("query_id"):
            output["name"] = record(library.name_path(owner, request["query_id"]))
        return output
    if action == "export":
        return library.export_recipe(budget, owner, value)
    if action == "validate":
        return materialization.validate(budget, owner, value)
    if action in {"materialize", "load"}:
        if action == "materialize":
            return materialization.materialize(budget, owner, value)
        saved, query, _ = materialization.load(budget, owner, value)
        return {
            "status": "ok",
            "revision_id": value["revision_id"],
            "materialization": saved,
            "query_id": query["query_id"],
            "examples": len(query["examples"]),
            "features_reused": True,
        }
    if action == "search":
        if not request.get("index") or not request.get("receipt"):
            raise InputError("B03 search requires --index --receipt")
        from .execution import step

        return step(request, budget, owner, value)
    raise InputError("B03 unsupported operation: " + action)
