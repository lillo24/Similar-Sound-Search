"""Preserved C02 scored/context original mixtures and independent native playback QA."""

import hashlib
import html
import json

import numpy as np

from ..evaluation.artifacts import record
from ..inputs import decode
from ..search import sources
from ..search.report import pcm16, stamp, verify_bundle
from ..separation.report import safe_clip
from ..storage import InputError, contained, digest
from .context import load_query


def page(value):
    def esc(v):
        return html.escape(str(v), quote=True)

    cards = []
    for i, item in enumerate(value["items"]):
        c = item["clip"]
        cards.append(f'''<article><h3>{esc(item["label"])}</h3><p>{esc(item["role"])}</p>
<p>{esc(item["timeline"])}</p><audio id="audio-{i}" controls preload="metadata"
src="{esc(c["path"])}"></audio>
<label for="seek-{i}">Seek within clip</label><input id="seek-{i}" type="range" min="0"
max="{c["duration_seconds"]}" step=".01" value="0" data-audio="audio-{i}">
<p id="state-{i}">Loading media…</p><small>Native {c["rate"]} Hz / {c["channels"]} channels.
Playback-only gain {c["gain"]:.8f}; {c["duration_seconds"]:.3f}s. Original mixture.</small>
<details><summary>Scored row and
contributions</summary><pre>{
            esc(json.dumps(item.get("evidence"), indent=2))
        }</pre></details></article>''')
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport"
content="width=device-width">
<title>C02 · Candidate retrieval</title><style>body{font:17px
system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;background:#f4f3ee;color:#172b35}
article,details{background:white;padding:1.2rem;margin:1rem 0;border:1px solid
#d6dfdf;border-radius:10px}
h1{font-size:30px}h3{font-size:20px}audio,input{width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}small{color:#46565c}.failed{color:#9a0000}</style>
<h1>C02 · Candidate retrieval</h1><p>Default: original legacy mean-example baseline, pitch off.
The labelled experimental event policy combines capped rank credits across the two complete
original banks.
Scores are not probabilities or calibrated sound presence. Short/component banks are scoped
diagnostics only.</p>
<p>Loulou remains the full 218–240s mixture with 217–241s context. Recording/version alignment,
master offset, rights, intended layer and complete event boundaries remain unverified.
Its 22 seconds exceed both indexed passage durations. No human relevance claim.</p>
<p>The C03 export retains twenty distinct groups; the visible lists show ten each.
Each scored player is an actual indexed row. Context and cluster envelopes are separate and
unscored.</p>
<details><summary>Coverage, frozen development and C03 evidence</summary><pre>"""
        + esc(json.dumps(value["summary"], indent=2))
        + """</pre></details>"""
        + "".join(cards)
        + """<script>
document.querySelectorAll('audio').forEach((a,i)=>{const s=document.getElementById('state-'+i);
a.addEventListener('loadedmetadata',()=>s.textContent='Ready · '+a.duration.toFixed(3)+' s');
a.addEventListener('error',()=>{s.textContent='Media missing or stale; verify bundle.';
s.className='failed';});});
document.querySelectorAll('input[type=range]').forEach(s=>s.addEventListener('input',()=>{
const a=document.getElementById(s.dataset.audio);const
t=Number(s.value);if(Number.isFinite(a.duration)&&t>=0&&t<=a.duration)a.currentTime=t;}));
</script></html>"""
    )


def build(budget, owner):
    execution_ref = record(owner.directory / "execution.json")["execution"]
    execution = owner.get(execution_ref, "executions")
    revision, saved, query, _ = load_query(budget, owner)
    if (
        query["record_hash"] != execution["identity"]["query_hash"]
        or saved["materialization_id"] != execution["identity"]["materialization_id"]
    ):
        raise InputError("C02 report: exact saved query differs")
    identity = {
        "version": "c02-playback-1",
        "execution_hash": execution["record_hash"],
        "comparison_hash": record(owner.directory / "development/comparison.json")["record_hash"],
        "diagnostics_hash": record(owner.directory / "development/representation-diagnostics.json")[
            "record_hash"
        ],
    }
    directory = owner.reports / ("retrieval-" + digest(identity))
    if (directory / "bundle.json").exists():
        raise InputError("C02 report complete; retain owned bundle")
    items = []
    clips = {}

    def add(label, role, a, x, first, last, evidence=None):
        key = (a["sha256"], first, last)
        if key not in clips:
            clips[key] = safe_clip(
                budget, directory / "media", {"source": a}, x, first, last, owner
            )
        items.append(
            {
                "label": label,
                "role": role,
                "source_audio": a,
                "clip": clips[key],
                "timeline": stamp(first / a["sample_rate_hz"])
                + " – "
                + stamp(last / a["sample_rate_hz"])
                + " available-file time; master offset unverified",
                "evidence": evidence,
            }
        )

    example = revision["recipe"]["examples"][0]
    if len(revision["recipe"]["examples"]) != 1 or example["kind"] != "asset":
        raise InputError("C02 delivery report expects the full original mixture")
    binding = query["identity"]["consumer"]["local_bindings"][example["asset_id"]]
    a = revision["recipe"]["assets"][example["asset_id"]]["audio"]
    owner.charge(budget, read_audio_seconds=a["duration_seconds"])
    x, actual = decode(contained(owner.root / binding["path"], owner.root), budget)
    if actual != a:
        raise InputError("C02 report query original changed")
    a = {**a, "local_path": binding["path"]}
    add(
        "Loulou · complete selected original",
        "Full 22s mixed query; pitch off",
        a,
        x,
        *example["event"],
    )
    add(
        "Loulou · original context",
        "Full 24s original context; unscored",
        a,
        x,
        *example["context"],
    )
    del x
    orders = {}
    for arm in ("legacy-mean", "event-multi"):
        orders[arm] = []
        for ref in execution["arms"][arm]["display"]:
            result = owner.get(ref, "c03-groups")
            row = result["passages"][0]["representative"]
            source = owner.get(result["sources"][row["recording_id"]], "sources")["source"]
            orders[arm].append(result["group"])
            x = sources.load(budget, source, context=owner)
            first, last = row["original_bounds"]
            label = (
                "Legacy baseline" if arm == "legacy-mean" else "Experimental combined banks"
            ) + f" · {result['rank']}. {source['artist']} — {source['title']}"
            detail = {
                "group": result["group"],
                "rank": result["rank"],
                "score": result["score"],
                "score_direction": execution["arms"][arm]["score_direction"],
                "scored_row": row,
                "contributions": result["contributions"],
                "display_envelope": result["passages"][0]["display_envelope"],
                "envelope_is_scored": False,
                "c03_group_ref": ref,
            }
            if arm == "event-multi":
                add(
                    label + " · scored passage",
                    "Actual scored original-mixture row",
                    source["source"],
                    x,
                    first,
                    last,
                    detail,
                )
            add(
                label + " · original context",
                "Unscored original context around the actual representative",
                source["source"],
                x,
                *row["original_context"],
                detail,
            )
            del x
    summary = {
        "execution_ref": execution_ref,
        "snapshot_hash": execution["identity"]["snapshot_hash"],
        "banks": execution["identity"]["banks"],
        "scored_windows": execution["scored_windows"],
        "baseline_equivalence": owner.get(execution["baseline_winners"], "baseline-winners")[
            "equivalence"
        ],
        "complete_group_counts": {k: v["eligible_groups"] for k, v in execution["arms"].items()},
        "shortlist_counts": {k: len(v["shortlist"]) for k, v in execution["arms"].items()},
        "display_orders": orders,
        "changed_display_order": orders["legacy-mean"] != orders["event-multi"],
        "event_map": execution["event_map"],
        "development": record(owner.directory / "development/comparison.json"),
        "representation_diagnostic_scope": (
            "two variants, one event; one-region candidate banks; no full-catalogue "
            "quality interpretation"
        ),
        "c03_contract": (
            "c02-c03-shortlist-1 -> c03-groups -> sources and group-supports; exact "
            "row/shard/native bounds, original context, contributions, exclusions and "
            "policy pinned"
        ),
        "resource_counts_before_report": record(owner.directory / "work.json")["counts"],
    }
    value = {
        "schema_version": "c02-playback-1",
        "identity": identity,
        "items": items,
        "summary": summary,
    }
    content = page(value)
    owner.charge(budget, metadata_bytes=len(content.encode()) + 4096)
    budget.reserve(len(content.encode()) + 65536)
    directory.mkdir(parents=True, exist_ok=True)
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
    return {
        "status": "ok",
        "report": (directory / "index.html").relative_to(owner.root).as_posix(),
        "items": len(items),
        "unique_wavs": len(clips),
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
                    raise InputError("C02 native QA: original " + k + " differs")
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
            raise InputError("C02 native QA: PCM16 gain/map/rate/channels/frames differ")
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
        "schema_version": "c02-native-qa-1",
        "bundle_hash": value["record_hash"],
        "passed": True,
        "items": answers,
    }
    owner.publish(budget, owner.directory / "native-qa.json", result, immutable=True)
    return {"status": "ok", "passed": True, "items": len(answers)}
