"""Immutable B02 transformation receipts, explicit source/cue geometry and lineage."""

import os
import time

import numpy as np
from scipy.io.wavfile import write as write_wav

from ..evaluation.artifacts import record, write_record
from ..inputs import decode, probe
from ..preparation import _parent, versions
from ..records import candidate, compose_mapping, validate_context
from ..search import sources
from ..search.contracts import code_identity
from ..storage import InputError, contained, digest, read_json
from . import dsp


def bounds(value, frames, label):
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) for v in value)
        or not 0 <= value[0] < value[1] <= frames
    ):
        raise InputError(label + ": integer half-open native frame bounds required")
    return value


def source(budget, spec, context):
    if not isinstance(spec, dict) or set(spec) - {
        "path",
        "sha256",
        "context",
        "parent_record",
        "bounds",
    }:
        raise InputError("B02 source/cue: unsupported fields")
    path = contained(budget.root / spec["path"], budget.root / "data")
    info = probe(path, budget)
    context.charge(budget, read_audio_seconds=info.frames / info.samplerate)
    x, audio = decode(path, budget)
    if audio["sha256"] != spec["sha256"]:
        raise InputError("B02 source/cue bytes changed: " + spec["path"])
    ctx = validate_context(
        read_json(budget.root / spec["context"]) if spec.get("context") else None
    )
    parent = candidate(path, audio, ctx, budget.root)
    if spec.get("parent_record"):
        if spec.get("context"):
            raise InputError("B02 source: choose parent_record or context")
        parent = record(budget.root / spec["parent_record"])
        context.charge(budget, read_audio_seconds=parent["source"]["duration_seconds"])
        parent = _parent(parent, path, audio, budget)
    population, groups = sources.catalogue(budget.root)
    excluded = set()
    for value in population:
        if (
            value["source_asset"]["sha256"] in {audio["sha256"], parent["source"]["sha256"]}
            or value["source_asset"]["canonical_pcm"]["sha256"] == audio["canonical_pcm"]["sha256"]
            or value["analysis_derivative"]["sha256"] == audio["sha256"]
        ):
            excluded.add(groups["entry_groups"][value["entry_id"]])
    return x, {"spec": spec, "audio": audio, "parent": parent}, excluded


def resolve(budget, spec, mode, context):
    if spec.get("schema_version") != "b02-process-input-1" or set(spec) - {
        "schema_version",
        "source",
        "region",
        "event",
        "cue",
        "label",
    }:
        raise InputError("B02 process: b02-process-input-1 required")
    x, original, groups = source(budget, spec["source"], context)
    rate = original["audio"]["sample_rate_hz"]
    first, last = bounds(spec["region"], len(x), "processing region")
    a, b = bounds(spec["event"], len(x), "event")
    if not first <= a < b <= last or (last - first) / rate > context.cfg["max_region_seconds"]:
        raise InputError("B02 event must be inside the at-most-12-second context")
    cue, conditioning = None, None
    if spec.get("cue"):
        cue, conditioning, cue_groups = source(budget, spec["cue"], context)
        ca, cb = bounds(spec["cue"]["bounds"], len(cue), "cue")
        if (cb - ca) / conditioning["audio"]["sample_rate_hz"] > context.cfg["max_cue_seconds"]:
            raise InputError("B02 cue exceeds four seconds")
        cue = cue[ca:cb]
        groups.update(cue_groups)
    if mode == "guided" and cue is None:
        raise InputError("B02 guided extraction: explicit cue required")
    identity = {
        "schema_version": "b02-transform-1",
        "spec": spec,
        "source": original,
        "cue": conditioning,
        "mode": mode,
        "configuration": context.cfg,
        "tools": versions(),
        "dsp_code": code_identity()["separation/dsp.py"],
    }
    return x[first:last], cue, identity, sorted(groups)


def verify_outputs(budget, value, context):
    first, last = value["identity"]["spec"]["region"]
    source = value["identity"]["source"]["audio"]
    for output in value["outputs"].values():
        path = contained(
            budget.root / output["path"], context.directory / "processed" / value["transform_id"]
        )
        context.charge(budget, read_audio_seconds=(last - first) / source["sample_rate_hz"])
        _, actual = decode(path, budget)
        if (
            actual != output["audio"]
            or actual["sample_count"] != last - first
            or actual["sample_rate_hz"] != source["sample_rate_hz"]
            or actual["channels"] != source["channels"]
        ):
            raise InputError("B02 output missing/corrupt/shifted: " + output["path"])
        expected = compose_mapping(
            value["identity"]["source"]["parent"],
            first / source["sample_rate_hz"],
            last / source["sample_rate_hz"],
            (last - first) / source["sample_rate_hz"],
            "sha256:" + actual["sha256"],
        )
        if output["mapping"] != expected:
            raise InputError("B02 output: source map changed")


def validate(budget, path, context):
    value = record(contained(path, context.directory / "processed"))
    if value.get("schema_version") != "b02-transform-1" or value["transform_id"] != digest(
        value["identity"]
    ):
        raise InputError("B02 transformation receipt: invalid identity/schema")
    _, _, expected, excluded = resolve(
        budget, value["identity"]["spec"], value["identity"]["mode"], context
    )
    if expected != value["identity"] or excluded != value["excluded_groups"]:
        raise InputError("B02 transformation stale: source/cue/map/configuration changed")
    verify_outputs(budget, value, context)
    return value


def process(budget, spec, mode, context):
    started = time.perf_counter()
    x, cue, identity, excluded = resolve(budget, spec, mode, context)
    key = digest(identity)
    directory = context.directory / "processed" / key
    path = directory / "record.json"
    if path.exists():
        value = record(path)
        if value["identity"] != identity or value["excluded_groups"] != excluded:
            raise InputError("B02 reuse: transform identity changed")
        verify_outputs(budget, value, context)
        return {
            "status": "ok",
            "transform": path.relative_to(budget.root).as_posix(),
            "reused": True,
            "validation_seconds": time.perf_counter() - started,
        }
    rate = identity["source"]["audio"]["sample_rate_hz"]
    count = 1 if mode == "original" else context.cfg["max_components"]
    reservation = x.nbytes * count + 131072
    context.charge(
        budget,
        processing_inputs=1,
        preparation_bytes=reservation,
        separator_input_seconds=(
            len(x) / rate
            + (
                len(cue) / identity["cue"]["audio"]["sample_rate_hz"]
                if cue is not None and mode == "guided"
                else 0
            )
        )
        if mode != "original"
        else 0,
    )
    budget.reserve(reservation, context.cfg["max_temporary_bytes"] + x.nbytes * 8)
    processing_started = time.perf_counter()
    outputs, details = dsp.process(
        x,
        rate,
        mode,
        context.cfg,
        cue,
        identity["cue"]["audio"]["sample_rate_hz"] if cue is not None else None,
    )
    processing_seconds = time.perf_counter() - processing_started
    directory.mkdir(parents=True, exist_ok=True)
    saved = {}
    for name, samples in outputs.items():
        if samples.shape != x.shape or not np.isfinite(samples).all():
            raise InputError("B02 transform: nonfinite or altered source support: " + name)
        target = directory / (name + ".wav")
        temporary = directory / (".partial-" + name + ".wav")
        write_wav(temporary, rate, samples.astype(np.float32))
        if target.exists():
            if target.read_bytes() != temporary.read_bytes():
                raise InputError("B02 interrupted output differs: " + name)
            temporary.unlink()
        else:
            os.replace(temporary, target)
        context.charge(budget, read_audio_seconds=len(x) / rate)
        actual, audio = decode(target, budget)
        if not np.array_equal(actual, samples):
            raise InputError("B02 output: float32 round-trip changed samples")
        first, last = spec["region"]
        summary = dsp.summaries(actual, x)
        saved[name] = {
            "path": target.relative_to(budget.root).as_posix(),
            "audio": audio,
            **summary,
            "mapping": compose_mapping(
                identity["source"]["parent"],
                first / rate,
                last / rate,
                (last - first) / rate,
                "sha256:" + audio["sha256"],
            ),
        }
    value = {
        "schema_version": "b02-transform-1",
        "transform_id": key,
        "identity": identity,
        "outputs": saved,
        "excluded_groups": excluded,
        "processing": details,
        "processing_seconds": processing_seconds,
        "cold_total_seconds": time.perf_counter() - started,
        "interpretation": "DSP components, not identified instruments; "
        "cue may be contaminated; no automatic fallback",
    }
    budget.refresh_disk()
    write_record(path, value, budget)
    return {
        "status": "ok",
        "transform": path.relative_to(budget.root).as_posix(),
        "reused": False,
        "outputs": {k: v["state"] for k, v in saved.items()},
    }


def handoff(budget, path, component, context):
    validate(budget, path, context)
    relative = path.relative_to(budget.root).as_posix()
    context.resolve_example(budget, {"b02_record": relative, "component": component})
    spec = {
        "schema_version": "a06-query-input-1",
        "label": "B02 " + component + " query; relevance unmeasured",
        "examples": [{"b02_record": relative, "component": component}],
    }
    target = context.directory / "inputs" / (digest(spec) + ".json")
    if target.exists() and read_json(target) != spec:
        raise InputError("B02 query handoff changed")
    if not target.exists():
        context.charge(budget, managed_output_bytes=65536)
        from ..storage import bounded_json

        bounded_json(target, spec, budget)
    return {"status": "ok", "input": target.relative_to(budget.root).as_posix()}
