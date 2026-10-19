"""Minimal verified local event report with separate single/multiple search pages."""

import hashlib
import html
import os
import shutil

from ..evaluation.artifacts import record, write_record
from ..inputs import decode
from ..records import map_time
from ..search.report import clip, stamp, verify_bundle
from ..storage import InputError, contained, digest, sha256
from .selection import load_selection


def page(value):
    def escape(x):
        return html.escape(str(x), quote=True)

    source = value["source"]
    rate = source["audio"]["sample_rate_hz"]
    first, last = source["region"]
    cards = []
    selected = set(value["selected_ids"])
    for event in value["proposals"]:
        a, b = event["start_frame"], event["end_frame"]
        cards.append(
            f"<tr><td>{escape(event['event_id'][:12])}</td>"
            f"<td>{stamp(a / rate)}–{stamp(b / rate)}</td>"
            f"<td>{'selected' if event['event_id'] in selected else 'proposal'}</td>"
            f"<td>{escape(', '.join(event['flags']) or 'no heuristic boundary warning')}</td></tr>"
        )
    audio = []
    for item in value["event_items"]:
        c = item["clip"]
        audio.append(
            f"<article><h3>{escape(item['label'])}</h3><p>{escape(item['time_basis'])}</p>"
            f'<audio controls preload="metadata" src="{escape(c["path"])}"></audio></article>'
        )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width">'
        "<title>B01 sound-event selection</title><style>"
        "body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;"
        "background:#f7f7f2;color:#18252c}article{background:white;padding:1rem;margin:1rem 0;"
        "border:1px solid #cbd2ce;border-radius:8px}table{border-collapse:collapse;width:100%}"
        "td,th{padding:.6rem;text-align:left;border-bottom:1px solid #ccd}audio{width:100%}"
        "a{color:#064e83}code{word-break:break-all}</style>"
        "<h1>B01 · sound-event selection</h1><p>Explicit/coarse selection remains the default. "
        "Proposals are experimental and contain surrounding mixture layers. "
        "No instrument isolation, intended-layer confirmation or human relevance was measured.</p>"
        f"<h2>{escape(source['parent']['recording'].get('title') or 'Explicit source')}</h2>"
        f"<p>Authorized available-file region {stamp(first / rate)}–{stamp(last / rate)}. "
        f"Native {rate} Hz / "
        f"{source['audio']['channels']} channels. Original-song offset: "
        f"{escape(source['parent']['timestamp_mapping']['original_recording_offset_seconds'])} "
        "(None means unknown). Loulou remains missing; this is a named engineering substitute.</p>"
        '<p><a href="single.html">One-event search and separate distances</a> · '
        '<a href="multiple.html">Unordered multiple-event search and per-example distances</a></p>'
        "<p>Both searches exclude source/duplicate parents and use the same 2.4-second grid, "
        "fixed mean timbre distance "
        "and pitch off. Scores are uncalibrated candidate rankings.</p>"
        "<h2>Proposals and frozen selection</h2><table><thead><tr><th>ID</th>"
        "<th>Available file</th><th>Selection</th>"
        "<th>Boundary uncertainty</th></tr></thead><tbody>" + "".join(cards) + "</tbody></table>"
        "<h2>Original context and encoded crops</h2>"
        + "".join(audio)
        + "<p>Context playback is separate from encoded query audio. "
        "PCM16 playback uses one declared constant attenuation only if needed for overload; "
        "immutable query audio retains native float samples. "
        "HTML/media hashes are checked by the loopback listener.</p></html>"
    )


def build(budget, spec, context):
    if spec.get("schema_version") != "b01-report-input-1":
        raise InputError("event report: expected b01-report-input-1")
    extraction = record(
        contained(budget.root / spec["extraction"], context.directory / "extractions")
    )
    selection = load_selection(budget, budget.root / extraction["selection"], context)
    if selection["record_hash"] != extraction["selection_hash"]:
        raise InputError("event report: extraction selection changed")
    proposal = record(budget.root / selection["proposal"])
    identity = {
        "extraction_hash": extraction["record_hash"],
        "single_report": spec["single_report"],
        "multiple_report": spec["multiple_report"],
    }
    directory = context.reports / ("events-" + digest(identity))
    items, pages = [], {}
    for name in ("single", "multiple"):
        original_path = contained(budget.root / spec[name + "_report"], context.reports)
        allowed = verify_bundle(budget.root, original_path, context.reports)
        bundle = record(original_path.parent / "bundle.json")
        # Copy only validated files named by the owned bundle. Pages share one
        # media directory; content-addressed names prevent collisions.
        for item in bundle["items"]:
            c = item["clip"]
            original = allowed["/" + c["path"]]
            target = contained(directory / c["path"], directory / "media")
            if not target.exists():
                context.charge(budget, clips=1, clip_bytes=original.stat().st_size + 4096)
                budget.reserve(original.stat().st_size + 4096)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, target)
                budget.refresh_disk()
            if sha256(target, budget) != c["sha256"]:
                raise InputError("event report: copied media differs")
            items.append({"clip": c})
        target = directory / (name + ".html")
        content = allowed["/index.html"].read_text(encoding="utf-8")
        budget.reserve(len(content.encode()) + 65536)
        directory.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        pages[name + ".html"] = sha256(target, budget)
    src = extraction["source"]
    context.charge(
        budget, read_audio_seconds=src["audio"]["duration_seconds"], managed_output_bytes=65536
    )
    samples, current = decode(budget.root / src["path"], budget)
    if current != src["audio"]:
        raise InputError("event report: original identity changed")
    source = {"source": src["audio"]}
    rate = src["audio"]["sample_rate_hz"]
    event_items = [
        {
            "label": "Authorized original context (not query support)",
            "time_basis": "Available-file " + stamp(src["region"][0] / rate),
            "clip": clip(
                budget, directory / "media", source, samples, *src["region"], context=context
            ),
        }
    ]
    for i, event in enumerate(extraction["events"]):
        e, prepared = event["event"], event["prepared"]
        mapping = map_time(prepared, 0)
        event_items.append(
            {
                "label": "Encoded event " + str(i + 1),
                "time_basis": str(mapping),
                "clip": clip(
                    budget,
                    directory / "media",
                    source,
                    samples,
                    e["start_frame"],
                    e["end_frame"],
                    context=context,
                ),
            }
        )
    value = {
        "schema_version": "b01-playback-1",
        "identity": identity,
        "source": src,
        "proposals": proposal["detection"]["events"],
        "selected_ids": [e["event"]["event_id"] for e in extraction["events"]],
        "event_items": event_items,
        "items": items + event_items,
        "pages": pages,
        "media_verified": True,
        "browser_controls": "not established by byte/map validation",
    }
    content = page(value)
    budget.reserve(len(content.encode()) + 65536)
    temporary = directory / ".b01-report.html"
    temporary.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary, directory / "index.html")
    value["html_sha256"] = hashlib.sha256((directory / "index.html").read_bytes()).hexdigest()
    write_record(directory / "bundle.json", value, budget)
    verify_bundle(budget.root, directory, context.reports)
    return {
        "status": "ok",
        "report": (directory / "index.html").relative_to(budget.root).as_posix(),
        "clips": len(value["items"]),
        "samples_verified": True,
    }
