"""Explicit local asset bindings and read-only historical transformation dependencies."""

from ..evaluation.artifacts import record
from ..events.selection import frame_seconds
from ..inputs import decode, inspect_file, probe
from ..preparation import _parent
from ..records import validate_context
from ..search import sources
from ..separation import artifacts
from ..storage import InputError, contained, digest, read_json
from .context import TransformContext
from .contracts import fields, identifier


def binding_path(owner, key):
    return owner.directory / "bindings" / (identifier(key) + ".json")


def asset_path(owner, key):
    return owner.directory / "assets" / (identifier(key) + ".json")


def read_binding(owner, key):
    snapshot = getattr(owner, "binding_snapshots", None)
    if snapshot is not None:
        value = snapshot.get(key)
        if not isinstance(value, dict) or value.get("record_hash") != digest(
            {k: v for k, v in value.items() if k != "record_hash"}
        ):
            raise InputError("B03 materialization: missing/corrupt immutable binding snapshot")
        return value
    return record(binding_path(owner, key))


def register(budget, owner, path, context=None, expected=None, parent_path=None):
    path = contained(path, budget.root)
    info = probe(path, budget)
    owner.charge(budget, read_audio_seconds=info.frames / info.samplerate)
    ctx = validate_context(context)
    value = inspect_file(path, budget, ctx)
    audio = value["technical_metadata"]
    if expected is not None and audio["sha256"] != expected:
        raise InputError("B03 register: source SHA256 differs: " + path.name)
    registration = owner.directory / "registrations" / (digest(value) + ".json")
    owner.publish(
        budget,
        registration,
        {"schema_version": "b03-a02-registration-1", "candidate": value},
        immutable=True,
    )
    parent = None
    if parent_path:
        parent_path = contained(parent_path, budget.root)
        parent = record(parent_path)
        contained(budget.root / parent["source"]["local_path"], budget.root)
        owner.charge(budget, read_audio_seconds=parent["source"]["duration_seconds"])
        _parent(parent, path, audio, budget)
    identity = {
        "audio": audio,
        "context": ctx,
        "parent_hash": parent["record_hash"] if parent else None,
    }
    key = digest(identity)
    owner.publish(
        budget,
        asset_path(owner, key),
        {"schema_version": "b03-asset-1", "asset_id": key, "identity": identity},
        immutable=True,
    )
    binding = {
        "schema_version": "b03-binding-1",
        "kind": "asset",
        "dependency": key,
        "path": path.relative_to(budget.root).as_posix(),
        "parent_record": parent_path.relative_to(budget.root).as_posix() if parent else None,
    }
    previous = binding_path(owner, key)
    if (
        previous.exists()
        and {k: v for k, v in record(previous).items() if k != "record_hash"} != binding
    ):
        raise InputError(
            "B03 register: asset already bound elsewhere; use explicit import --bindings"
        )
    owner.publish(budget, previous, binding, immutable=True)
    return {
        "status": "ok",
        "asset_id": key,
        "audio": audio,
        "context": ctx,
        "registration": registration.relative_to(owner.root).as_posix(),
    }


def read_asset(budget, owner, key, with_samples=False):
    saved = record(asset_path(owner, key))
    identity = saved["identity"]
    if (
        saved.get("schema_version") != "b03-asset-1"
        or digest(identity) != key
        or saved["asset_id"] != key
    ):
        raise InputError("B03 asset: corrupt identity/schema")
    bound = read_binding(owner, key)
    fields(
        bound,
        {"schema_version", "kind", "dependency", "path", "parent_record", "record_hash"},
        "asset binding",
    )
    if (
        bound["schema_version"] != "b03-binding-1"
        or bound["kind"] != "asset"
        or bound["dependency"] != key
    ):
        raise InputError("B03 binding: wrong asset/schema")
    path = contained(budget.root / bound["path"], budget.root)
    if not path.is_file():
        raise FileNotFoundError("B03 required source missing: " + bound["path"])
    owner.charge(budget, read_audio_seconds=identity["audio"]["duration_seconds"])
    samples, audio = decode(path, budget)
    if audio != identity["audio"]:
        raise InputError(
            "B03 asset: changed source bytes/PCM/decoder; re-register explicitly: " + bound["path"]
        )
    if identity["parent_hash"] is not None:
        parent = record(contained(budget.root / bound["parent_record"], budget.root))
        if parent["record_hash"] != identity["parent_hash"]:
            raise InputError("B03 asset: wrong parent/map receipt")
        contained(budget.root / parent["source"]["local_path"], budget.root)
        owner.charge(budget, read_audio_seconds=parent["source"]["duration_seconds"])
        _parent(parent, path, audio, budget)
    return (identity, bound, samples) if with_samples else (identity, bound)


def transform_descriptor(value, component):
    if value.get("schema_version") != "b02-transform-1" or value["transform_id"] != digest(
        value["identity"]
    ):
        raise InputError("B03 transform: expected intact B02 transformation receipt")
    output = value["outputs"].get(component)
    if output is None or output["state"] != "ok":
        raise InputError("B03 transform: component absent/near-silent; select original explicitly")
    identity = value["identity"]
    return {
        "kind": "transform",
        "transform_id": value["transform_id"],
        "record_hash": value["record_hash"],
        "component": component,
        "mode": identity["mode"],
        "configuration": identity["configuration"],
        "tools": identity["tools"],
        "dsp_code": identity["dsp_code"],
        "event": identity["spec"]["event"],
        "context": identity["spec"]["region"],
        "source_audio": identity["source"]["audio"],
        "source_parent_id": identity["source"]["parent"]["record_id"],
        "source_mapping": identity["source"]["parent"]["timestamp_mapping"],
        "cue": {
            "audio": identity["cue"]["audio"],
            "bounds": identity["spec"]["cue"]["bounds"],
            "parent_id": identity["cue"]["parent"]["record_id"],
            "contamination": "not verified clean",
        }
        if identity["cue"]
        else None,
        "output": {k: v for k, v in output.items() if k != "path"},
        "excluded_groups": value["excluded_groups"],
    }


def transform_view(owner, path):
    path = contained(path, owner.root)
    historical = path.is_relative_to(owner.root / "data/runs/separation/processed")
    view = TransformContext(owner, historical=historical)
    contained(path, view.directory / "processed")
    return path, view


def bind_transform(budget, owner, path, component):
    path, _ = transform_view(owner, path)
    value = record(path)
    descriptor = transform_descriptor(value, component)
    key = digest(descriptor)
    owner.publish(
        budget,
        binding_path(owner, key),
        {
            "schema_version": "b03-binding-1",
            "kind": "transform",
            "dependency": key,
            "path": path.relative_to(owner.root).as_posix(),
        },
        immutable=True,
    )
    return descriptor


def read_transform(budget, owner, descriptor):
    key = digest(descriptor)
    bound = read_binding(owner, key)
    fields(
        bound, {"schema_version", "kind", "dependency", "path", "record_hash"}, "transform binding"
    )
    if (
        bound.get("schema_version") != "b03-binding-1"
        or bound.get("kind") != "transform"
        or bound.get("dependency") != key
    ):
        raise InputError("B03 transform: wrong dependency binding")
    path, view = transform_view(owner, owner.root / bound["path"])
    value = artifacts.validate(budget, path, view)
    if transform_descriptor(value, descriptor["component"]) != descriptor:
        raise InputError("B03 transform: changed source/cue/component/map/receipt")
    return value


def groups_for(owner, identity):
    population, groups = sources.catalogue(owner.root)
    audio = identity["audio"]
    return {
        groups["entry_groups"][v["entry_id"]]
        for v in population
        if v["source_asset"]["sha256"] == audio["sha256"]
        or v["source_asset"]["canonical_pcm"]["sha256"] == audio["canonical_pcm"]["sha256"]
        or v["analysis_derivative"]["sha256"] == audio["sha256"]
    }


def resolve_example(budget, owner, item):
    if item["kind"] == "asset":
        identity, binding = read_asset(budget, owner, item["asset_id"])
        rate = identity["audio"]["sample_rate_hz"]
        first, last = item["event"]
        start, end = frame_seconds(first, last, rate)
        result = {"path": binding["path"], "start": start, "end": end}
        if binding["parent_record"]:
            result["parent_record"] = binding["parent_record"]
        else:
            path = owner.directory / "contexts" / (digest(identity["context"]) + ".json")
            if not path.exists():
                from ..storage import bounded_json

                owner.charge(budget, metadata_bytes=65536)
                bounded_json(path, identity["context"], budget)
            elif read_json(path) != identity["context"]:
                raise InputError("B03 source context changed")
            result["context"] = path.relative_to(owner.root).as_posix()
        return result, sorted(groups_for(owner, identity))
    if item["kind"] != "transform":
        raise InputError("B03 example: unknown processing kind")
    value = read_transform(budget, owner, item["transform"])
    output = value["outputs"][item["transform"]["component"]]
    a, b = value["identity"]["spec"]["event"]
    first = value["identity"]["spec"]["region"][0]
    start, end = frame_seconds(a - first, b - first, output["audio"]["sample_rate_hz"])
    return {"path": output["path"], "start": start, "end": end}, value["excluded_groups"]
