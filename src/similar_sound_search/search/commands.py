"""Delivered offline operations, deterministic pre-ranking demo and cost pilot."""

import time

import numpy as np
from scipy.io.wavfile import write as write_wav
from scipy.signal import resample_poly

from ..evaluation.artifacts import record, write_record
from ..evaluation.scoring import known_answers
from ..inputs import measure
from ..matchers.models import adapter
from ..matchers.runner import memory_check
from ..preparation import prepare
from ..storage import InputError, bounded_json
from . import final, index, query, ranking, report, sources
from .contracts import configuration, frozen, grid, save_array
from .job import charge


def development_source(budget):
    _, _, protocol, _, _ = frozen(budget)
    population, groups = sources.catalogue(budget.root)
    for value in population:
        family = protocol["catalogue_links"]["entry_families"][value["entry_id"]]
        if protocol["families"][family] == "development":
            return sources.public_source(value, groups["entry_groups"][value["entry_id"]])
    raise InputError("A06 pilot/demo: no development-side catalogue original")


def pilot(budget):
    cfg = configuration(budget.root)
    _, _, _, _, desc = frozen(budget)
    path = budget.root / "manifests/search/pilot.json"
    if path.exists():
        value = record(path)
        if value["configuration"] != cfg or value["representation"] != desc:
            raise InputError("cost pilot changed; retain original evidence")
        return {"status": "ok", "pilot": value, "reused": True}
    source = development_source(budget)
    samples = sources.load(budget, source)
    rate = source["source"]["sample_rate_hz"]
    bounds = grid(len(samples), rate, cfg)[:64]
    charge(
        budget,
        pilot_windows=len(bounds),
        feature_bytes=len(bounds) * 384 * 4 + 65536,
        processed_window_seconds=sum((b - a) / rate for a, b in bounds),
    )
    obj, load_seconds = adapter(budget, "efficientat", desc)
    started = time.perf_counter()
    array = np.stack([obj.encode(samples[a:b], rate) for a, b in bounds])
    extraction = time.perf_counter() - started
    identity = {
        "pilot": True,
        "source_hash": source["source"]["sha256"],
        "bounds": bounds,
        "representation": desc,
        "dimension": 384,
    }
    save_array(budget.root / "data/features/search-pilot", identity, array, budget)
    value = {
        "schema_version": "a06-pilot-1",
        "configuration": cfg,
        "representation": desc,
        "source_id": source["recording_id"],
        "split": "development",
        "bounds": bounds,
        "windows": len(bounds),
        "load_seconds": load_seconds,
        "extraction_seconds": extraction,
        "peak_working_bytes": memory_check(budget),
        "catalogue_rankings_inspected": False,
        "decision": "Retain 2.4s/.25s grid and 512-window shards; no second duration",
        "estimated_full_extraction_seconds": extraction / len(bounds) * 44025,
    }
    write_record(path, value, budget)
    return {"status": "ok", "pilot": value, "reused": False}


def demo_inputs(budget):
    source = development_source(budget)
    samples = sources.load(budget, source)
    rate = source["source"]["sample_rate_hz"]
    # First non-silent 2.4s crop from starts 2,4.4,... below 30s, without any rankings.
    first = None
    size = int(2.4 * rate)
    for start in range(2 * rate, min(len(samples) - 2 * size, 30 * rate), size):
        if not measure(samples[start : start + size])["silent"]:
            first = start
            break
    if first is None:
        raise InputError("substitute demo: predetermined development source lacks an eligible crop")
    directory = budget.root / "config/local"
    example = {
        "path": source["source"]["local_path"],
        "start": str(first / rate),
        "end": str((first + size) / rate),
        "context": "config/local/a06-demo-context.json",
    }
    context = {
        "schema_version": "a02-input-1",
        "kind": source["source"]["kind"],
        "provenance": {
            "origin_url": source["source_url"],
            "permitted_use": source["rights"]["permitted_use"],
        },
    }
    bounded_json(directory / "a06-demo-context.json", context, budget)
    label = "Alternative engineering demo — development catalogue crop; Loulou unavailable"
    single = {"schema_version": "a06-query-input-1", "label": label, "examples": [example]}
    second = {**example, "start": str((first + size) / rate), "end": str((first + 2 * size) / rate)}
    multiple = {
        "schema_version": "a06-query-input-1",
        "label": label + " · two adjacent examples",
        "examples": [example, second, example],
    }
    for name, value in (("a06-demo.json", single), ("a06-multiple.json", multiple)):
        bounded_json(directory / name, value, budget)
    write_record(
        budget.root / "manifests/search/demo-selection.json",
        {
            "source_id": source["recording_id"],
            "source_hash": source["source"]["sha256"],
            "split": "development",
            "selected_before_rankings": True,
            "start_frame": first,
            "end_frame": first + size,
            "rate": rate,
            "selection": "first sorted development recording; first non-silent scheduled crop",
            "label": label,
            "parent_group": source["group"],
            "loulou_run": "unrun; missing/unverified",
        },
        budget,
    )
    return {
        "status": "ok",
        "single": "config/local/a06-demo.json",
        "multiple": "config/local/a06-multiple.json",
        "recording": source["recording_id"],
    }


def diagnostic_inputs(budget):
    """A development-only known target with independently fixed source coordinates."""
    from ..evaluation.rendering import render_tone

    _, _, protocol, _, _ = frozen(budget)
    preset = next(
        p for p in protocol["presets"] if protocol["families"][p["family"]] == "development"
    )
    target, _ = render_tone(preset, 0, 0, 42106)
    target = resample_poly(target, 2, 1).astype(np.float32)
    rate = 48000
    samples = np.zeros((rate * 8, 2), dtype=np.float32)
    start = rate * 3
    samples[start : start + len(target), 0] = target
    samples[start : start + len(target), 1] = target * 0.7
    path = budget.root / "data/audio/engineering/a06-known.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        charge(budget, query_preparation_bytes=samples.nbytes + 65536)
        budget.reserve(samples.nbytes + 65536, samples.nbytes * 4)
        write_wav(path, rate, samples)
        budget.refresh_disk()
    context = {
        "schema_version": "a02-input-1",
        "kind": "excerpt",
        "provenance": {"permitted_use": "Generated A06 engineering fixture"},
        "recording": {
            "recording_id": "a06-known-generated",
            "version": "a06-known-1",
            "identity_status": "verified",
            "identity_evidence": "fixed generated construction",
        },
        "original_recording_offset_seconds": 10,
        "offset_evidence": "engineering construction",
    }
    context_path = budget.root / "config/local/a06-known-context.json"
    bounded_json(context_path, context, budget)
    # Deliberate crop/resample lineage: final query maps to original 3.1..5.3s,
    # and known external synthetic offset maps to 13.1..15.3s, once.
    charge(budget, read_audio_seconds=10.4, query_preparation_bytes=2 * 65536 + 2 * rate * 4)
    first = prepare(path, budget, 16000, "preserve", "3", "5.4", context)
    budget.refresh_disk()
    second = prepare(
        budget.root / first["record"]["artifact"]["local_path"],
        budget,
        24000,
        "preserve",
        "0.1",
        "2.3",
        parent_record=first["record"],
    )
    budget.refresh_disk()
    bounded_json(
        budget.root / "config/local/a06-engineering.json",
        {
            "schema_version": "a06-engineering-1",
            "sources": [
                {
                    "path": path.relative_to(budget.root).as_posix(),
                    "context": "config/local/a06-known-context.json",
                }
            ],
        },
        budget,
    )
    bounded_json(
        budget.root / "config/local/a06-known-query.json",
        {
            "schema_version": "a06-query-input-1",
            "label": "Known-target engineering diagnostic",
            "examples": [
                {
                    "path": second["record"]["artifact"]["local_path"],
                    "parent_record": second["bundle"] + "/record.json",
                }
            ],
        },
        budget,
    )
    write_record(
        budget.root / "manifests/search/known-target.json",
        {
            "role": "engineering",
            "inserted_source_frames": [start, start + len(target)],
            "source_rate": rate,
            "expected_query_source_seconds": [3.1, 5.3],
            "expected_query_recording_seconds": [13.1, 15.3],
            "offset": 10,
        },
        budget,
    )
    return {
        "status": "ok",
        "engineering": "config/local/a06-engineering.json",
        "query": "config/local/a06-known-query.json",
    }


def dispatch(request, budget):
    action = request["search_action"]
    if action == "pilot":
        return pilot(budget)
    if action == "demo-inputs":
        return demo_inputs(budget)
    if action == "diagnostic-inputs":
        return diagnostic_inputs(budget)
    if action == "index":
        return index.step(request, budget)
    if action == "prepare-query":
        if not request.get("input"):
            raise InputError("search prepare-query requires explicit input JSON")
        return query.prepare_query(budget, request["input"], request.get("method") or "efficientat")
    if action == "rank":
        if not request.get("index") or not request.get("query"):
            raise InputError("search rank requires --index and --query")
        return ranking.rank(request, budget)
    if action == "report":
        if not request.get("input"):
            raise InputError("search report requires persisted result JSON")
        return report.build(budget, request["input"])
    if action == "declare":
        return final.declare(budget)
    if action == "final-run":
        return final.run_step(budget)
    if action == "final-score":
        return final.score_saved(budget)
    if action == "known-answer":
        return known_answers(budget, budget.root / "data/runs/search/known")
    raise InputError("unsupported A06 operation " + action)
