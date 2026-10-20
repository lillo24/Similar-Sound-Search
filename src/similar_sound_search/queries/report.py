"""Minimal revision/pitch summary with verified original and explicitly derived players."""

import hashlib
import html
import json

from ..evaluation.artifacts import record, write_record
from ..inputs import decode
from ..search import sources
from ..search.contracts import code_identity
from ..search.report import stamp
from ..separation.report import safe_clip
from ..storage import InputError, contained, digest
from . import assets, library, materialization
from .contracts import fields


def page(value):
    def esc(v):
        return html.escape(str(v), quote=True)

    cards = []
    for i, item in enumerate(value["items"]):
        clip = item["clip"]
        detail = item.get("score_detail")
        candidate_pitch = ""
        if detail is not None:
            estimate = detail["pitch"]
            candidate_pitch = (
                " Candidate pitch abstained: " + estimate["reason"]
                if estimate["hz"] is None
                else f" Candidate pitch {estimate['hz']:.2f} Hz: {estimate['reason']}"
            )
        score = (
            ""
            if detail is None
            else f"Timbre {detail['timbre_distance']:.8f} + "
            f"pitch {detail['pitch_contribution']:.8f} = {detail['score']:.8f}. "
            f"{detail['pitch_detail']['reason']}"
        )
        cards.append(f'''<article><h3>{esc(item["label"])}</h3><p>{esc(item["timeline"])}</p>
<p>{esc(item["signal_role"])}. {esc(score)}{esc(candidate_pitch)}</p>
<audio id="audio-{i}" controls preload="metadata" src="{esc(clip["path"])}"></audio>
<label for="seek-{i}">Seek within clip</label><input id="seek-{i}" type="range" min="0"
max="{clip["duration_seconds"]}" step=".01" value="0" data-audio="audio-{i}">
<p id="state-{i}">Loading media…</p><small>Native {clip["rate"]} Hz / {clip["channels"]} channels.
Raw processing gain 1; playback-only gain {clip["gain"]:.8f}.
Duration {clip["duration_seconds"]:.3f}s.</small></article>''')
    recipes = "".join(
        "<article><h3>"
        + esc(v["label"])
        + " · revision "
        + esc(v["revision_id"][:12])
        + "</h3><p>"
        + esc(v.get("unique_pcm_examples", "unavailable"))
        + " unique PCM example(s). Estimates: "
        + esc(
            "; ".join(
                str(p["hz"]) + " Hz — " + p["reason"]
                if p["hz"] is not None
                else "abstained — " + p["reason"]
                for p in v.get("pitch", [])
            )
        )
        + "</p><details><summary>Exact saved source, selection and processing choices"
        + "</summary><pre>"
        + esc(json.dumps(v, indent=2, ensure_ascii=False))
        + "</pre></details></article>"
        for v in value["summaries"]
    )
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport"
content="width=device-width">
<title>B03 · Reusable sound queries</title><style>
body{font:17px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;
background:#f4f3ee;color:#172b35}
article,details{background:white;padding:1.2rem;margin:1rem 0;
border:1px solid #d6dfdf;border-radius:10px}
h1{font-size:30px}h3{font-size:20px}audio,input{width:100%}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}
small{color:#46565c}.failed{color:#9a0000}
</style><h1>B03 · Reusable sound queries</h1><p>Defaults: original audio, pitch off.
Experimental pitch adds at most 0.03 to cosine distance; timbre selects the passage first.
Missing or ambiguous required pitch estimates contribute zero, with a visible reason.</p>
<p>Selected media and required cues were validated for this bundle. Source provenance,
recording version, master alignment and completeness remain explicit in each saved recipe.
Technical decoding does not establish an intended layer or human similarity.</p>
<h2>Immutable revisions and estimates</h2>"""
        + recipes
        + "<h2>Selected audio and original catalogue candidates</h2>"
        + "".join(cards)
        + """<script>
document.querySelectorAll('audio').forEach((a,i)=>{const s=document.getElementById('state-'+i);
a.addEventListener('loadedmetadata',()=>s.textContent='Ready · '+a.duration.toFixed(3)+' s');
a.addEventListener('error',()=>{s.textContent='Media missing or stale — verify this bundle.';
s.className='failed';});});
document.querySelectorAll('input[type=range]').forEach(slider=>slider.addEventListener('input',()=>{
const a=document.getElementById(slider.dataset.audio);const t=Number(slider.value);
if(Number.isFinite(a.duration)&&t>=0&&t<=a.duration)a.currentTime=t;}));</script></html>"""
    )


def build(budget, owner, spec):
    fields(spec, {"revisions", "executions"}, "report input")
    if (
        not isinstance(spec["revisions"], list)
        or not 1 <= len(spec["revisions"]) <= 4
        or not isinstance(spec["executions"], list)
        or not 1 <= len(spec["executions"]) <= 2
    ):
        raise InputError("B03 report: one to four revisions and one/two exact executions required")
    revisions = []
    for item in spec["revisions"]:
        fields(item, {"revision_id", "label"}, "report revision")
        revisions.append(
            (library.revision(owner, item["revision_id"]), library.label(item["label"]))
        )
    executions = [
        record(contained(owner.root / p, owner.directory / "executions"))
        for p in spec["executions"]
    ]
    for execution in executions:
        if (
            execution.get("schema_version") != "b03-execution-1"
            or execution["state"] != "complete"
            or digest(execution["identity"]) != execution["execution_id"]
        ):
            raise InputError("B03 report: corrupt/incomplete execution")
        revision = library.revision(owner, execution["identity"]["revision_id"])
        if execution["revision"] != revision or revision["revision_id"] not in {
            v[0]["revision_id"] for v in revisions
        }:
            raise InputError("B03 report: execution's exact revision must be included unchanged")
    identity = {
        "version": "b03-playback-1",
        "revisions": spec["revisions"],
        "executions": [v["record_hash"] for v in executions],
        "code": code_identity(),
    }
    directory = owner.reports / ("queries-" + digest(identity))
    media = directory / "media"
    items, summaries, clips = [], [], {}

    def add(label, role, path, audio, samples, a, b, origin=0, score=None, evidence=None):
        key = (audio["sha256"], a, b)
        source_audio = {**audio, "local_path": path.relative_to(owner.root).as_posix()}
        if key not in clips:
            clips[key] = safe_clip(budget, media, {"source": source_audio}, samples, a, b, owner)
        c = clips[key]
        zero = origin + a / audio["sample_rate_hz"]
        items.append(
            {
                "label": label,
                "signal_role": role,
                "clip": c,
                "source_audio": source_audio,
                "source_origin_seconds": origin,
                "origin_evidence": evidence or {"kind": "file"},
                "available_file_zero_seconds": zero,
                "timeline": stamp(zero)
                + " – "
                + stamp(origin + b / audio["sample_rate_hz"])
                + " available-file time; master offset unverified",
                "score_detail": score,
            }
        )

    validated_queries = {}
    for revision, label in revisions:
        matching = [
            v for v in executions if v["identity"]["revision_id"] == revision["revision_id"]
        ]
        exact_id = matching[0]["identity"]["materialization_id"] if matching else None
        if any(v["identity"]["materialization_id"] != exact_id for v in matching):
            raise InputError("B03 report: choose one exact materialization per displayed revision")
        saved = materialization.receipt(owner, revision, exact_id)
        if matching and any(
            v["materialization"] != saved
            or v["identity"]["query_hash"] != saved["identity"]["query_hash"]
            for v in matching
        ):
            raise InputError("B03 report: execution/materialization snapshot changed")
        query_hash = saved["identity"]["query_hash"]
        if query_hash not in validated_queries:
            _, validated_queries[query_hash], _ = materialization.load(
                budget, owner, revision, exact_id
            )
        query = validated_queries[query_hash]
        if query["identity"]["consumer"]["examples"] != revision["recipe"]["examples"]:
            raise InputError("B03 report: cached query does not match this exact revision")
        summaries.append(
            {
                "label": label,
                "revision_id": revision["revision_id"],
                "recipe_pitch": revision["recipe"]["pitch"],
                "query_id": query["query_id"],
                "unique_pcm_examples": len(query["examples"]),
                "contributing_selections": len(revision["recipe"]["examples"]),
                "pitch": [v["pitch"] for v in query["examples"]],
                "exclusions": query["identity"]["excluded_groups"],
                "selection": revision["recipe"]["examples"],
                "sources": revision["recipe"]["assets"],
            }
        )
        owner.binding_snapshots = query["identity"]["consumer"]["local_bindings"]
        try:
            for n, example in enumerate(revision["recipe"]["examples"]):
                if example["kind"] == "asset":
                    info, binding, samples = assets.read_asset(
                        budget, owner, example["asset_id"], with_samples=True
                    )
                    path = owner.root / binding["path"]
                    audio = info["audio"]
                    origin = 0
                    origin_evidence = {"kind": "file"}
                    if binding["parent_record"]:
                        parent = record(owner.root / binding["parent_record"])
                        origin = parent["timestamp_mapping"]["segments"][0]["source_start_seconds"]
                        origin_evidence = {
                            "kind": "a02",
                            "record": binding["parent_record"],
                            "record_hash": parent["record_hash"],
                        }
                    add(
                        label + f" · original context {n + 1}",
                        "Original provided context",
                        path,
                        audio,
                        samples,
                        *example["context"],
                        origin=origin,
                        evidence=origin_evidence,
                    )
                    add(
                        label + f" · selected example {n + 1}",
                        "Original selected example",
                        path,
                        audio,
                        samples,
                        *example["event"],
                        origin=origin,
                        evidence=origin_evidence,
                    )
                    del samples
                else:
                    value = assets.read_transform(budget, owner, example["transform"])
                    s = value["identity"]["source"]
                    binding = assets.read_binding(owner, digest(example["transform"]))
                    source_origin = s["parent"]["timestamp_mapping"]["segments"][0][
                        "source_start_seconds"
                    ]
                    origin_evidence = {
                        "kind": "b02",
                        "record": binding["path"],
                        "record_hash": value["record_hash"],
                    }
                    path = owner.root / s["spec"]["path"]
                    owner.charge(budget, read_audio_seconds=s["audio"]["duration_seconds"])
                    samples, audio = decode(path, budget)
                    add(
                        label + " · original context",
                        "Original mixture alongside optional processing",
                        path,
                        audio,
                        samples,
                        *value["identity"]["spec"]["region"],
                        origin=source_origin,
                        evidence={**origin_evidence, "component": "source"},
                    )
                    del samples
                    out = value["outputs"][example["transform"]["component"]]
                    path = owner.root / out["path"]
                    owner.charge(budget, read_audio_seconds=out["audio"]["duration_seconds"])
                    samples, audio = decode(path, budget)
                    first = value["identity"]["spec"]["region"][0]
                    rate = audio["sample_rate_hz"]
                    add(
                        label + " · derived context",
                        "Explicit B02 derived component",
                        path,
                        audio,
                        samples,
                        0,
                        len(samples),
                        origin=source_origin + first / rate,
                        evidence={
                            **origin_evidence,
                            "component": example["transform"]["component"],
                        },
                    )
                    a, b = value["identity"]["spec"]["event"]
                    add(
                        label + " · selected derived example",
                        "Explicit processed query",
                        path,
                        audio,
                        samples,
                        a - first,
                        b - first,
                        origin=source_origin + first / rate,
                        evidence={
                            **origin_evidence,
                            "component": example["transform"]["component"],
                        },
                    )
                    del samples
                    if value["identity"]["cue"]:
                        cue = value["identity"]["cue"]
                        path = owner.root / cue["spec"]["path"]
                        owner.charge(budget, read_audio_seconds=cue["audio"]["duration_seconds"])
                        samples, audio = decode(path, budget)
                        add(
                            label + " · conditioning cue",
                            "Mixed cue; no retrieval vote; clean instrument unverified",
                            path,
                            audio,
                            samples,
                            *value["identity"]["spec"]["cue"]["bounds"],
                            origin=cue["parent"]["timestamp_mapping"]["segments"][0][
                                "source_start_seconds"
                            ],
                            evidence={**origin_evidence, "component": "cue"},
                        )
                        del samples
        finally:
            owner.binding_snapshots = None
    candidate_clips = {}
    for execution in executions:
        preference = (
            "off" if execution["identity"]["pitch_policy"]["weight"] == 0 else "experimental .03"
        )
        for rank, hit in enumerate(execution["candidates"], 1):
            source = hit["source"]
            key = (hit["recording_id"], hit["start_frame"], hit["end_frame"])
            label = f"Pitch {preference} · {rank}. {source['artist']} — {source['title']}"
            if key in candidate_clips:
                item = {
                    **candidate_clips[key],
                    "label": label,
                    "score_detail": {
                        k: hit[k]
                        for k in (
                            "timbre_distance",
                            "pitch_contribution",
                            "score",
                            "pitch_detail",
                            "pitch",
                        )
                    },
                }
                items.append(item)
                continue
            samples = sources.load(budget, source, context=owner)
            rate = source["source"]["sample_rate_hz"]
            a, b = max(0, hit["start_frame"] - rate), min(len(samples), hit["end_frame"] + rate)
            add(
                label,
                "Original candidate mixture",
                owner.root / source["source"]["local_path"],
                source["source"],
                samples,
                a,
                b,
                score={
                    k: hit[k]
                    for k in (
                        "timbre_distance",
                        "pitch_contribution",
                        "score",
                        "pitch_detail",
                        "pitch",
                    )
                },
            )
            candidate_clips[key] = items[-1]
            del samples
    evidence = {
        "schema_version": "b03-playback-1",
        "identity": identity,
        "summaries": summaries,
        "items": items,
        "encoding": "native-channel/rate PCM16; explicit attenuation only",
        "offline": True,
    }
    content = page(evidence)
    owner.charge(budget, metadata_bytes=len(content.encode("utf-8")) + 4096)
    budget.reserve(len(content.encode("utf-8")) + 65536)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / ".partial-index.html"
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(directory / "index.html")
    budget.refresh_disk()
    evidence["html_sha256"] = hashlib.sha256((directory / "index.html").read_bytes()).hexdigest()
    write_record(directory / "bundle.json", evidence, budget)
    return {
        "status": "ok",
        "report": (directory / "index.html").relative_to(owner.root).as_posix(),
        "items": len(items),
        "unique_wavs": len(clips),
        "bundle_hash": record(directory / "bundle.json")["record_hash"],
    }
