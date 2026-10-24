"""Private inspectable per-case report from saved predictions/truth; no feature inference."""

import hashlib
import html
import json

from similar_sound_search.application import media
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import InputError, digest

from . import contracts, pipeline
from .context import MIB


def build(budget, owner):
    from .context import Context

    files = {}
    sections = []

    def linked(path, name=None):
        key = name or digest(path.relative_to(owner.root).as_posix()) + path.suffix
        if path.suffix == ".wav":
            # Hashing an original is a complete read even without PCM decoding.
            from similar_sound_search.inputs import probe

            info = probe(path, budget)
            owner.charge(budget, read_audio_seconds=info.frames / info.samplerate)
        files[key] = dict(
            path=path.relative_to(owner.root).as_posix(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        return "/evaluation/" + key

    def player(path, a, b, rate):
        return (
            '<audio controls preload="none" data-start="'
            + str(a / rate)
            + '" data-end="'
            + str(b / rate)
            + '" src="'
            + linked(path)
            + '"></audio>'
        )

    first_failure = None
    for split in ("development", "confirmation"):
        view = Context(owner.root, owner.allocation, split)
        locator = record(view.directory / "scores" / (split + "-summary.json"))
        assessment = view.get(locator["assessment"], "assessments")
        pop = {s["recording_id"]: s for s in contracts.population(view)["sources"]}
        neutral = {q["case_id"]: q for q in contracts.inputs(view)["queries"]}
        rows = []
        for case in assessment["cases"]:
            cid = case["case_id"]
            pred = pipeline.saved_prediction(view, cid)
            predpath = (
                view.root
                / record(view.directory / "prediction-bindings" / (split + "-" + cid + ".json"))[
                    "prediction"
                ]["path"]
            )
            content = (
                '<p><a href="'
                + linked(predpath)
                + '">Complete immutable prediction</a> · '
                + html.escape(str(case["families"]))
                + " · "
                + html.escape(
                    case["condition"]
                    if isinstance(case["condition"], str)
                    else str(case["condition"])
                )
                + "</p>"
            )
            for e in neutral[cid]["examples"]:
                content += (
                    "<p>Query selected native event "
                    + html.escape(str(e["event"]))
                    + "</p>"
                    + player(owner.root / e["path"], *e["event"], e["audio"]["sample_rate_hz"])
                )
            for arm in ("legacy-mean", "event-multi"):
                group = view.get(pred["arms"][arm]["complete_groups"][0], "group-results")
                row = group["passages"][0]["representative"]
                s = pop[row["recording_id"]]
                metrics = case["arms"][arm]["10"]
                content += (
                    "<h4>"
                    + arm
                    + "</h4><p>Rank 1: "
                    + group["group"][:12]
                    + "; score "
                    + str(group["score"])
                    + "; native scored interval "
                    + str(row["original_bounds"])
                    + "</p>"
                )
                content += player(
                    owner.root / s["source"]["local_path"],
                    *row["original_bounds"],
                    s["source"]["sample_rate_hz"],
                )
                content += (
                    "<pre>"
                    + html.escape(
                        json.dumps(dict(at_10=metrics, losses=case["attribution"][arm]), indent=2)
                    )
                    + "</pre>"
                )
            if (
                first_failure is None
                and split == "development"
                and case["primary"]
                and case["arms"]["legacy-mean"]["10"]["misses"]
            ):
                first_failure = (view, pred, case)
            rows.append(
                "<details><summary>"
                + split
                + " "
                + str(case["ordinal"])
                + " · "
                + html.escape(case["kind"])
                + " · "
                + cid[:12]
                + "</summary>"
                + content
                + "</details>"
            )
        sections.append(
            "<h2>"
            + split
            + "</h2><pre>"
            + html.escape(
                json.dumps(dict(summary=assessment["summary"], gate=assessment["gate"]), indent=2)
            )
            + "</pre>"
            + "".join(rows)
        )
        linked(view.root / locator["assessment"]["path"], split + "-scores.json")
    failure = None
    failure_html = ""
    if first_failure:
        view, pred, case = first_failure
        positives = set(case["positive_groups"])
        selected = next(
            (
                r
                for r in pred["arms"]["legacy-mean"]["complete_groups"]
                if view.get(r, "group-results")["group"] in positives
            ),
            pred["arms"]["legacy-mean"]["complete_groups"][0],
        )
        row = view.get(selected, "group-results")["passages"][0]["representative"]
        s = next(
            s
            for s in contracts.population(view)["sources"]
            if s["recording_id"] == row["recording_id"]
        )
        a = media.cached_clip(budget, view, s, row["original_bounds"])
        b = media.cached_clip(budget, view, s, row["original_context"])
        failure = dict(
            rule=(
                "First development primary baseline IoU miss at 10; first ranked know"
                "n-positive representative"
            ),
            case_id=case["case_id"],
            scored=a,
            context=b,
        )
        owner.publish(budget, owner.directory / "failure-example.json", failure, immutable=True)
        failure_html = (
            "<h2>Predeclared case with event misses</h2><p>Case "
            + case["case_id"][:12]
            + ". The selected highest-ranked known-positive representative follows the fixed rule "
            "and may itself match a target. All missed events remain in the case metrics.</p>"
        )
        for label, ref in (("Exact scored PCM16 crop", a), ("Unscored context PCM16 crop", b)):
            clip = view.get(ref, "media")
            url = linked(view.root / clip["local_path"], "failure-" + ref["record_hash"] + ".wav")
            duration = (clip["bounds"][1] - clip["bounds"][0]) / clip["original"]["source"][
                "sample_rate_hz"
            ]
            failure_html += (
                "<p>"
                + label
                + " · native "
                + str(clip["bounds"])
                + '</p><audio controls preload="none" data-start="0" data-end="'
                + str(duration)
                + '" src="'
                + url
                + '"></audio>'
            )
    title = "D02 · frozen product evaluation"
    source = (
        (
            '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="vie'
            'wport" content="width=device-width"><title>'
        )
        + title
        + '</title><link rel="stylesheet" href="/evaluation/report.css"><main><h1>'
        + title
        + (
            "</h1><p>Prospective confirmation within familiar A04 construction me"
            "chanisms. These are independent generated performances, not human ti"
            "mbre ratings or unseen music. Default: original mixture / legacy mea"
            "n / pitch off.</p><p>Players below read existing generated original "
            "files and bound playback to the displayed native scored interval. Co"
            "ntext and support envelopes are not predictions. Exact PCM16 scored/"
            "context clips are separately validated through the product result AP"
            "I. No calibrated absent-target rejection exists.</p>"
        )
        + "".join(sections)
        + failure_html
        + (
            "<h2>Resource and handoff</h2><p>One finite D02 pool. Saved results r"
            "emain readable after execution capacity is exhausted. D03 must speci"
            "fy a new bounded runtime resource policy; resetting this evaluation "
            "ledger is not a runtime policy. Loulou remains on 8774; C03 on 8772."
            ' No D04 listening has begun.</p></main><script src="/evaluation/repo'
            'rt.js"></script></html>'
        )
    )
    assets = {
        "index.html": source,
        "report.css": (
            "body{font:16px system-ui;background:#101722;color:#e6edf5;margin:0}m"
            "ain{max-width:1000px;margin:auto;padding:28px}details{border:1px sol"
            "id #435168;padding:16px;margin:14px 0}summary{cursor:pointer}pre{whi"
            "te-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}a{color:#85d"
            "4ed}audio{width:min(100%,560px)}h4{margin-bottom:5px}"
        ),
        "report.js": (
            "document.querySelectorAll('audio').forEach(a=>{a.addEventListener('p"
            "lay',()=>{if(a.currentTime<+a.dataset.start||a.currentTime>=+a.datas"
            "et.end)a.currentTime=+a.dataset.start});a.addEventListener('timeupda"
            "te',()=>{if(a.currentTime>=+a.dataset.end)a.pause()})});"
        ),
    }
    from similar_sound_search.application.files import atomic_bytes

    for name, data in assets.items():
        raw = data.encode("utf-8")
        if len(raw) > 4 * MIB:
            raise InputError("D02 report exceeds bounded file size")
        target = owner.reports / name
        owner.charge(budget, metadata_bytes=2 * len(raw) + 4096)
        budget.reserve(2 * len(raw) + 4096)
        budget.track_file(target)
        atomic_bytes(target, raw)
        budget.account_file(target, len(raw))
        linked(target, name)
    return owner.publish(
        budget,
        owner.directory / "report-bundle.json",
        dict(
            schema_version="d02-report-bundle-1",
            files=files,
            failure_example=failure,
            protocol=owner.protocol["record_hash"],
        ),
        immutable=True,
    )
