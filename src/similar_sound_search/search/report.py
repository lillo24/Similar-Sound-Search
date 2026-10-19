"""Original-mixture PCM16 playback bundles, safe local HTML and allowlisted serving."""

import hashlib
import html
import os
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
from scipy.io.wavfile import write as write_wav

from ..evaluation.artifacts import record, write_record
from ..inputs import decode
from ..storage import InputError, contained, digest, is_link, sha256
from . import sources
from .contracts import configuration
from .job import charge, read_charge


def pcm16(samples):
    """One explicit constant attenuation only when PCM16 would overload; no clipping."""
    peak = float(np.max(np.abs(samples)))
    gain = min(1.0, (32767 / 32768) / peak) if peak else 1.0
    integers = np.rint(samples.astype(np.float64) * gain * 32768).astype(np.int16)
    return integers, gain


def clip(budget, directory, source, samples, first, last, context=None):
    meta = source["source"]
    if not 0 <= first < last <= len(samples):
        raise InputError("playback clip: native source bounds invalid")
    selected = samples[first:last]
    integers, gain = pcm16(selected)
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
    path = directory / (key + ".wav")
    receipt = directory / (key + ".json")
    expected = integers.astype(np.float32) / 32768
    if path.exists() or receipt.exists():
        saved = record(receipt)
        if saved["identity"] != identity or sha256(path, budget) != saved["sha256"]:
            raise InputError("playback clip: corrupt/stale media or conversion receipt")
    else:
        size = integers.nbytes + 4096
        charge(budget, context=context, clips=1, clip_bytes=size)
        budget.reserve(size, samples.nbytes * 3 + selected.nbytes * 4 + 32 * 1024**2)
        directory.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".a06-clip-", suffix=".wav", dir=directory)
        os.close(fd)
        write_wav(name, meta["sample_rate_hz"], integers)
        os.replace(name, path)
        budget.refresh_disk()
        write_record(
            receipt,
            {"identity": identity, "sha256": sha256(path, budget), "bytes": path.stat().st_size},
            budget,
        )
    read_charge(
        budget, {"duration_seconds": len(expected) / meta["sample_rate_hz"]}, context=context
    )
    actual, current = decode(path, budget)
    if not np.array_equal(actual, expected) or current["sample_count"] != last - first:
        raise InputError(
            "playback verification: exported samples differ from declared original crop"
        )
    return {
        "path": "media/" + path.name,
        "receipt": "media/" + receipt.name,
        "sha256": sha256(path, budget),
        "frames": last - first,
        "rate": meta["sample_rate_hz"],
        "channels": meta["channels"],
        "source_start_frame": first,
        "source_end_frame": last,
        "clip_zero_source_seconds": first / meta["sample_rate_hz"],
        "gain": gain,
        "duration_seconds": (last - first) / meta["sample_rate_hz"],
        "samples_verified": True,
    }


def stamp(seconds):
    minutes, rest = divmod(seconds, 60)
    return f"{int(minutes):02d}:{rest:06.3f}"


def link(url, label):
    if not url or urlsplit(url).scheme not in {"http", "https"} or urlsplit(url).username:
        return ""
    return (
        '<a rel="noreferrer" href="'
        + html.escape(url, quote=True)
        + '">'
        + html.escape(label)
        + "</a>"
    )


def page(evidence):
    cards = []
    for i, item in enumerate(evidence["items"]):
        s = item["source"]
        rate = s["source"]["sample_rate_hz"]
        offset = s["offset"] or 0
        basis = (
            "recording time"
            if s["offset"] is not None
            else "excerpt-relative"
            if s["basis"] == "excerpt"
            else "available-file time; master offset unverified"
        )
        match = (
            stamp(item["start_frame"] / rate + offset)
            + " – "
            + stamp(item["end_frame"] / rate + offset)
        )
        c = item["clip"]
        context = (
            stamp(c["source_start_frame"] / rate + offset)
            + " – "
            + stamp(c["source_end_frame"] / rate + offset)
        )
        score = (
            ""
            if item.get("score") is None
            else (
                f"<p>Timbre distance {item['timbre_distance']:.5f}; lower is closer. "
                f"Pitch contribution {item['pitch_contribution']:.5f}.</p>"
            )
        )
        role = "Query" if item["role"] == "query" else "Candidate"
        title = html.escape(s["title"] or "Untitled")
        media = html.escape(c["path"], quote=True)
        cards.append(f'''<article><h2>{role} {i + 1}: {title}</h2>
<p>{html.escape(s["artist"] or "Unknown artist")} · {link(s.get("source_url"), "Source")}</p>
<p>Matched/selected: <strong>{match}</strong> ({basis}). Playback context: {context}.</p>{score}
<audio id="audio-{i}" controls preload="metadata" src="{media}"></audio>
<label class="small" for="seek-{i}">Seek within this clip</label>
<input id="seek-{i}" class="seek" type="range" min="0"
max="{c["duration_seconds"]}" step="0.01" value="0" data-audio="audio-{i}">
<p class="state" id="state-{i}">Loading media…</p><p class="small">Original mixture ·
{c["channels"]} channel(s) · PCM16 WAV · gain {c["gain"]:.8f}.
Clip zero = source {stamp(c["clip_zero_source_seconds"])}.</p></article>''')
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Similar Sound Search — local listening</title><style>
body{font:17px system-ui;max-width:920px;margin:35px auto;padding:0 20px;
background:#f5f3ef;color:#232c36}article{background:white;padding:20px;
margin:20px 0;border-radius:10px}h1{font-size:30px}h2{font-size:21px}
audio{width:100%}.small{font-size:13px;color:#555}.failed{color:#a00000}
.seek{width:100%}
.state{font-size:14px}a{color:#13567e}</style>
<h1>Similar Sound Search</h1><p>"""
        + html.escape(evidence["label"])
        + """</p><p>Ranked candidates, without a confirmed-match or probability claim.
One passage per distinct recording or known duplicate group.
Human relevance remains unmeasured.</p>"""
        + "".join(cards)
        + """<script>document.querySelectorAll('audio').forEach((a,i)=>{
const s=document.getElementById('state-'+i);
a.addEventListener('loadedmetadata',()=>{
s.textContent='Ready · '+a.duration.toFixed(3)+' s';});
a.addEventListener('error',()=>{
s.textContent='Media missing or stale — regenerate/verify this report bundle.';
s.className='state failed';});});
document.querySelectorAll('.seek').forEach(slider=>{
const seek=()=>{
const a=document.getElementById(slider.dataset.audio);
const value=Number(slider.value);
if(Number.isFinite(a.duration) && value>=0 && value<=a.duration){a.currentTime=value;}
};
slider.addEventListener('input',seek);
slider.addEventListener('change',seek);
});</script></html>"""
    )


def build(budget, result_path, context=None):
    value = record(
        contained(
            result_path,
            context.results if context is not None else budget.root / "data/runs/search/results",
        )
    )
    cfg = configuration(budget.root)
    directory = (
        context.reports if context is not None else budget.root / "reports/local/a06"
    ) / value["result_id"]
    items = []
    for example in value["query"]["examples"]:
        p = example["prepared"]
        source = {
            "source": {**p["technical_metadata"], **p["source"]},
            "title": value["query"]["label"],
            "artist": "Explicit query selection",
            "source_url": p["source"]["provenance"].get("origin_url"),
            "offset": p["timestamp_mapping"]["original_recording_offset_seconds"],
            "basis": p["timestamp_mapping"]["basis"],
        }
        original = Path(p["source"]["local_path"])
        original = original if original.is_absolute() else budget.root / original
        read_charge(budget, source["source"], context=context)
        samples, meta = decode(original, budget)
        if meta["sha256"] != source["source"]["sha256"]:
            raise InputError("query playback original changed")
        segment = p["timestamp_mapping"]["segments"][0]
        rate = meta["sample_rate_hz"]
        first = int(round(segment["source_start_seconds"] * rate))
        last = int(round((segment["source_start_seconds"] + segment["asset_end_seconds"]) * rate))
        items.append(
            {
                "role": "query",
                "source": source,
                "start_frame": first,
                "end_frame": last,
                "clip": clip(
                    budget, directory / "media", source, samples, first, last, context=context
                ),
            }
        )
    for hit in value["candidates"]:
        source = hit["source"]
        samples = (
            sources.load(budget, source)
            if context is None
            else sources.load(budget, source, context=context)
        )
        rate = source["source"]["sample_rate_hz"]
        context_frames = (cfg["playback_context_milliseconds"] * rate + 999) // 1000
        first, last = (
            max(0, hit["start_frame"] - context_frames),
            min(len(samples), hit["end_frame"] + context_frames),
        )
        items.append(
            {
                **hit,
                "role": "candidate",
                "clip": clip(
                    budget, directory / "media", source, samples, first, last, context=context
                ),
            }
        )
    evidence = {
        "schema_version": "a06-playback-1",
        "result_hash": value["record_hash"],
        "label": value["query"]["label"],
        "items": items,
        "encoding": "WAV/PCM16",
        "offline": True,
        "coverage_state": value["state"],
    }
    html_path = directory / "index.html"
    html_content = page(evidence)
    budget.reserve(len(html_content.encode()) + 65536)
    directory.mkdir(parents=True, exist_ok=True)
    temporary_html = directory / ".a06-report.html"
    temporary_html.write_text(html_content, encoding="utf-8", newline="\n")
    os.replace(temporary_html, html_path)
    budget.refresh_disk()
    evidence["html_sha256"] = hashlib.sha256(html_path.read_bytes()).hexdigest()
    write_record(directory / "bundle.json", evidence, budget)
    return {
        "status": "ok",
        "report": html_path.relative_to(budget.root).as_posix(),
        "clips": len(items),
        "samples_verified": True,
    }


def verify_bundle(root, path, report_root=None):
    path = contained(path, report_root if report_root is not None else root / "reports/local/a06")
    directory = path if path.is_dir() else path.parent
    value = record(directory / "bundle.json")
    allowed = {"/index.html": directory / "index.html"}
    if hashlib.sha256(allowed["/index.html"].read_bytes()).hexdigest() != value["html_sha256"]:
        raise InputError("report HTML changed; regenerate verified bundle")
    for name, expected in value.get("pages", {}).items():
        if (
            not name.endswith(".html")
            or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-." for c in name)
            or "/" in name
            or name.startswith(".")
        ):
            raise InputError("report page: bounded owned HTML filename required")
        page_path = contained(directory / name, directory)
        if is_link(page_path) or hashlib.sha256(page_path.read_bytes()).hexdigest() != expected:
            raise InputError("report page missing/stale: " + name)
        allowed["/" + name] = page_path
    for item in value["items"]:
        c = item["clip"]
        media = contained(directory / c["path"], directory / "media")
        if is_link(media) or hashlib.sha256(media.read_bytes()).hexdigest() != c["sha256"]:
            raise InputError("report media missing/stale: " + c["path"])
        allowed["/" + c["path"]] = media
    return allowed


def byte_range(header, size):
    """One bounded RFC byte range for verified WAV seeking; no multipart responses."""
    if header is None:
        return 0, size - 1, False
    if not isinstance(header, str) or len(header) > 64 or not header.startswith("bytes="):
        raise InputError("media range: expected one bytes=start-end range")
    value = header[6:]
    if value.count("-") != 1 or "," in value:
        raise InputError("media range: multipart/malformed request refused")
    first, last = value.split("-")
    if any(v and (not v.isascii() or not v.isdigit()) for v in (first, last)) or not (
        first or last
    ):
        raise InputError("media range: integer byte endpoints required")
    if not first:
        length = int(last)
        if length <= 0:
            raise InputError("media range: positive suffix length required")
        start, end = max(0, size - length), size - 1
    else:
        start, end = int(first), min(size - 1, int(last)) if last else size - 1
    if not 0 <= start <= end < size:
        raise InputError("media range: outside verified media bytes")
    return start, end, True


def serve(root, path, port, report_root=None):
    """User-started idle listener: loopback, exact bundle allowlist, no repository access."""
    allowed = verify_bundle(root, path, report_root)
    if not 1024 <= port <= 65535:
        raise InputError("report server: port must be 1024..65535")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            key = urlsplit(self.path).path
            if key == "/":
                key = "/index.html"
            if key not in allowed:
                self.send_error(404, "Outside owned report/media allowlist")
                return
            target = allowed[key]
            if not target.is_file():
                self.send_error(410, "Media missing/stale")
                return
            expected = hashlib.sha256(target.read_bytes()).hexdigest()
            # Recheck the frozen bundle before each request, including changes after startup.
            try:
                verify_bundle(root, path, report_root)
            except (InputError, OSError):
                self.send_error(410, "Media missing/stale; verify/regenerate bundle")
                return
            size = target.stat().st_size
            try:
                first, last, partial = byte_range(self.headers.get("Range"), size)
            except InputError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            self.send_response(206 if partial else 200)
            self.send_header(
                "Content-Type",
                "audio/wav" if target.suffix == ".wav" else "text/html; charset=utf-8",
            )
            self.send_header("Content-Length", str(last - first + 1))
            self.send_header("Accept-Ranges", "bytes")
            if partial:
                self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
            self.send_header("Cache-Control", "no-store")
            self.send_header("ETag", expected)
            self.end_headers()
            with target.open("rb") as stream:
                stream.seek(first)
                remaining = last - first + 1
                while remaining:
                    data = stream.read(min(1024 * 1024, remaining))
                    if not data:
                        raise InputError("report stream: verified media truncated during response")
                    self.wfile.write(data)
                    remaining -= len(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Serving verified owned bundle at http://127.0.0.1:{port}/ ; Ctrl+C stops", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
