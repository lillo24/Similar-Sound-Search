"""B02 playback boundary: original context, transformed signals and original candidates."""

import hashlib
import html
import os

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..inputs import decode
from ..search import sources
from ..search.report import clip, pcm16, stamp, verify_bundle
from ..storage import InputError, contained, digest, sha256
from . import artifacts
from .comparison import ARMS, read


def safe_clip(budget, directory, source, samples, first, last, context):
    """Recover an interrupted owned WAV only after verifying its exact conversion."""
    meta = source["source"]
    integers, gain = pcm16(samples[first:last])
    identity = {
        "source_sha256": meta["sha256"],
        "source_pcm": meta["canonical_pcm"],
        "first_frame": first,
        "last_frame": last,
        "rate": meta["sample_rate_hz"],
        "channels": meta["channels"],
        "encoding": "WAV/PCM16 little endian",
        "conversion": "float32 to round-to-nearest int16; no dither or channel change",
        "gain": gain,
    }
    key = digest(identity)
    wav, receipt = directory / (key + ".wav"), directory / (key + ".json")
    if wav.exists() and not receipt.exists():
        contained(wav, context.reports)
        context.charge(
            budget,
            clips=1,
            clip_bytes=wav.stat().st_size + 4096,
            read_audio_seconds=len(integers) / meta["sample_rate_hz"],
        )
        actual, audio = decode(wav, budget)
        if audio["sample_rate_hz"] != meta["sample_rate_hz"] or not np.array_equal(
            actual, integers.astype(np.float32) / 32768
        ):
            raise InputError("B02 interrupted playback WAV differs; preserve for inspection")
        write_record(
            receipt,
            {"identity": identity, "sha256": sha256(wav, budget), "bytes": wav.stat().st_size},
            budget,
        )
    return clip(budget, directory, source, samples, first, last, context=context)


def page(value):
    def escape(v):
        return html.escape(str(v), quote=True)

    cards = []
    for i, item in enumerate(value["items"]):
        c = item["clip"]
        score = (
            ""
            if item.get("score") is None
            else f"Distance {item['score']:.8f} (lower is closer; pitch off)."
        )
        cards.append(f'''<article><h3>{escape(item["label"])}</h3>
<p>{escape(item["timeline"])}</p><p>{escape(score)}</p>
<audio id="audio-{i}" controls preload="metadata" src="{escape(c["path"])}"></audio>
<label for="seek-{i}">Seek within clip</label><input id="seek-{i}" type="range" min="0"
max="{c["duration_seconds"]}" step=".01" value="0" data-audio="audio-{i}">
<p id="state-{i}">Loading media…</p><small>{escape(item["signal_role"])} · native {c["rate"]} Hz,
{c["channels"]} channel(s). Raw processing gain 1. Playback-only gain {c["gain"]:.8f}.
No independent stem normalization. Clip length {c["duration_seconds"]:.3f}s.</small></article>''')
    rows = []
    for arm, d in value["decision"].items():
        rows.append(
            f"<tr><td>{escape(arm)}</td><td>{d['paired_top1_gains']}</td><td>{d['paired_top1_losses']}</td>"
            f"<td>{d['median_sdr_improvement_db']:.3f} dB</td>"
            f"<td>{d['preservation_gate']}</td><td>{d['promoted']}</td></tr>"
        )
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport"
content="width=device-width">
<title>B02 · Optional processing comparison</title><style>
body{font:17px system-ui;max-width:1000px;margin:2rem auto;padding:0
1rem;background:#f4f3ee;color:#172b35}
article{background:white;padding:1.2rem;margin:1rem 0;border-radius:10px;border:1px solid #d6dfdf}
audio,input{width:100%}h1{font-size:30px}h3{font-size:20px}td,th{padding:.6rem;text-align:left;border-bottom:1px
solid #ccc}
small{color:#46565c}.failed{color:#9a0000}table{width:100%;border-collapse:collapse}</style>
<h1>B02 · Optional separation and extraction</h1><p>Default: original audio. Experimental
harmonic/percussive
components are not isolated instruments. Cue extraction uses an explicit, possibly contaminated
audio example.</p>
<p>"""
        + escape(value.get("source_label", "Explicit B02 source"))
        + """</p>
<p>Intended layer, complete real note and human relevance are unverified.</p><p>"""
        + escape(
            value.get("geometry_label", "Native geometry is bound in transformation receipts.")
        )
        + """</p><p>Master offset remains unknown when not supplied.
Processing never shifts or stretches these coordinates.</p>
<h2>Fixed development decision</h2><p>12 positive cases, clean/contaminated cues reported
separately;
absent, censored, silent and exact-waveform controls are separate. Candidate-side diagnostic
uses one
predeclared case and the same 16 complete original passages; it is distinct from the real
query-side searches.</p>
<table><tr><th>Mode</th><th>Top-1 gains</th><th>Losses</th><th>Median SDR
gain</th><th>Preservation passes</th><th>Promoted</th></tr>"""
        + "".join(rows)
        + """</table>
<p>Projection/SDR diagnostics use exact constructed components only in evaluation. No time
shift, fade,
truth-driven routing or loudness compensation is applied. Reconstruction alone does not
establish quality.</p>
<h2>Aligned audio and original catalogue passages</h2><p>Candidate cards always play original
mixtures.
Each query arm returns up to ten distinct recording/duplicate groups. Forced rankings and
distances do not detect presence.</p>"""
        + "".join(cards)
        + """<script>
document.querySelectorAll('audio').forEach((a,i)=>{const s=document.getElementById('state-'+i);
a.addEventListener('loadedmetadata',()=>s.textContent='Ready · '+a.duration.toFixed(3)+' s');
a.addEventListener('error',()=>{
s.textContent='Media missing or stale — verify/regenerate this bundle.';
s.className='failed';});});
document.querySelectorAll('input[type=range]').forEach(slider=>{slider.addEventListener('input',()=>{
const a=document.getElementById(slider.dataset.audio);const t=Number(slider.value);
if(Number.isFinite(a.duration)&&t>=0&&t<=a.duration)a.currentTime=t;});});</script></html>"""
    )


def build(budget, spec, context):
    if (
        set(spec) != {"transforms", "results", "comparison"}
        or set(spec["transforms"]) != set(ARMS)
        or set(spec["results"]) != set(ARMS)
    ):
        raise InputError("B02 report: exact original/broad/guided transforms and results required")
    comparison = record(
        contained(budget.root / spec["comparison"], context.directory / "comparison")
    )
    values = {
        mode: artifacts.validate(budget, budget.root / path, context)
        for mode, path in spec["transforms"].items()
    }
    specs = [v["identity"]["spec"] for v in values.values()]
    if any(v != specs[0] for v in specs) or any(values[m]["identity"]["mode"] != m for m in ARMS):
        raise InputError("B02 report: comparison source/event/cue differs")
    results = {
        m: record(contained(budget.root / p, context.results)) for m, p in spec["results"].items()
    }
    for mode, value in results.items():
        if value["identity"]["pitch_weight"] != 0 or value["state"] != "complete":
            raise InputError("B02 report: pitch-off complete real results required")
        examples = value["query"]["identity"]["consumer"]["examples"]
        if examples != [{"b02_record": spec["transforms"][mode], "component": ARMS[mode]}]:
            raise InputError("B02 report: processed query/result binding differs")
    if (
        len(
            {
                (v["identity"]["index_id"], digest(v["excluded_groups"]), v["scored_windows"])
                for v in results.values()
            }
        )
        != 1
    ):
        raise InputError("B02 report: arms must have equal original candidate support/exclusions")
    identity = {
        "spec": spec,
        "transforms": {k: v["record_hash"] for k, v in values.items()},
        "results": {k: v["record_hash"] for k, v in results.items()},
        "comparison": comparison["record_hash"],
    }
    directory = context.reports / ("separation-" + digest(identity))
    items = []

    def add(
        label, role, samples, audio, first, last, timeline, score=None, source_path=None, origin=0
    ):
        local = source_path or audio.get("local_path")
        if not local:
            raise InputError("B02 playback: explicit media source path required")
        items.append(
            {
                "label": label,
                "signal_role": role,
                "timeline": timeline,
                "score": score,
                "source_audio": {**audio, "local_path": local},
                "source_origin_seconds": origin,
                "available_file_zero_seconds": origin + first / audio["sample_rate_hz"],
                "clip": safe_clip(
                    budget, directory / "media", {"source": audio}, samples, first, last, context
                ),
            }
        )

    native = values["original"]["identity"]["source"]["audio"]
    first, last = specs[0]["region"]
    event = specs[0]["event"]
    for mode, value in values.items():
        for name, out in value["outputs"].items():
            x, audio = read(
                budget, context, {"path": out["path"], "sha256": out["audio"]["sha256"]}
            )
            role = "Original mixture" if mode == "original" else "Processed component · " + name
            rate = native["sample_rate_hz"]
            origin = out["mapping"]["segments"][0]["source_start_seconds"]
            timeline = (
                f"Available-file {stamp(origin)}–{stamp(origin + len(x) / rate)}; "
                f"clip zero = source {origin:.6f}s; master offset unverified when absent."
            )
            add(
                mode + " context · " + name,
                role,
                x,
                audio,
                0,
                len(x),
                timeline,
                source_path=out["path"],
                origin=origin,
            )
            if name == ARMS[mode]:
                add(
                    mode + " selected query",
                    role,
                    x,
                    audio,
                    event[0] - first,
                    event[1] - first,
                    f"Same native event [{event[0]}, {event[1]}) at {rate} Hz; "
                    f"{origin + (event[0] - first) / rate:.3f}–"
                    f"{origin + (event[1] - first) / rate:.3f}s original available-file.",
                    source_path=out["path"],
                    origin=origin,
                )
    cue, cm = read(budget, context, specs[0]["cue"])
    ca, cb = specs[0]["cue"]["bounds"]
    add(
        "Conditioning audio cue · contaminated mixture",
        "Original cue mixture",
        cue,
        cm,
        ca,
        cb,
        f"Available-file {ca / cm['sample_rate_hz']:.3f}–{cb / cm['sample_rate_hz']:.3f}s; "
        "no target-layer identity claim.",
        source_path=specs[0]["cue"]["path"],
    )
    for mode, value in results.items():
        for rank, hit in enumerate(value["candidates"], 1):
            source = hit["source"]
            samples = sources.load(budget, source, context=context)
            rate = source["source"]["sample_rate_hz"]
            a, b = max(0, hit["start_frame"] - rate), min(len(samples), hit["end_frame"] + rate)
            add(
                f"{mode} query · candidate {rank}: {source['title']}",
                "Original candidate mixture",
                samples,
                source["source"],
                a,
                b,
                f"Scored original passage {hit['start_frame'] / rate:.6f}–"
                f"{hit['end_frame'] / rate:.6f}s "
                f"available-file; playback zero {a / rate:.6f}s; "
                f"master offset {source['offset']}.",
                hit["score"],
            )
    # A controlled aligned example makes measured target loss inspectable separately.
    controlled = comparison["cases"][0]
    for mode in ARMS:
        value = artifacts.validate(
            budget, budget.root / controlled["arms"][mode]["transform"], context
        )
        out = value["outputs"][ARMS[mode]]
        x, meta = read(budget, context, {"path": out["path"], "sha256": out["audio"]["sha256"]})
        a, b = controlled["case"]["native_mapping"]["selected_in_region"]
        add(
            "Controlled development · " + mode,
            "Original controlled mixture" if mode == "original" else "Processed controlled query",
            x,
            meta,
            a,
            b,
            "Constructed source event 1.500–3.900s; full phrase/release, "
            "exact target reserved to evaluator.",
            source_path=out["path"],
            origin=out["mapping"]["segments"][0]["source_start_seconds"],
        )
    native_origin = values["original"]["outputs"]["original"]["mapping"]["segments"][0][
        "source_start_seconds"
    ]
    native_rate = native["sample_rate_hz"]
    value = {
        "schema_version": "b02-playback-1",
        "identity": identity,
        "items": items,
        "decision": comparison["decisions"],
        "default": comparison["default"],
        "source_label": specs[0].get("label", "Explicit B02 source"),
        "geometry_label": (
            f"Same selected event {native_origin + (event[0] - first) / native_rate:.3f}–"
            f"{native_origin + (event[1] - first) / native_rate:.3f}s; context "
            f"{native_origin:.3f}–{native_origin + (last - first) / native_rate:.3f}s. "
            "Cue identity and bounds are shown below; available-file coordinates."
        ),
        "encoding": "WAV/PCM16",
        "offline": True,
    }
    content = page(value)
    context.charge(budget, managed_output_bytes=len(content.encode()) + 65536)
    budget.reserve(len(content.encode()) + 65536)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / ".partial.html"
    temporary.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary, directory / "index.html")
    budget.refresh_disk()
    value["html_sha256"] = hashlib.sha256((directory / "index.html").read_bytes()).hexdigest()
    write_record(directory / "bundle.json", value, budget)
    verify_bundle(budget.root, directory, context.reports)
    return {
        "status": "ok",
        "report": (directory / "index.html").relative_to(budget.root).as_posix(),
        "clips": len(items),
        "original_candidates_verified": True,
        "samples_verified": True,
    }
