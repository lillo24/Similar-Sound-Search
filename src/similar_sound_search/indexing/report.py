"""C01 listener: separate bank ranks, truthful native originals and labelled components."""

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
from . import banks, queries
from . import build as builder


def page(value):
    def esc(v):
        return html.escape(str(v), quote=True)

    cards = []
    for i, item in enumerate(value["items"]):
        c = item["clip"]
        cards.append(f'''<article><h3>{esc(item["label"])}</h3><p>{esc(item["role"])}</p>
<p>{esc(item["timeline"])}. {esc(item.get("score", ""))}</p>
<audio id="audio-{i}" controls preload="metadata" src="{esc(c["path"])}"></audio>
<label for="seek-{i}">Seek within clip</label><input id="seek-{i}" type="range" min="0"
max="{c["duration_seconds"]}" step=".01" value="0" data-audio="audio-{i}">
<p id="state-{i}">Loading media…</p><small>Native {c["rate"]} Hz / {c["channels"]} channel(s).
Playback-only gain {c["gain"]:.8f}. {c["duration_seconds"]:.3f}s.</small></article>''')
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>C01 · Passage banks</title><style>body{font:17px system-ui;max-width:1000px;margin:2rem auto;
padding:0 1rem;background:#f4f3ee;color:#172b35}article,details{background:white;padding:1.2rem;
margin:1rem 0;border:1px solid #d6dfdf;border-radius:10px}h1{font-size:30px}h3{font-size:20px}
audio,input{width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}
small{color:#46565c}.failed{color:#9a0000}</style><h1>C01 · Passage banks</h1>
<p>Default: original audio, pitch off. Each bank ranks separately; scores are lower-better
cosine distances, without a presence threshold or cross-bank fusion. These are candidates
for inspection, not verified instruments or human similarity ratings.</p>
<p>Loulou: full 218–240s mixed reference and 217–241s context. Recording version,
master offset, intended layer, rights and complete notes remain unverified.
Extra durations and HPSS components remain experimental. Components cover selected regions only.</p>
<details><summary>Actual bank coverage, costs and development outcomes</summary><pre>"""
        + esc(json.dumps(value["summary"], indent=2, ensure_ascii=False))
        + """</pre></details>"""
        + "".join(cards)
        + """<script>
document.querySelectorAll('audio').forEach((a,i)=>{const s=document.getElementById('state-'+i);
a.addEventListener('loadedmetadata',()=>s.textContent='Ready · '+a.duration.toFixed(3)+' s');
a.addEventListener('error',()=>{s.textContent='Media missing or stale; verify bundle.';
s.className='failed';});});
document.querySelectorAll('input[type=range]').forEach(slider=>slider.addEventListener('input',()=>{
const a=document.getElementById(slider.dataset.audio);const t=Number(slider.value);
if(Number.isFinite(a.duration)&&t>=0&&t<=a.duration)a.currentTime=t;}));</script></html>"""
    )


def build(budget, owner):
    snapshot_path = owner.root / record(owner.directory / "snapshot.json")["snapshot"]
    snapshot = record(contained(snapshot_path, owner.indexes / "snapshots"))
    executions = [record(p) for p in sorted((owner.directory / "executions").glob("*.json"))]
    if len(executions) != 2 or any(
        v["identity"]["revision_id"] != owner.protocol["delivery"]["revision"]
        or not v["complete_eligible_group_winners"]
        for v in executions
    ):
        raise InputError(
            "C01 report requires two complete per-bank executions of the pinned original revision"
        )
    if any(v["bank_hash"] not in {b["record_hash"] for b in snapshot["banks"]} for v in executions):
        raise InputError("C01 report: execution bank differs from delivered snapshot")
    revision, saved, query, _ = queries.load(budget, owner)
    if any(
        v["query"] != query or v["materialization"] != saved or v["revision"] != revision
        for v in executions
    ):
        raise InputError("C01 report: exact revision/materialization/source binding changed")
    comparison = record(owner.directory / "development/comparison.json")
    admission = record(owner.directory / "admission.json")
    support = record(owner.directory / "support-verification.json")
    if (
        not support["passed"]
        or not support["admission_unchanged"]
        or support["comparison_hash"] != comparison["record_hash"]
        or support["decision_hash"] != admission["record_hash"]
    ):
        raise InputError("C01 report: full-event support verification/decision changed")
    identity = {
        "version": "c01-playback-1",
        "snapshot_hash": snapshot["record_hash"],
        "executions": [v["record_hash"] for v in executions],
        "support_verification_hash": support["record_hash"],
    }
    directory = owner.reports / ("index-" + digest(identity))
    items, clips = [], {}

    def add(label, role, audio, samples, first, last, origin=0, score=None, evidence=None):
        key = (audio["sha256"], first, last)
        if key not in clips:
            clips[key] = safe_clip(
                budget, directory / "media", {"source": audio}, samples, first, last, owner
            )
        c = clips[key]
        items.append(
            {
                "label": label,
                "role": role,
                "clip": c,
                "source_audio": audio,
                "origin_seconds": origin,
                "mapping_evidence": evidence,
                "timeline": stamp(origin + first / audio["sample_rate_hz"])
                + " – "
                + stamp(origin + last / audio["sample_rate_hz"])
                + " available-file time; master offset unverified",
                "score": score,
            }
        )

    # Resolve the exact immutable local binding captured by this materialization,
    # not the library's current name/head or a guessed filename.
    example = revision["recipe"]["examples"][0]
    if len(revision["recipe"]["examples"]) != 1 or example["kind"] != "asset":
        raise InputError("C01 delivery report: expected the declared whole original mixture")
    binding = query["identity"]["consumer"]["local_bindings"][example["asset_id"]]
    audio = revision["recipe"]["assets"][example["asset_id"]]["audio"]
    owner.charge(budget, read_audio_seconds=audio["duration_seconds"])
    samples, actual = decode(contained(owner.root / binding["path"], owner.root), budget)
    if actual != audio:
        raise InputError("C01 report: pinned query original changed")
    audio = {**audio, "local_path": binding["path"]}
    add(
        "Loulou · complete selected original",
        "Mixed query, full 22s; pitch off",
        audio,
        samples,
        *example["event"],
    )
    add(
        "Loulou · original context",
        "Original mixture context, full 24s",
        audio,
        samples,
        *example["context"],
    )
    del samples
    for execution in executions:
        b = next(v for v in snapshot["banks"] if v["record_hash"] == execution["bank_hash"])
        cfg = b["grid"]
        label = "Original legacy" if b["kind"] == "legacy-original" else "Experimental original"
        label += f" {cfg['window_milliseconds'] / 1000:g}s / {cfg['hop_milliseconds'] / 1000:g}s"
        for rank, candidate in enumerate(execution["candidates"], 1):
            source = candidate["source"]
            samples = sources.load(budget, source, context=owner)
            rate = source["source"]["sample_rate_hz"]
            a, z = candidate["start_frame"], candidate["end_frame"]
            add(
                f"{label} · {rank}. {source['artist']} — {source['title']}",
                "Original candidate mixture; scored passage "
                + stamp(a / rate)
                + "–"
                + stamp(z / rate),
                source["source"],
                samples,
                max(0, a - rate),
                min(len(samples), z + rate),
                score="Mean cosine distance " + format(candidate["timbre_distance"], ".9f"),
                evidence=execution["passages"][candidate["group"]],
            )
            del samples
    component_path = owner.directory / "components.json"
    if component_path.exists():
        for relative in record(component_path)["plans"]:
            plan = banks.validate_plan(owner, owner.root / relative)
            for signal in plan["signals"].values():
                component = builder.load_signal(budget, owner, signal)
                original = sources.load(budget, signal["original"], context=owner)
                lo, hi = banks.original_bounds(signal, [0, len(component)])
                name = signal["component"]
                add(
                    "Component region · " + plan["scope"] + " · " + name,
                    "Original mixture for indexed component; HPSS is not an instrument label",
                    signal["original"]["source"],
                    original,
                    lo,
                    hi,
                    evidence=signal["mapping"],
                )
                add(
                    "Separate component audition · " + plan["scope"] + " · " + name,
                    "Experimental derived HPSS component, region only; no relevance promotion",
                    signal["audio"],
                    component,
                    0,
                    len(component),
                    origin=lo / signal["original"]["source"]["sample_rate_hz"],
                    evidence=signal["mapping"],
                )
                del component, original
    summary = {
        "snapshot": snapshot,
        "admission": admission,
        "development": {
            k: {
                **v,
                "raw_available_source_support_including_short_file": v["full_event_support"],
                "full_event_support": support["strict_full_2400ms"][k]["full_2400ms_support"],
            }
            for k, v in comparison["summary"].items()
        },
        "support_verification": support,
        "original_equivalence": [
            v["baseline_equivalence"] for v in executions if v.get("baseline_equivalence")
        ],
        "work_before_report": record(owner.directory / "work.json")["counts"],
    }
    value = {
        "schema_version": "c01-playback-1",
        "identity": identity,
        "items": items,
        "summary": summary,
        "offline": True,
        "encoding": "native rate/channels PCM16 with explicit playback-only attenuation",
    }
    content = page(value)
    owner.charge(budget, metadata_bytes=len(content.encode("utf-8")) + 4096)
    budget.reserve(len(content.encode("utf-8")) + 65536)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / ".partial-index.html"
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(directory / "index.html")
    value["html_sha256"] = hashlib.sha256((directory / "index.html").read_bytes()).hexdigest()
    owner.publish(budget, directory / "bundle.json", value, immutable=True)
    pointer = {"bundle": (directory / "bundle.json").relative_to(owner.root).as_posix()}
    owner.publish(budget, owner.directory / "report.json", pointer)
    return {
        "status": "ok",
        "report": (directory / "index.html").relative_to(owner.root).as_posix(),
        "items": len(items),
        "unique_wavs": len(clips),
        "bundle_hash": record(directory / "bundle.json")["record_hash"],
    }


def verify_native(budget, owner):
    path = contained(owner.root / record(owner.directory / "report.json")["bundle"], owner.reports)
    value = record(path)
    verify_bundle(owner.root, path.parent, owner.reports)
    checked, answers = {}, []
    for item in value["items"]:
        a = item["source_audio"]
        if a["sha256"] not in checked:
            owner.charge(budget, read_audio_seconds=a["duration_seconds"])
            samples, actual = decode(contained(owner.root / a["local_path"], owner.root), budget)
            for key in (
                "sha256",
                "canonical_pcm",
                "sample_count",
                "sample_rate_hz",
                "channels",
                "decoder",
            ):
                if actual[key] != a[key]:
                    raise InputError("C01 native QA: original/component " + key + " changed")
            # Keep one source at a time; repeated items may re-read the source
            # rather than retaining many full decoded tracks in memory.
            checked = {a["sha256"]: samples}
        samples = checked[a["sha256"]]
        c = item["clip"]
        lo, hi = c["source_start_frame"], c["source_end_frame"]
        expected, gain = pcm16(samples[lo:hi])
        owner.charge(budget, read_audio_seconds=c["duration_seconds"])
        actual, audio = decode(path.parent / c["path"], budget)
        if (
            gain != c["gain"]
            or not np.array_equal(actual, expected.astype(np.float32) / 32768)
            or audio["sample_rate_hz"] != a["sample_rate_hz"]
            or audio["channels"] != a["channels"]
            or len(actual) != hi - lo
        ):
            raise InputError("C01 native QA: crop/gain/rate/channel/sample mismatch")
        answers.append(
            {
                "label": item["label"],
                "native_bounds": [lo, hi],
                "frames": len(actual),
                "rate": audio["sample_rate_hz"],
                "channels": audio["channels"],
                "exact_samples": True,
            }
        )
    result = {
        "schema_version": "c01-native-qa-1",
        "bundle_hash": value["record_hash"],
        "passed": True,
        "items": answers,
    }
    owner.publish(budget, owner.directory / "native-qa.json", result, immutable=True)
    return {"status": "ok", "passed": True, "items": len(answers)}
