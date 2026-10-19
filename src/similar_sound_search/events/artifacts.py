"""Authorized source/region records and validated deterministic proposal artifacts."""

from pathlib import Path

from ..evaluation.artifacts import record, write_record
from ..inputs import decode, probe
from ..preparation import _parent, crop_frames
from ..records import candidate
from ..search.contracts import code_identity
from ..storage import InputError, contained, digest, read_json, sha256
from .detector import propose


def source(budget, spec, context):
    if spec.get("schema_version") != "b01-source-1":
        raise InputError("event source: expected b01-source-1 with explicit region")
    path = Path(spec["path"])
    path = contained(path if path.is_absolute() else budget.root / path, budget.root / "data/audio")
    info = probe(path, budget)
    region = spec.get("region")
    if not isinstance(region, dict):
        raise InputError("event source: explicit selected region required")
    if set(region) == {"start_frame", "end_frame"}:
        first, last = region["start_frame"], region["end_frame"]
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (first, last)):
            raise InputError("event region: integer half-open source frames required")
    elif set(region) == {"start_seconds", "end_seconds"}:
        first, last = crop_frames(
            region["start_seconds"], region["end_seconds"], info.frames, info.samplerate
        )
    else:
        raise InputError("event region: explicit frame pair or seconds pair required")
    if (
        not 0 <= first < last <= info.frames
        or (last - first) / info.samplerate > context.cfg["max_region_seconds"]
    ):
        raise InputError("event region: out of input bounds or greater than 30 seconds")
    context.charge(budget, read_audio_seconds=info.frames / info.samplerate)
    samples, meta = decode(path, budget)
    if spec.get("sha256") and spec["sha256"] != meta["sha256"]:
        raise InputError("event source changed: " + str(path))
    parent = record(budget.root / spec["parent_record"]) if spec.get("parent_record") else None
    ctx = read_json(budget.root / spec["context"]) if spec.get("context") else None
    if parent is not None and ctx is not None:
        raise InputError("event source: parent record or new context, never both")
    if parent and parent["source"]["local_path"] != path.relative_to(budget.root).as_posix():
        context.charge(budget, read_audio_seconds=parent["source"]["duration_seconds"])
    lineage = (
        _parent(parent, path, meta, budget) if parent else candidate(path, meta, ctx, budget.root)
    )
    return samples, {
        "spec": spec,
        "audio": meta,
        "parent": lineage,
        "region": [first, last],
        "path": path.relative_to(budget.root).as_posix(),
    }


def recipe(context):
    code = code_identity()
    return {
        "version": "b01-proposals-1",
        "configuration": context.cfg,
        "code": {p: code[p] for p in ("events/detector.py", "events/artifacts.py")},
    }


def validate(budget, path, context):
    value = record(contained(path, context.directory / "proposals"))
    if (
        value["identity"]["recipe"] != recipe(context)
        or digest(value["identity"]) != value["proposal_id"]
    ):
        raise InputError("event proposals stale: detector/configuration changed")
    src = value["identity"]["source"]
    original = contained(budget.root / src["path"], budget.root / "data/audio")
    context.charge(budget, read_audio_seconds=src["audio"]["duration_seconds"])
    if sha256(original, budget) != src["audio"]["sha256"]:
        raise InputError("event proposals stale: original bytes changed: " + src["path"])
    # A changed explicit context or parent must not reuse an obsolete map.
    spec = src["spec"]
    current = record(budget.root / spec["parent_record"]) if spec.get("parent_record") else None
    ctx = read_json(budget.root / spec["context"]) if spec.get("context") else None
    if current is not None and current != src["parent"]:
        raise InputError("event proposals stale: parent lineage changed")
    if current is not None:
        context.charge(budget, read_audio_seconds=current["source"]["duration_seconds"])
        _parent(current, original, src["audio"], budget)
    if current is None:
        proposed = candidate(original, src["audio"], ctx, budget.root)
        if proposed != src["parent"]:
            raise InputError("event proposals stale: input context changed")
    return value


def generate(budget, spec_path, context):
    samples, src = source(budget, read_json(spec_path), context)
    identity = {"recipe": recipe(context), "source": src}
    key = digest(identity)
    path = context.directory / "proposals" / (key + ".json")
    if path.exists():
        value = validate(budget, path, context)
        return {
            "status": "ok",
            "proposal": path.relative_to(budget.root).as_posix(),
            "events": len(value["detection"]["events"]),
            "reused": True,
        }
    context.charge(budget, proposal_inputs=1)
    budget.reserve(65536, samples.nbytes * 3 + 256 * 1024**2)
    detection = propose(samples, src["audio"]["sample_rate_hz"], *src["region"], context.cfg)
    context.charge(budget, proposed_events=len(detection["events"]), managed_output_bytes=65536)
    # Event IDs include source/configuration; equal frame numbers in other files differ.
    for event in detection["events"]:
        event["event_id"] = digest([key, event["event_id"]])
        if event["start_frame"] == 0:
            event["flags"].append("file_start_censored")
        if event["end_frame"] == src["audio"]["sample_count"]:
            event["flags"].append("file_end_censored")
    write_record(
        path,
        {
            "schema_version": "b01-proposals-1",
            "proposal_id": key,
            "identity": identity,
            "detection": detection,
        },
        budget,
    )
    return {
        "status": "ok",
        "proposal": path.relative_to(budget.root).as_posix(),
        "events": len(detection["events"]),
        "state": detection["state"],
        "reused": False,
    }
