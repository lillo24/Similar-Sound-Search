"""Immutable portable revisions, display labels, optimistic heads and explicit import."""

import re
import uuid

from ..evaluation.artifacts import record
from ..separation.artifacts import bounds
from ..storage import InputError, contained, digest, project_lock
from . import assets
from .contracts import canonical_examples, fields, identifier, preference, selection

OFF = {"version": "b03-pitch-1", "weight": 0, "scale_semitones": 12}


def revision_path(owner, key):
    return owner.directory / "revisions" / (identifier(key, "revision") + ".json")


def name_path(owner, key):
    return owner.directory / "names" / (identifier(key, "query name ID") + ".json")


def validate_recipe(recipe):
    fields(recipe, {"schema_version", "assets", "examples", "pitch"}, "recipe")
    if (
        recipe["schema_version"] != "b03-query-recipe-1"
        or not isinstance(recipe["assets"], dict)
        or len(recipe["assets"]) > 8
    ):
        raise InputError("B03 recipe: unknown schema or asset table")
    preference(recipe["pitch"])
    examples = canonical_examples(recipe["examples"])
    if examples != recipe["examples"]:
        raise InputError("B03 recipe: examples must be canonical unordered contributions")
    used = set()
    for item in examples:
        selection(item.get("selection"))
        if item.get("kind") == "asset":
            fields(item, {"kind", "asset_id", "event", "context", "selection"}, "original example")
            key = identifier(item["asset_id"], "asset")
            value = recipe["assets"].get(key)
            if not isinstance(value, dict) or digest(value) != key:
                raise InputError("B03 recipe: missing/wrong source identity")
            fields(value, {"audio", "context", "parent_hash"}, "asset identity")
            from ..records import validate_context

            if validate_context(value["context"]) != value["context"]:
                raise InputError("B03 source context is not normalized")
            audio = value["audio"]
            frames, rate = audio["sample_count"], audio["sample_rate_hz"]
            if any(
                isinstance(v, bool) or not isinstance(v, int) or v <= 0
                for v in (frames, rate, audio["channels"])
            ):
                raise InputError("B03 asset: positive native dimensions required")
            identifier(audio["sha256"], "source bytes")
            identifier(audio["canonical_pcm"]["sha256"], "source PCM")
            a, b = bounds(item["event"], frames, "B03 selected event")
            left, right = bounds(item["context"], frames, "B03 original context")
            if not left <= a < b <= right or (b - a) / rate > 30 or (right - left) / rate > 30:
                raise InputError(
                    "B03 original event/context: at most thirty seconds, no truncation"
                )
            if value["parent_hash"] is not None:
                identifier(value["parent_hash"], "parent")
            used.add(key)
        elif item.get("kind") == "transform":
            fields(item, {"kind", "transform", "selection"}, "processed example")
            v = item["transform"]
            fields(
                v,
                {
                    "kind",
                    "transform_id",
                    "record_hash",
                    "component",
                    "mode",
                    "configuration",
                    "tools",
                    "dsp_code",
                    "event",
                    "context",
                    "source_audio",
                    "source_parent_id",
                    "source_mapping",
                    "cue",
                    "output",
                    "excluded_groups",
                },
                "transform dependency",
            )
            for key in ("transform_id", "record_hash", "dsp_code"):
                identifier(v[key], "transform " + key)
            rate = v["source_audio"]["sample_rate_hz"]
            a, b = bounds(v["event"], v["source_audio"]["sample_count"], "B03 transformed event")
            left, right = bounds(
                v["context"], v["source_audio"]["sample_count"], "B03 transformed context"
            )
            if (
                not left <= a < b <= right
                or (right - left) / rate > 12
                or v["component"]
                not in {"original", "harmonic", "percussive", "extracted", "residual"}
            ):
                raise InputError("B03 transform: unsupported context/component")
            if v["mode"] == "guided" and v["cue"] is None:
                raise InputError("B03 guided revision requires actual cue provenance")
        else:
            raise InputError("B03 recipe: unknown example kind")
    if used != set(recipe["assets"]):
        raise InputError("B03 recipe: unused/missing asset dependencies")
    return recipe


def normalize(budget, owner, spec):
    if spec.get("schema_version") == "b03-query-recipe-1":
        return validate_recipe(spec)
    fields(spec, {"schema_version", "examples"}, "query input", {"pitch"})
    if spec["schema_version"] != "b03-query-input-1":
        raise InputError("B03 input: expected b03-query-input-1 or portable recipe")
    examples, dependencies = [], {}
    for item in canonical_examples(spec["examples"]):
        selected = selection(item.get("selection"))
        if "asset_id" in item:
            fields(item, {"asset_id", "event", "context", "selection"}, "source input")
            key = identifier(item["asset_id"])
            value = record(assets.asset_path(owner, key))
            dependencies[key] = value["identity"]
            examples.append({"kind": "asset", **item})
        else:
            fields(item, {"transform_record", "component", "selection"}, "transform input")
            variant = assets.bind_transform(
                budget, owner, owner.root / item["transform_record"], item["component"]
            )
            examples.append({"kind": "transform", "transform": variant, "selection": selected})
    return validate_recipe(
        {
            "schema_version": "b03-query-recipe-1",
            "assets": dependencies,
            "examples": canonical_examples(examples),
            "pitch": spec.get("pitch", OFF),
        }
    )


def revision(owner, key):
    value = record(revision_path(owner, key))
    if (
        value.get("schema_version") != "b03-revision-1"
        or value.get("revision_id") != key
        or digest(validate_recipe(value["recipe"])) != key
    ):
        raise InputError("B03 revision: corrupt/stale recipe identity")
    return value


def resolve(owner, query_id=None, revision_id=None):
    if bool(query_id) == bool(revision_id):
        raise InputError("B03 select exactly --query-id or --revision")
    if query_id:
        value = record(name_path(owner, query_id))
        revision_id = value["selected"]
    return revision(owner, revision_id)


def label(value):
    if (
        not isinstance(value, str)
        or not 0 < len(value.strip()) <= 160
        or any(ord(c) < 32 for c in value)
    ):
        raise InputError("B03 display name: one to 160 printable characters required")
    return value


def save(budget, owner, spec, name, query_id=None, expected=None):
    recipe = normalize(budget, owner, spec)
    key = digest(recipe)
    name = label(name)
    with project_lock(owner.root, ".b03-library.lock"):
        previous = None
        if query_id:
            previous = record(name_path(owner, query_id))
            if expected != previous["selected"]:
                raise InputError(
                    "B03 revision conflict: --expected must match current selected revision"
                )
        elif expected is not None:
            raise InputError("B03 create: --expected is only valid for an existing query")
        else:
            query_id = digest({"new_query": uuid.uuid4().hex})
        owner.publish(
            budget,
            revision_path(owner, key),
            {"schema_version": "b03-revision-1", "revision_id": key, "recipe": recipe},
            immutable=True,
        )
        versions = sorted(set((previous["revisions"] if previous else []) + [key]))
        owner.publish(
            budget,
            name_path(owner, query_id),
            {
                "schema_version": "b03-name-1",
                "query_id": query_id,
                "label": name,
                "selected": key,
                "revisions": versions,
            },
        )
    return {
        "status": "ok",
        "query_id": query_id,
        "revision_id": key,
        "label": name,
        "state": "valid_recipe; materialization availability not yet validated",
    }


def change_name(budget, owner, query_id, expected, name=None, selected=None):
    with project_lock(owner.root, ".b03-library.lock"):
        value = record(name_path(owner, query_id))
        if expected != value["record_hash"]:
            raise InputError("B03 display/head conflict: --expected must match name record_hash")
        if selected is not None:
            revision(owner, selected)
            if selected not in value["revisions"]:
                raise InputError("B03 select: revision does not belong to named query")
            value["selected"] = selected
        if name is not None:
            value["label"] = label(name)
        owner.publish(
            budget,
            name_path(owner, query_id),
            {k: v for k, v in value.items() if k != "record_hash"},
        )
    return {"status": "ok", "name": record(name_path(owner, query_id))}


def inventory(recipe):
    result = {key: {"kind": "asset", "identity": value} for key, value in recipe["assets"].items()}
    for item in recipe["examples"]:
        if item["kind"] == "transform":
            v = item["transform"]
            result[digest(v)] = {
                "kind": "transform",
                "descriptor": v,
                "required": "exact transform receipt and source/cue/parent/output closure "
                "at its recorded project-relative layout; do not rewrite historical receipts",
            }
    return result


def export_recipe(budget, owner, value):
    output = {
        "schema_version": "b03-query-export-1",
        "revision_id": value["revision_id"],
        "recipe": value["recipe"],
        "dependencies": inventory(value["recipe"]),
        "availability": "metadata only; explicit local bindings and exact "
        "media/weights/features required",
    }
    portable(output)
    path = owner.directory / "exports" / (value["revision_id"] + ".json")
    owner.publish(budget, path, output, immutable=True)
    return {
        "status": "ok",
        "export": path.relative_to(owner.root).as_posix(),
        "revision_id": value["revision_id"],
    }


def portable(value):
    """Refuse machine paths/credential fields in a transportable metadata recipe."""
    if isinstance(value, dict):
        forbidden = {"password", "token", "secret", "authorization", "api_key", "access_key"}
        if any(str(k).lower() in forbidden for k in value):
            raise InputError("B03 export: credential fields are not portable query metadata")
        for item in value.values():
            portable(item)
    elif isinstance(value, list):
        for item in value:
            portable(item)
    elif isinstance(value, str) and re.search(
        r"(?<!\w)[A-Za-z]:[\\/]|^\\\\|(?<![\w:/])/[^/\s]", value
    ):
        raise InputError("B03 export: absolute paths in metadata must be removed explicitly")


def import_recipe(budget, owner, value, bindings=None):
    fields(
        value,
        {"schema_version", "revision_id", "recipe", "dependencies", "availability", "record_hash"},
        "export",
    )
    recipe = validate_recipe(value["recipe"])
    key = digest(recipe)
    if (
        value["schema_version"] != "b03-query-export-1"
        or key != value["revision_id"]
        or inventory(recipe) != value["dependencies"]
    ):
        raise InputError("B03 import: altered dependency inventory/revision")
    supplied = bindings or {}
    if not isinstance(supplied, dict) or set(supplied) - set(value["dependencies"]):
        raise InputError("B03 import: unknown dependency binding")
    # Validate every supplied binding before changing any existing binding table.
    checked = {}
    for dependency, bound in supplied.items():
        item = value["dependencies"][dependency]
        if item["kind"] == "asset":
            fields(bound, {"path"}, "import asset binding", {"parent_record"})
            path = contained(owner.root / bound["path"], owner.root)
            identity = item["identity"]
            owner.charge(budget, read_audio_seconds=identity["audio"]["duration_seconds"])
            from ..inputs import decode

            _, actual = decode(path, budget)
            if actual != identity["audio"]:
                raise InputError(
                    "B03 import: same filename/different bytes or decoder metadata: "
                    + bound["path"]
                )
            if identity["parent_hash"]:
                from ..preparation import _parent

                parent = record(contained(owner.root / bound.get("parent_record", ""), owner.root))
                if parent["record_hash"] != identity["parent_hash"]:
                    raise InputError("B03 import: wrong parent/map receipt")
                contained(owner.root / parent["source"]["local_path"], owner.root)
                owner.charge(budget, read_audio_seconds=parent["source"]["duration_seconds"])
                _parent(parent, path, actual, budget)
            elif bound.get("parent_record"):
                raise InputError("B03 import: unexpected parent receipt")
            checked[dependency] = {
                "schema_version": "b03-binding-1",
                "kind": "asset",
                "dependency": dependency,
                "path": path.relative_to(owner.root).as_posix(),
                "parent_record": bound.get("parent_record"),
            }
        else:
            fields(bound, {"path"}, "import transform binding")
            from ..separation import artifacts

            path, view = assets.transform_view(owner, owner.root / bound["path"])
            actual = artifacts.validate(budget, path, view)
            if (
                assets.transform_descriptor(actual, item["descriptor"]["component"])
                != item["descriptor"]
            ):
                raise InputError("B03 import: wrong transform/cue/map receipt")
            checked[dependency] = {
                "schema_version": "b03-binding-1",
                "kind": "transform",
                "dependency": dependency,
                "path": path.relative_to(owner.root).as_posix(),
            }
    with project_lock(owner.root, ".b03-library.lock"):
        for asset_id, identity in recipe["assets"].items():
            owner.publish(
                budget,
                assets.asset_path(owner, asset_id),
                {"schema_version": "b03-asset-1", "asset_id": asset_id, "identity": identity},
                immutable=True,
            )
        for dependency, bound in checked.items():
            previous = assets.binding_path(owner, dependency)
            if previous.exists():
                old = record(previous)
                owner.publish(
                    budget,
                    owner.directory / "binding-history" / (old["record_hash"] + ".json"),
                    {k: v for k, v in old.items() if k != "record_hash"},
                    immutable=True,
                )
            owner.publish(budget, previous, bound)
        owner.publish(
            budget,
            revision_path(owner, key),
            {"schema_version": "b03-revision-1", "revision_id": key, "recipe": recipe},
            immutable=True,
        )
    unresolved = [k for k in value["dependencies"] if not assets.binding_path(owner, k).is_file()]
    return {
        "status": "ok",
        "revision_id": key,
        "state": "unresolved" if unresolved else "bindings supplied; validate before execution",
        "unresolved": unresolved,
    }
