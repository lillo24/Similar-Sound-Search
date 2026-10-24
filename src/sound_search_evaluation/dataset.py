"""Frozen construction only: fresh performances, neutral inputs and private truth."""

import io
import math

import numpy as np
from scipy.signal import butter, resample_poly, sosfilt

from similar_sound_search.application import queries
from similar_sound_search.evaluation.artifacts import record, write_wav
from similar_sound_search.evaluation.rendering import RATE, mix, render_tone
from similar_sound_search.inputs import decode
from similar_sound_search.storage import InputError, digest


def preset(family, seed, colour="positive"):
    rng = np.random.default_rng(seed)
    p = {k: family[k] for k in ("spectral_slope", "fm_ratio", "cutoff_hz")}
    p["spectral_slope"] += rng.uniform(-0.04, 0.04)
    p["fm_ratio"] += rng.uniform(-0.02, 0.02)
    p["cutoff_hz"] += rng.uniform(-35, 35)
    if colour in {"hard-negative", "absent-target"}:
        delta = (1.3, 0.67, 2200) if colour == "hard-negative" else (2.4, 1.7, 6000)
        for k, d in zip(("spectral_slope", "fm_ratio", "cutoff_hz"), delta, strict=True):
            p[k] += d
    return dict(mechanism=family["mechanism"], parameters=p, variant=0)


def performance(family, spec, colour="positive"):
    seed = spec["performance_seed"]
    rng = np.random.default_rng(seed)
    detune = float(rng.uniform(-0.13, 0.13))
    if spec["event_seconds"] == 1.1:
        # Isolate a complete first-note attack/release, not a truncated motif tail.
        from .rendering import single_event

        samples = single_event(preset(family, seed, colour), spec["pitch"] + detune, seed)
    else:
        samples, _ = render_tone(
            preset(family, seed, colour), spec["phrase"], spec["pitch"] + detune, seed
        )
    t = np.arange(len(samples)) / RATE
    modulation = 1 + 0.03 * np.sin(
        2 * np.pi * rng.uniform(0.7, 2.1) * t + rng.uniform(0, 2 * np.pi)
    )
    return samples * modulation


def background(seed):
    rng = np.random.default_rng(seed)
    t = np.arange(192000) / RATE
    x = sosfilt(butter(3, 1800, fs=RATE, output="sos"), rng.standard_normal(len(t)))
    x *= 0.04 / np.sqrt(np.mean(x * x))
    return x + 0.01 * np.sin(2 * np.pi * 127 * t) + 0.008 * np.sin(2 * np.pi * 331 * t)


def components(families, spec, query=False, kind=None):
    colour = "absent-target" if kind == "absent-target" else spec.get("character", "positive")
    target = performance(families[spec["family"]], spec, colour)
    bg = background(spec["background_seed"])
    positions = [9600] if query else [round(v * RATE) for v in spec["positions"]]
    combined, receipt = mix(target, bg, positions, spec["ratio_db"])
    length = round(spec["duration_seconds"] * RATE)
    mono = combined[:length]
    channels = spec.get("channels", 1)
    if channels == 2:
        rng = np.random.default_rng(spec["background_seed"] + 1)
        combined = np.column_stack([mono, 0.7 * mono + 0.01 * rng.standard_normal(length)])
    else:
        combined = mono[:, None]
    rate = spec.get("rate", RATE)
    if rate != RATE:
        common = math.gcd(rate, RATE)
        combined = resample_poly(combined, rate // common, RATE // common, axis=0)
    return combined.astype(np.float32), dict(
        target=target, background=bg, positions=positions, receipt=receipt
    )


def write_audio(budget, owner, path, samples, rate):
    """Exclusive original creation; readiness follows decode/audit, incomplete bytes stay."""
    if path.exists():
        owner.charge(budget, read_audio_seconds=len(samples) / rate)
        actual, meta = decode(path, budget)
        if not np.array_equal(actual, samples):
            raise InputError("D02 retained generated original differs: " + path.name)
        return meta
    buffer = io.BytesIO()
    write_wav(buffer, rate, samples)
    raw = buffer.getvalue()
    owner.charge(budget, import_bytes=len(raw))
    budget.reserve(len(raw) + 4096, samples.nbytes * 6)
    path.parent.mkdir(parents=True, exist_ok=True)
    budget.track_file(path)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        import os

        os.fsync(stream.fileno())
    budget.account_file(path, len(raw))
    owner.charge(budget, read_audio_seconds=len(samples) / rate)
    return decode(path, budget)[1]


def generate_sources(budget, owner, ordinals):
    cfg = owner.protocol["splits"][owner.split]
    for i in ordinals:
        spec = cfg["sources"][i]
        render_spec = (
            cfg["sources"][spec["duplicate_of"]] if spec["duplicate_of"] is not None else spec
        )
        samples, _ = components(cfg["families"], render_spec)
        path = owner.audio / owner.split / "candidates" / (spec["source_id"] + ".wav")
        meta = write_audio(budget, owner, path, samples, render_spec["rate"])
        source = dict(
            recording_id=spec["source_id"],
            group=spec["group"],
            kind="engineering",
            record_hash=digest(dict(audio=meta, group=spec["group"])),
            source={**meta, "local_path": path.relative_to(owner.root).as_posix()},
            title="D02 item " + spec["source_id"][:8],
            artist="Generated performance",
            data_role="D02 engineering; outside discovery",
            provider="generated",
            rights="Project-generated D02 evaluation audio",
            source_url=None,
            source_page=None,
            basis="file",
            offset=None,
            offset_evidence="Known generated native origin",
        )
        owner.publish(
            budget,
            owner.directory / "generated" / (spec["source_id"] + ".json"),
            dict(schema_version="d02-generated-source-1", source=source),
            immutable=True,
        )
    return dict(sources=len(ordinals))


def generate_queries(budget, owner, ordinals):
    cfg = owner.protocol["splits"][owner.split]
    for i in ordinals:
        case = cfg["cases"][i]
        examples = []
        for j, spec in enumerate(case["examples"]):
            if spec["source_ordinal"] is not None:
                parent = cfg["sources"][spec["source_ordinal"]]
                source = record(owner.directory / "generated" / (parent["source_id"] + ".json"))[
                    "source"
                ]
                path = owner.root / source["source"]["local_path"]
                meta = source["source"]
            else:
                samples, _ = components(cfg["families"], spec, query=True, kind=case["kind"])
                path = (
                    owner.audio / owner.split / "queries" / (digest([case["case_id"], j]) + ".wav")
                )
                meta = write_audio(budget, owner, path, samples, RATE)
            examples.append(
                dict(
                    path=path.relative_to(owner.root).as_posix(),
                    audio=meta,
                    event=spec["event"],
                    context=spec["context"],
                )
            )
        owner.publish(
            budget,
            owner.directory / "generated-queries" / (case["case_id"] + ".json"),
            dict(
                schema_version="d02-neutral-query-1",
                case_id=case["case_id"],
                ordinal=i,
                examples=examples,
            ),
            immutable=True,
        )
    return dict(queries=len(ordinals))


def register_case(budget, owner, case_id):
    """B03 save/materialization inputs; product cases are registered via actual upload."""
    value = record(owner.directory / "generated-queries" / (case_id + ".json"))
    examples = []
    for example in value["examples"]:
        result = queries.register(
            budget, owner, owner.root / example["path"], "D02 reference " + case_id[:8]
        )
        examples.append(
            dict(
                asset_id=result["asset_id"],
                event=example["event"],
                context=example["context"],
                selection=dict(
                    origin="D02 prospective native selection",
                    version="b03-manual-native-1",
                    complete=False,
                    uncertainty=["Constructed mixture; no human layer judgment"],
                ),
            )
        )
    saved = queries.save(budget, owner, dict(label="D02 query " + case_id[:8], examples=examples))
    revision = saved["revision_id"]
    owner.publish(
        budget,
        owner.directory / "case-bindings" / (case_id + ".json"),
        dict(case_id=case_id, revision=revision),
        immutable=True,
    )
    return dict(case_id=case_id, revision=revision)
