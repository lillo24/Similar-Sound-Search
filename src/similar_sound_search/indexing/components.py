"""Optional region components: validated B02 reuse, ancestry and original playback."""

import numpy as np

from ..evaluation.artifacts import record
from ..inputs import decode
from ..queries.context import TransformContext
from ..separation import artifacts, dsp
from ..storage import InputError, contained, digest
from . import banks


def component_signal(value, name, original, path):
    identity = value["identity"]
    # Actual DSP dispatch determines dependency. Broad ignores its cue argument;
    # guided consumes it. Keep every historical cue in provenance regardless.
    if identity["mode"] != "broad" or name not in {"harmonic", "percussive"}:
        raise InputError("C01 generic component refused: query-dependent/guided or unsupported DSP")
    output = value["outputs"].get(name)
    if (
        output is None
        or output["state"] != "ok"
        or output["overload_samples"]
        or output["peak"] > 1
        or output["rms"] < 1e-7
    ):
        raise InputError("C01 component missing, clipped or near-silent: " + name)
    if identity["source"]["parent"]["source"]["sha256"] != original["source"]["sha256"]:
        raise InputError("C01 component parent is not the declared original recording")
    a = output["audio"]
    region = identity["spec"]["region"]
    if a["sample_count"] != region[1] - region[0] or a["duration_seconds"] > 12:
        raise InputError("C01 component: changed trim/padding/native support")
    signal = {
        "signal_id": digest([original["recording_id"], value["transform_id"], name]),
        "kind": "component",
        "component": name,
        "original": original,
        "audio": {**a, "local_path": output["path"]},
        "mapping": output["mapping"],
        "transformation": value,
        "transform_path": path,
        "ancestry_groups": value["excluded_groups"],
        "query_dependent": False,
        "instrument_identity": "unverified",
        "coverage_kind": "experimental region, not a full-track stem",
    }
    banks.original_bounds(signal, [0, a["sample_count"]])
    return signal


def view(owner, path):
    historical = path.is_relative_to(owner.root / "data/runs/separation/processed")
    return TransformContext(owner, historical=historical)


def load_component(budget, owner, signal):
    path = contained(owner.root / signal["transform_path"], owner.root)
    transform = artifacts.validate(budget, path, view(owner, path))
    if transform != signal["transformation"]:
        raise InputError("C01 component: source/cue/DSP/output/ancestry changed")
    expected = component_signal(
        transform, signal["component"], signal["original"], signal["transform_path"]
    )
    if expected != signal:
        raise InputError("C01 component: signal/map identity changed")
    a = signal["audio"]
    owner.charge(budget, read_audio_seconds=a["duration_seconds"])
    samples, audio = decode(
        contained(owner.root / a["local_path"], view(owner, path).directory / "processed"), budget
    )
    if (
        audio != {k: v for k, v in a.items() if k != "local_path"}
        or not np.isfinite(samples).all()
        or np.max(np.abs(samples)) > 1
    ):
        raise InputError("C01 component: corrupt/nonfinite/clipped output")
    source = transform["identity"]["source"]["audio"]
    owner.charge(budget, read_audio_seconds=source["duration_seconds"])
    original, actual = decode(owner.root / transform["identity"]["spec"]["source"]["path"], budget)
    if actual != source:
        raise InputError("C01 component: original changed during signal validation")
    lo, hi = transform["identity"]["spec"]["region"]
    summary = dsp.summaries(samples, original[lo:hi])
    output = transform["outputs"][signal["component"]]
    if summary["state"] != "ok" or summary != {k: output[k] for k in summary}:
        raise InputError("C01 component: actual near-silence/energy/overload summary differs")
    return samples


def prepare(budget, owner, desc, population, fixtures):
    pointer = owner.directory / "components.json"
    if pointer.exists():
        raise InputError("C01 component declaration already exists; build/resume its saved plans")
    plans, failures = [], []
    real = owner.protocol["components"]["real_regions"]
    if len(real) > 4 or any(len(v["components"]) > 2 for v in real):
        raise InputError("C01 component region/component ceiling exceeded")
    owner.charge(budget, real_regions=len(real))
    refusal = owner.protocol["components"].get("guided_refusal")
    guided_evidence = None
    if refusal:
        value = record(
            contained(owner.root / refusal["record"], owner.root / "data/runs/separation/processed")
        )
        if (
            value["record_hash"] != refusal["record_hash"]
            or digest(value["identity"]) != value["transform_id"]
            or not value["identity"]["cue"]
        ):
            raise InputError("C01 guided refusal: expected intact actual cue-dependent receipt")
        try:
            component_signal(value, "extracted", {}, refusal["record"])
        except InputError as exc:
            guided_evidence = {
                "record_hash": value["record_hash"],
                "transform_id": value["transform_id"],
                "mode": value["identity"]["mode"],
                "cue_preserved": value["identity"]["cue"]["audio"]["sha256"],
                "generic_bank_state": "refused",
                "reason": str(exc),
            }
        else:
            raise InputError("C01 guided refusal control unexpectedly admitted")
    selected = []
    for item in real:
        original = [
            v["original"]
            for v in population.values()
            if v["audio"]["sha256"] == item["source_sha256"]
        ]
        if len(original) != 1:
            raise InputError("C01 component: real original not uniquely bound")
        selected.append((item["record"], original[0], "discovery", item["components"], item))
    source = fixtures["sources"][0]["source"]
    spec = {
        "schema_version": "b02-process-input-1",
        "source": {"path": source["source"]["local_path"], "sha256": source["source"]["sha256"]},
        "region": [0, source["source"]["sample_count"]],
        "event": [0, source["source"]["sample_count"]],
        "label": "C01 controlled mixture; no instrument/separation relevance claim",
    }
    # Charge and write an explicit pending receipt before any DSP. B02's own
    # processing boundary reserves inputs/seconds/output under the C01 delegate.
    owner.publish(
        budget, owner.directory / "component-pending.json", {"state": "pending", "spec": spec}
    )
    result = artifacts.process(budget, spec, "broad", TransformContext(owner))
    selected.append((result["transform"], source, "engineering", ["harmonic", "percussive"], None))
    for relative, original, scope, names, declaration in selected:
        path = owner.root / relative
        try:
            value = artifacts.validate(budget, path, view(owner, path))
            if declaration and (
                value["identity"]["spec"]["region"] != declaration["region"]
                or value["identity"]["source"]["audio"]["sample_rate_hz"] != declaration["rate"]
            ):
                raise InputError("C01 component: prospectively declared region changed")
            for name in names:
                try:
                    signal = component_signal(value, name, original, relative)
                    variant = {
                        "kind": "HPSS",
                        "component": name,
                        "mode": "broad",
                        "configuration": value["identity"]["configuration"],
                        "dsp_code": value["identity"]["dsp_code"],
                    }
                    plan_path, _ = banks.create_plan(
                        budget,
                        owner,
                        "component-" + name + "-" + scope,
                        variant,
                        desc,
                        owner.cfg["component_grid"],
                        {signal["signal_id"]: signal},
                        scope,
                    )
                    plans.append(plan_path.relative_to(owner.root).as_posix())
                except InputError as exc:
                    failures.append(
                        {
                            "record": relative,
                            "component": name,
                            "state": "unsupported",
                            "reason": str(exc),
                        }
                    )
        except (InputError, FileNotFoundError) as exc:
            failures.append(
                {"record": relative, "components": names, "state": "failed", "reason": str(exc)}
            )
    value = {
        "schema_version": "c01-component-declaration-1",
        "state": "partial" if failures else "ready-regions-only",
        "plans": plans,
        "failures": failures,
        "full_catalogue_separation": False,
        "guided_refusal": guided_evidence,
    }
    owner.publish(budget, pointer, value, immutable=True)
    return {"status": "ok", **value}
