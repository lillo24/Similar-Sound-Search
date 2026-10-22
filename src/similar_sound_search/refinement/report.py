"""C03 preserved original before/after/context media; independent native verification."""

import hashlib
import html
import json

import numpy as np

from ..evaluation.artifacts import record
from ..inputs import decode
from ..retrieval.context import load_query
from ..search import sources
from ..search.report import pcm16, stamp, verify_bundle
from ..separation.report import safe_clip
from ..storage import InputError, contained, digest
from .context import Historical


def page(value):
    def esc(v):
        return html.escape(str(v), quote=True)

    cards = []
    for i, item in enumerate(value["items"]):
        c = item["clip"]
        cards.append(f'''<article><h2>{esc(item["label"])}</h2><p>{esc(item["role"])}</p>
<p>{esc(item["timeline"])}</p>
<audio id="audio-{i}" controls preload="metadata" src="{esc(c["path"])}"></audio>
<label for="seek-{i}">Seek within clip</label><input id="seek-{i}" type="range" min="0"
max="{c["duration_seconds"]}" step=".01" value="0" data-audio="audio-{i}">
<p id="state-{i}">Loading media...</p><small>Native {c["rate"]} Hz / {c["channels"]} channels;
{c["duration_seconds"]:.3f}s; playback-only gain {c["gain"]:.8f}.</small>
<details><summary>Original scores and exact support</summary>
<pre>{esc(json.dumps(item.get("evidence"), indent=2))}</pre></details></article>''')
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport"
content="width=device-width">
<title>C03 · Original timing refinement</title><style>body{font:17px system-ui;
max-width:1000px;
margin:2rem auto;
padding:0 1rem;
background:#f4f3ee;
color:#172b35}
article,details{background:white;
padding:1.2rem;
margin:1rem 0;
border:1px solid #d6dfdf;
border-radius:10px}
h1{font-size:30px}
h2{font-size:20px}
audio,input{width:100%}
pre{white-space:pre-wrap;
overflow-wrap:anywhere;
font-size:13px}
small{color:#46565c}
.failed{color:#9a0000}</style>
<h1>C03 · Original timing refinement</h1>
<p>Experimental placement within the same twenty C02 event-multi groups. Song order is unchanged;
ten songs are shown. Original retrieval remains the default. Two anchors per group, fixed duration,
at most nine native starts. Lower cosine distance is not evidence of human relevance.</p>
<p>Before and after players are actual scored original-mixture intervals. Context is unscored.
Every original representative is retained. Sliding a fixed window does not establish
sound boundaries.
No extraction, presence threshold or source-ranking promotion.</p>
<p>Loulou remains the full 218..240s mixture with 217..241s context. Recording/version alignment,
master offset, rights, intended layer and complete event boundaries remain unverified.</p>
<details><summary>All twenty groups, coverage and C04 handoff</summary><pre>"""
        + esc(json.dumps(value["summary"], indent=2))
        + """</pre></details>"""
        + "".join(cards)
        + """<script>
document.querySelectorAll('audio').forEach((a,i)=>{const s=document.getElementById('state-'+i);
a.addEventListener('loadedmetadata',()=>s.textContent='Ready · '+a.duration.toFixed(3)+' s');
a.addEventListener('error',()=>{s.textContent='Media missing or stale;
 verify bundle.';
s.className='failed';
});
});

document.querySelectorAll('input[type=range]').forEach(s=>s.addEventListener('input',()=>{
const a=document.getElementById(s.dataset.audio);const t=Number(s.value);
if(Number.isFinite(a.duration)&&t>=0&&t<=a.duration)a.currentTime=t;}));
</script></html>"""
    )


def build(budget, owner):
    ref = record(owner.directory / "execution.json")["execution"]
    execution = owner.get(ref, "executions")
    identity = {
        "version": "c03-playback-1",
        "execution": ref,
        "comparison": record(owner.directory / "development/comparison.json")["record_hash"],
    }
    directory = owner.reports / ("refinement-" + digest(identity))
    progress = owner.directory / "report-progress.json"
    if progress.exists():
        state = record(progress)
        if state["identity"] != identity or state["state"] == "complete":
            raise InputError("C03 report changed or already complete")
    else:
        state = {"identity": identity, "state": "pending", "items": [], "clips": {}, "groups": []}

    def add(label, role, a, x, b, evidence=None):
        key = digest([a["sha256"], b])
        if key not in state["clips"]:
            state["clips"][key] = safe_clip(
                budget, directory / "media", {"source": a}, x, *b, owner
            )
        state["items"].append(
            {
                "label": label,
                "role": role,
                "source_audio": a,
                "clip": state["clips"][key],
                "timeline": stamp(b[0] / a["sample_rate_hz"])
                + " - "
                + stamp(b[1] / a["sample_rate_hz"])
                + " available-file time; master offset unverified",
                "evidence": evidence,
            }
        )

    if not state["items"]:
        rev, _, query, _ = load_query(budget, owner)
        example = rev["recipe"]["examples"][0]
        binding = query["identity"]["consumer"]["local_bindings"][example["asset_id"]]
        a = rev["recipe"]["assets"][example["asset_id"]]["audio"]
        owner.charge(budget, read_audio_seconds=a["duration_seconds"])
        x, actual = decode(contained(owner.root / binding["path"], owner.root), budget)
        if actual != a:
            raise InputError("C03 report saved full query changed")
        a = {**a, "local_path": binding["path"]}
        add("Loulou · full selected mixture", "Full 22s query, pitch off", a, x, example["event"])
        add("Loulou · original context", "Unscored 24s context", a, x, example["context"])
        del x
        owner.publish(budget, progress, state)
    old = Historical(owner)
    for r in [r for r in execution["display"] if r["record_hash"] not in state["groups"]][:3]:
        g = owner.get(r, "groups")
        a = g["anchors"][0]
        row = a["selected"]
        source = old.get(g["input"]["sources"][row["recording_id"]], "sources")["source"]
        x = sources.load(budget, source, context=owner)
        label = f"{g['rank']}. {source['artist']} - {source['title']}"
        detail = {
            "rank": g["rank"],
            "group": g["group"],
            "c04_group": r,
            "state": g["state"],
            "anchor": a,
            "unchanged_group_order": True,
        }
        add(
            label + " · before",
            "C02 scored original interval",
            source["source"],
            x,
            a["input"]["original_bounds"],
            detail,
        )
        add(
            label + " · after",
            "C03 scored original interval; " + a["state"],
            source["source"],
            x,
            row["original_bounds"],
            detail,
        )
        add(
            label + " · context",
            "Unscored original context around C03 interval",
            source["source"],
            x,
            row["original_context"],
            detail,
        )
        del x
        state["groups"].append(r["record_hash"])
        owner.publish(budget, progress, state)
    if len(state["groups"]) < len(execution["display"]):
        return {"status": "ok", "state": "in_progress", "groups": len(state["groups"])}
    summary = {
        "execution": ref,
        "input_execution": execution["identity"]["input_execution"],
        "groups": [
            {
                "group": owner.get(r, "groups")["group"],
                "rank": owner.get(r, "groups")["rank"],
                "state": owner.get(r, "groups")["state"],
                "reference": r,
            }
            for r in execution["groups"]
        ],
        "development_comparison": record(owner.directory / "development/comparison.json"),
        "C04": execution["dependency_graph"],
        "resource_counts_before_report": record(owner.directory / "work.json")["counts"],
    }
    value = {
        "schema_version": "c03-playback-1",
        "identity": identity,
        "items": state["items"],
        "summary": summary,
    }
    content = page(value)
    owner.charge(budget, metadata_bytes=len(content.encode()) + 4096)
    budget.reserve(len(content.encode()) + 65536)
    temp = directory / ".partial-index.html"
    temp.write_text(content, encoding="utf-8", newline="\n")
    temp.replace(directory / "index.html")
    value["html_sha256"] = hashlib.sha256((directory / "index.html").read_bytes()).hexdigest()
    saved = owner.publish(budget, directory / "bundle.json", value, immutable=True)
    owner.publish(
        budget,
        owner.directory / "report.json",
        {"bundle": (directory / "bundle.json").relative_to(owner.root).as_posix()},
    )
    state["state"] = "complete"
    owner.publish(budget, progress, state)
    return {
        "status": "ok",
        "state": "complete",
        "report": (directory / "index.html").relative_to(owner.root).as_posix(),
        "items": len(value["items"]),
        "unique_wavs": len(state["clips"]),
        "bundle_hash": saved["record_hash"],
    }


def verify_native(budget, owner):
    path = contained(owner.root / record(owner.directory / "report.json")["bundle"], owner.reports)
    value = record(path)
    verify_bundle(owner.root, path.parent, owner.reports)
    cached = {}
    answers = []
    for item in value["items"]:
        a = item["source_audio"]
        if a["sha256"] not in cached:
            owner.charge(budget, read_audio_seconds=a["duration_seconds"])
            x, actual = decode(contained(owner.root / a["local_path"], owner.root), budget)
            for k in (
                "sha256",
                "canonical_pcm",
                "sample_count",
                "sample_rate_hz",
                "channels",
                "decoder",
            ):
                if actual[k] != a[k]:
                    raise InputError("C03 native QA: original " + k + " differs")
            cached = {a["sha256"]: x}
        c = item["clip"]
        lo, hi = c["source_start_frame"], c["source_end_frame"]
        expected, gain = pcm16(cached[a["sha256"]][lo:hi])
        owner.charge(budget, read_audio_seconds=c["duration_seconds"])
        actual, meta = decode(path.parent / c["path"], budget)
        if (
            gain != c["gain"]
            or not np.array_equal(actual, expected.astype(np.float32) / 32768)
            or meta["sample_count"] != hi - lo
            or meta["sample_rate_hz"] != a["sample_rate_hz"]
            or meta["channels"] != a["channels"]
        ):
            raise InputError("C03 native QA: PCM16 gain/map/rate/channels/frames differ")
        answers.append(
            {
                "label": item["label"],
                "native_bounds": [lo, hi],
                "frames": len(actual),
                "rate": meta["sample_rate_hz"],
                "channels": meta["channels"],
                "exact_samples": True,
            }
        )
    result = {
        "schema_version": "c03-native-qa-1",
        "bundle_hash": value["record_hash"],
        "passed": True,
        "items": answers,
    }
    owner.publish(budget, owner.directory / "native-qa.json", result, immutable=True)
    return {"status": "ok", "passed": True, "items": len(answers)}
