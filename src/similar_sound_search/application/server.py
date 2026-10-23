"""Loopback-only HTTP product boundary, explicit mutations and allowlisted byte ranges."""

import hashlib
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ..evaluation.artifacts import record
from ..search.report import byte_range, verify_bundle
from ..storage import InputError, ResourceError, contained
from . import api, job, media, queries
from .context import Context, PersistenceError
from .locks import lock

STATIC = Path(__file__).parent / "web"


def upload_path(owner, key):
    api.identifier(key)
    value = record(owner.directory / "uploads" / (key + ".json"))
    path = contained(owner.root / value["path"], owner.audio / "imports")
    if not path.is_file():
        raise InputError("D01 uploaded reference is missing")
    return path


class Manager:
    def __init__(self, root, limits):
        self.root, self.limits = root, limits
        self.thread = None
        self.key = None
        self.errors = {}
        self.mutex = threading.Lock()

    def start(self, key):
        with self.mutex:
            if self.thread and self.thread.is_alive():
                if self.key == key:
                    return
                raise ResourceError("Another request is active; this request remains pending")
            self.key = key

            def run():
                try:
                    job.run(self.root, self.limits, key)
                except (InputError, OSError, ValueError, RuntimeError) as exc:
                    self.errors[key] = dict(
                        message=str(exc),
                        error_type=type(exc).__name__,
                        observed_process="stopped",
                        persistence_failure=isinstance(exc, PersistenceError),
                    )

            self.thread = threading.Thread(target=run, name="d01-coordinator", daemon=False)
            self.thread.start()

    def stop(self):
        if self.thread and self.thread.is_alive():
            api.cancel(self.root, self.key, hashlib.sha256(secrets.token_bytes(32)).hexdigest())
            self.thread.join(125)


def make_server(root, limits, port=8774):
    if not 1024 <= port <= 65535:
        raise InputError("D01 port must be 1024..65535")
    owner = Context(root)
    manager = Manager(owner.root, limits)
    token = secrets.token_urlsafe(32)
    origin = "http://127.0.0.1:" + str(port)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def host_ok(self):
            if self.headers.get("Host") != "127.0.0.1:" + str(port):
                raise InputError("D01 untrusted Host; use " + origin)
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise InputError("D01 cross-origin request refused")

        def send_json(self, value, status=200):
            raw = json.dumps(value, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.headers_common()
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(raw)

        def headers_common(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            inline = " 'unsafe-inline'" if self.path.startswith("/historical/") else ""
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'"
                + inline
                + "; style-src 'self'"
                + inline
                + "; "
                "img-src 'self' data:; media-src 'self'; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'",
            )

        def target(self):
            path = unquote(urlsplit(self.path).path)
            if any(p in {".", ".."} for p in path.split("/")) or "\\" in path or "%" in path:
                raise InputError("D01 path traversal/encoded path refused")
            return path

        def send_file(self, path, mime):
            size = path.stat().st_size
            try:
                first, last, partial = byte_range(self.headers.get("Range"), size)
            except InputError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(last - first + 1))
            self.send_header("Accept-Ranges", "bytes")
            if partial:
                self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
            self.headers_common()
            self.end_headers()
            if self.command == "HEAD":
                return
            with path.open("rb") as stream:
                stream.seek(first)
                remaining = last - first + 1
                while remaining:
                    block = stream.read(min(131072, remaining))
                    if not block:
                        raise InputError("D01 authorized media changed while streaming")
                    self.wfile.write(block)
                    remaining -= len(block)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            try:
                self.host_ok()
                path = self.target()
                if path == "/favicon.ico":
                    self.send_response(204)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                assets = {
                    "/": ("index.html", "text/html; charset=utf-8"),
                    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                    "/style.css": ("style.css", "text/css; charset=utf-8"),
                }
                if path in assets:
                    name, mime = assets[path]
                    return self.send_file(STATIC / name, mime)
                if path == "/api/bootstrap":
                    return self.send_json(
                        dict(
                            token=token,
                            catalogue=api.catalogue(root),
                            library=api.library(root),
                            completed=api.completed_searches(root),
                        )
                    )
                if path.startswith("/api/job/"):
                    key = api.identifier(path[9:])
                    value = api.status(root, key)
                    if key in manager.errors:
                        value["observed_failure"] = manager.errors[key]
                    return self.send_json(value)
                if path.startswith("/api/result/"):
                    return self.send_json(api.result(root, api.identifier(path[12:])))
                if path.startswith("/api/revision/"):
                    return self.send_json(queries.exact_revision(owner, api.identifier(path[14:])))
                if path.startswith("/api/waveform/"):
                    value = record(
                        owner.directory / "waveforms" / (api.identifier(path[14:]) + ".json")
                    )
                    return self.send_json(value)
                if path.startswith("/media/"):
                    target, value = media.validate(owner, api.identifier(path[7:]))
                    if value["original"]["kind"] != "reference":
                        raise InputError("D01 candidate media requires its complete result scope")
                    return self.send_file(target, "audio/wav")
                if path.startswith("/result-media/"):
                    parts = path[14:].split("/")
                    if len(parts) != 2:
                        raise InputError("D01 media requires opaque result and media IDs")
                    target, _ = api.result_media(root, *parts)
                    return self.send_file(target, "audio/wav")
                if path.startswith("/historical/"):
                    from ..refinement.context import Context as HistoricalContext

                    view = HistoricalContext(root)
                    locator = record(view.directory / "report.json")
                    bundle = contained(root / locator["bundle"], view.reports).parent
                    allowed = verify_bundle(root, bundle, view.reports)
                    if (
                        record(bundle / "bundle.json")["record_hash"]
                        != owner.protocol["playback_bundle"]
                    ):
                        raise InputError("D01 pinned historical report changed")
                    key = "/" + path[len("/historical/") :]
                    if key == "/":
                        key = "/index.html"
                    if key not in allowed:
                        raise FileNotFoundError("Outside historical bundle allowlist")
                    return self.send_file(
                        allowed[key],
                        "audio/wav" if key.endswith(".wav") else "text/html; charset=utf-8",
                    )
                raise FileNotFoundError("Outside application/media allowlist")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return
            except (InputError, OSError, ValueError, KeyError) as exc:
                self.send_json(
                    dict(error=str(exc), error_type=type(exc).__name__),
                    404 if isinstance(exc, FileNotFoundError) else 409,
                )
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_POST(self):
            try:
                self.host_ok()
                if self.headers.get("Origin") != origin or not secrets.compare_digest(
                    self.headers.get("X-D01-Token", ""), token
                ):
                    self.close_connection = True
                    rejected_length = self.headers.get("Content-Length", "")
                    if rejected_length.isdecimal() and int(rejected_length) <= 65536:
                        self.connection.settimeout(5)
                        self.rfile.read(int(rejected_length))
                    return self.send_json(
                        dict(error="Untrusted origin/session; refresh this local application"), 403
                    )
                length = self.headers.get("Content-Length", "")
                if (
                    not length.isascii()
                    or not length.isdecimal()
                    or self.headers.get("Transfer-Encoding")
                ):
                    raise InputError("D01 bounded Content-Length required")
                length = int(length)
                path = self.target()
                if path == "/api/upload":
                    return self.upload(length)
                if self.headers.get_content_type() != "application/json" or not 0 < length <= 65536:
                    raise InputError("D01 JSON request must be 1..65536 bytes")
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise InputError("D01 JSON request must be an object")
                if path == "/api/submit":
                    result = api.submit(root, limits, request)
                    try:
                        manager.start(result["job_id"])
                    except ResourceError:
                        result["pending_reason"] = "Another request is active; resume when it stops"
                    return self.send_json(result, 202)
                if path in {"/api/cancel", "/api/resume"}:
                    if set(request) != {"job_id", "request_id"}:
                        raise InputError("D01 control requires job and idempotent request ID")
                    key = api.identifier(request["job_id"])
                    if path == "/api/cancel":
                        return self.send_json(api.cancel(root, key, request["request_id"]))
                    result = api.resume_control(root, key, request["request_id"])
                    manager.start(key)
                    return self.send_json(result, 202)
                raise FileNotFoundError("Unknown explicit application mutation")
            except (InputError, OSError, ValueError, KeyError) as exc:
                self.close_connection = True
                self.send_json(dict(error=str(exc), error_type=type(exc).__name__), 409)
            except (BrokenPipeError, ConnectionResetError):
                return

        def upload(self, length):
            if self.headers.get_content_type() != "application/octet-stream":
                raise InputError("D01 upload requires audio bytes")
            from ..inputs import SUPPORTED
            from ..resources import CatalogueBudget

            label = unquote(self.headers.get("X-Filename", "reference"))
            suffix = Path(label).suffix.lower()
            if suffix not in SUPPORTED or len(label) > 160 or any(ord(c) < 32 for c in label):
                raise InputError("D01 unsupported filename/format; select WAV, FLAC, AIFF or MP3")
            if not 0 < length <= min(limits["max_input_bytes"], 128 * 1024**2):
                raise ResourceError("D01 upload exceeds bounded import/input allowance")
            key = api.identifier(self.headers.get("X-Upload-ID"))
            if len(list((owner.directory / "uploads").glob("*.json"))) >= 64:
                raise ResourceError("D01 upload count exhausted; load an existing reference")
            allocation = "upload-" + key
            context = Context(root, allocation)
            existing = context.directory / "uploads" / (key + ".json")
            if existing.exists():
                raise InputError("D01 upload already exists; load the registered reference")
            context.admit(allocation, 512 * 1024)
            budget = CatalogueBudget(root, limits)
            context.charge(budget, import_bytes=length)
            budget.reserve(length + 4096)
            target = context.audio / "imports" / (key + suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            # Never overwrite: exclusive mode retains interrupted imports for diagnosis.
            with target.open("xb") as stream:
                remaining = length
                while remaining:
                    block = self.rfile.read(min(131072, remaining))
                    if not block:
                        raise InputError("D01 truncated upload; retained incomplete import")
                    stream.write(block)
                    h.update(block)
                    remaining -= len(block)
                stream.flush()
                os.fsync(stream.fileno())
            context.publish(
                budget,
                existing,
                dict(
                    upload_id=key,
                    path=target.relative_to(root).as_posix(),
                    sha256=h.hexdigest(),
                    bytes=length,
                    label=label,
                ),
                immutable=True,
            )
            context.release(allocation)
            self.send_json(dict(upload_id=key, label=label, bytes=length), 201)

        def log_message(self, *args):
            pass

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        raise InputError(f"D01 cannot bind {origin}; port is in use or unavailable: {exc}") from exc
    server.manager = manager
    server.daemon_threads = True
    return server


def serve(root, limits, port=8774):
    from ..matchers.runner import peak_memory

    with lock(root, "server"):
        server = make_server(root, limits, port)
        print(
            f"Sound Search: http://127.0.0.1:{port}/ · foreground PID {os.getpid()} · Ctrl+C stops",
            flush=True,
        )
        print(
            f"Server initial peak working memory: {peak_memory()} bytes "
            "(worker overlap reported separately)",
            flush=True,
        )
        try:
            server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            print("Stopping admission; waiting for the owned bounded worker…", flush=True)
        finally:
            server.server_close()
            server.manager.stop()
