"""Explicit proposal/manual selection, native A02 extraction and unordered query handoff."""

from decimal import Decimal, localcontext

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..inputs import decode
from ..preparation import prepare
from ..search.contracts import code_identity
from ..storage import InputError, contained, digest, read_json
from . import artifacts


def automatic(events, cfg):
    """First distinct chronological supported bounds, retaining uncertainty; no score access."""
    seen, result = set(), []
    for event in sorted(events, key=lambda e: (e["start_frame"], e["onset_frame"], e["event_id"])):
        bounds = (event["start_frame"], event["end_frame"])
        if bounds in seen or "below_minimum_query_duration" in event["flags"]:
            continue
        seen.add(bounds)
        result.append(event)
        if len(result) == cfg["max_selected_events"]:
            break
    return result


def select(budget, path, context, ids=None, intervals=None, auto=False):
    value = artifacts.validate(budget, path, context)
    if sum((bool(ids), bool(intervals), auto)) != 1:
        raise InputError("selection: choose exactly --auto, --ids or --intervals")
    source = value["identity"]["source"]
    first, last = source["region"]
    if auto:
        events = automatic(value["detection"]["events"], context.cfg)
        method = (
            "first distinct chronological supported proposals, up to three; uncertainty retained"
        )
    elif ids:
        proposed = {e["event_id"]: e for e in value["detection"]["events"]}
        if len(set(ids)) != len(ids) or set(ids) - set(proposed):
            raise InputError("selection: unknown or repeated event ID")
        events = [proposed[k] for k in ids]
        method = "explicit event IDs"
    else:
        events = []
        for item in intervals:
            if len(item) != 2 or any(isinstance(v, bool) or not isinstance(v, int) for v in item):
                raise InputError("manual selection: integer half-open native bounds required")
            a, b = item
            events.append(
                {
                    "event_id": digest([value["proposal_id"], "manual", a, b]),
                    "start_frame": a,
                    "end_frame": b,
                    "onset_frame": a,
                    "flags": ["manual_completeness_unverified"],
                    "complete": False,
                }
            )
        method = "explicit manual native intervals; not detector success"
    if not 1 <= len(events) <= context.cfg["max_selected_events"]:
        raise InputError(
            "selection: no usable events or more than three; explicit manual path available"
        )
    rate = source["audio"]["sample_rate_hz"]
    for event in events:
        a, b = event["start_frame"], event["end_frame"]
        ms = (b - a) * 1000 / rate
        if (
            not first <= a < b <= last
            or not context.cfg["minimum_event_milliseconds"]
            <= ms
            <= context.cfg["maximum_event_milliseconds"]
        ):
            raise InputError("selection: bounds outside region or unsupported duration (60ms..8s)")
    events.sort(key=lambda e: (e["start_frame"], e["end_frame"], e["event_id"]))
    identity = {
        "proposal_hash": value["record_hash"],
        "events": events,
        "method": method,
        "selection_code": code_identity()["events/selection.py"],
    }
    key = digest(identity)
    output = context.directory / "selections" / (key + ".json")
    result = {
        "schema_version": "b01-selection-1",
        "selection_id": key,
        "identity": identity,
        "proposal": path.relative_to(budget.root).as_posix(),
        "source": source,
    }
    if output.exists():
        if record(output)["identity"] != identity:
            raise InputError("selection reuse: identity differs")
    else:
        context.charge(budget, managed_output_bytes=65536)
        write_record(output, result, budget)
    return {
        "status": "ok",
        "selection": output.relative_to(budget.root).as_posix(),
        "events": len(events),
        "method": method,
    }


def frame_seconds(first, last, rate):
    """Interior quarter-sample decimals make A02 floor/ceil exact even at 44.1 kHz."""
    with localcontext() as ctx:
        ctx.prec = 40
        return str((Decimal(first) + Decimal(".25")) / rate), str(
            (Decimal(last) - Decimal(".25")) / rate
        )


def load_selection(budget, path, context):
    value = record(contained(path, context.directory / "selections"))
    proposal = artifacts.validate(budget, budget.root / value["proposal"], context)
    if (
        value["identity"]["proposal_hash"] != proposal["record_hash"]
        or value["selection_id"] != digest(value["identity"])
        or value["identity"]["selection_code"] != code_identity()["events/selection.py"]
        or value["source"] != proposal["identity"]["source"]
    ):
        raise InputError("selection stale: proposal/bounds/selection code changed")
    return value


def extract(budget, path, context):
    value = load_selection(budget, path, context)
    source = value["source"]
    rate, channels = source["audio"]["sample_rate_hz"], source["audio"]["channels"]
    key = value["selection_id"]
    directory = context.directory / "extractions" / key
    extracted = []
    for event in value["identity"]["events"]:
        first, last = event["start_frame"], event["end_frame"]
        start, end = frame_seconds(first, last, rate)
        context.charge(
            budget,
            read_audio_seconds=source["audio"]["duration_seconds"],
            preparation_bytes=(last - first) * channels * 4 + 65536,
        )
        parent = source["parent"] if source["parent"]["kind"] == "prepared" else None
        if parent is not None:
            context.charge(budget, read_audio_seconds=parent["source"]["duration_seconds"])
        ctx = (
            read_json(budget.root / source["spec"]["context"])
            if source["spec"].get("context")
            else None
        )
        result = prepare(
            budget.root / source["path"],
            budget,
            rate,
            "preserve",
            start,
            end,
            context=ctx if parent is None else None,
            parent_record=parent,
        )
        prepared = result["record"]
        # Verify actual query samples against the immutable native source; never
        # rely on rounded seconds as evidence of extraction correctness.
        context.charge(
            budget,
            read_audio_seconds=source["audio"]["duration_seconds"]
            + prepared["artifact"]["duration_seconds"],
        )
        original, _ = decode(budget.root / source["path"], budget)
        crop, _ = decode(budget.root / prepared["artifact"]["local_path"], budget)
        if not np.array_equal(crop, original[first:last]) or crop.shape != (last - first, channels):
            raise InputError("event extraction: native sample verification failed")
        extracted.append(
            {
                "event": event,
                "prepared": prepared,
                "parent_record": result["bundle"] + "/record.json",
                "model_support": {
                    "actual_frames": last - first,
                    "native_rate": rate,
                    "minimum_model_frames_at_32khz": 1024,
                    "model_padding_frames": max(
                        0, 1024 - ((last - first) * 32000 + rate - 1) // rate
                    ),
                    "padding": "adapter right-zero-pads only below 1024 resampled frames",
                    "catalogue_window_seconds": 2.4,
                    "time_stretch": False,
                },
            }
        )

    def handoff(items):
        # Binding is a set of source/bounds/recipe identities; temporal order stays
        # in the extraction record, never in retrieval identity or distance weights.
        bindings = sorted(
            {
                digest(
                    {
                        "source": source["audio"]["sha256"],
                        "bounds": [e["event"]["start_frame"], e["event"]["end_frame"]],
                        "proposal": value["identity"]["proposal_hash"],
                    }
                )
                for e in items
            }
        )
        return {
            "schema_version": "a06-query-input-1",
            "label": "B01 selected events (uncertainty retained)",
            "b01_binding": {"version": "b01-handoff-1", "events": bindings},
            "examples": [
                {
                    "path": e["prepared"]["artifact"]["local_path"],
                    "parent_record": e["parent_record"],
                }
                for e in items
            ],
        }

    single, multiple = directory / "single.json", directory / "multiple.json"
    for out, spec in ((single, handoff(extracted[:1])), (multiple, handoff(extracted))):
        if out.exists():
            if {k: v for k, v in record(out).items() if k != "record_hash"} != spec:
                raise InputError("event handoff stale")
        else:
            write_record(out, spec, budget)
    write_record(
        directory / "extraction.json",
        {
            "schema_version": "b01-extraction-1",
            "selection": path.relative_to(budget.root).as_posix(),
            "selection_hash": value["record_hash"],
            "source": source,
            "events": extracted,
            "native_samples_verified": True,
        },
        budget,
    )
    return {
        "status": "ok",
        "extraction": (directory / "extraction.json").relative_to(budget.root).as_posix(),
        "single_input": single.relative_to(budget.root).as_posix(),
        "multiple_input": multiple.relative_to(budget.root).as_posix(),
        "events": len(extracted),
    }
