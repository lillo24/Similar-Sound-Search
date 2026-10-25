"""Loopback companion with finite media paths; it cannot dispatch application jobs."""

import json
import os
import re
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import feedback, manifest
from .common import ReviewError, inside, read

WEB = Path(__file__).parent / "web"


class LoopbackServer(ThreadingHTTPServer):
    allow_reuse_address = os.name != "nt"
    daemon_threads = True

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def byte_range(header, size):
    if header is None:
        return 0, size - 1, False
    if not re.fullmatch(r"bytes=[0-9]*-[0-9]*", header):
        raise ReviewError("Invalid single byte range")
    a, b = header[6:].split("-")
    if not a:
        if not b or int(b) <= 0:
            raise ReviewError("Invalid suffix range")
        first, last = max(0, size - int(b)), size - 1
    else:
        first, last = int(a), min(int(b), size - 1) if b else size - 1
    if not 0 <= first <= last < size:
        raise ReviewError("Unsatisfiable byte range")
    return first, last, True


def make_server(root, port=8777, feedback_name="feedback"):
    if not 1024 <= port <= 65535:
        raise ReviewError("Use a loopback port in 1024..65535")
    if feedback_name not in {"feedback", "qa-feedback"}:
        raise ReviewError("Only D04-owned feedback directories are allowed")
    root = root.resolve()
    bundle = inside(root, "bundle")
    review = manifest.validate(read(bundle / "review.json"))
    published = manifest.validate(
        read(Path(__file__).resolve().parents[2] / "manifests/listening/d04-v1.json")
    )
    if review != published:
        raise ReviewError("Private bundle differs from the published immutable review")
    items = manifest.media_items(review)
    store = feedback.Store(root, inside(root, "metadata/" + feedback_name), review)
    token, mutex = secrets.token_urlsafe(32), threading.Lock()
    origin = "http://127.0.0.1:" + str(port)

    def audio(role):
        item = items[role]
        path = inside(bundle, "media/" + item["sha256"] + ".wav")
        manifest.audio_header(path, item)
        return path

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def handle(self):
            try:
                super().handle()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # Native seek/refresh may close its prior range request.
                self.close_connection = True

        def log_message(self, *args):
            # Avoid unbounded logs and accidentally logging raw feedback/tokens.
            pass

        def host(self):
            if self.headers.get("Host") != "127.0.0.1:" + str(port):
                raise ReviewError("Untrusted Host; use the printed 127.0.0.1 link")
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise ReviewError("Cross-site requests are refused")

        def target(self):
            value = urlsplit(self.path)
            path = unquote(value.path)
            if (
                value.query
                or value.fragment
                or "\\" in path
                or "%" in path
                or any(p in {".", ".."} for p in path.split("/"))
            ):
                raise ReviewError("Encoded, traversing or parameterized paths are refused")
            return path

        def headers_common(self):
            for k, v in {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cross-Origin-Resource-Policy": "same-origin",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
                "style-src 'self'; media-src 'self'; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            }.items():
                self.send_header(k, v)

        def body(self, raw, mime, status=200, download=None):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(raw)))
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="' + download + '"')
            self.headers_common()
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(raw)

        def json(self, value, status=200):
            self.body(
                json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"),
                "application/json; charset=utf-8",
                status,
            )

        def file(self, path, mime, maximum, download=None):
            size = path.stat().st_size
            if size > maximum:
                raise ReviewError("Allowlisted file exceeds its size bound")
            try:
                first, last, partial = byte_range(self.headers.get("Range"), size)
            except ReviewError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.headers_common()
                self.end_headers()
                return
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(last - first + 1))
            self.send_header("Accept-Ranges", "bytes")
            if partial:
                self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="' + download + '"')
            self.headers_common()
            self.end_headers()
            if self.command != "HEAD":
                with path.open("rb") as stream:
                    stream.seek(first)
                    left = last - first + 1
                    while left:
                        block = stream.read(min(left, 131072))
                        if not block:
                            raise ReviewError("Saved review file changed during playback")
                        self.wfile.write(block)
                        left -= len(block)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            try:
                self.host()
                path = self.target()
                assets = {
                    "/": (WEB / "index.html", "text/html; charset=utf-8", None),
                    "/review.js": (WEB / "review.js", "text/javascript; charset=utf-8", None),
                    "/review.css": (WEB / "review.css", "text/css; charset=utf-8", None),
                    "/review.json": (bundle / "review.json", "application/json", "D04-review.json"),
                    "/D04_LISTENING.md": (
                        bundle / "D04_LISTENING.md",
                        "text/markdown; charset=utf-8",
                        "D04_LISTENING.md",
                    ),
                    "/feedback-template.json": (
                        bundle / "feedback-template.json",
                        "application/json",
                        "D04-feedback-template.json",
                    ),
                }
                if path in assets:
                    target, mime, download = assets[path]
                    return self.file(target, mime, 1024 * 1024, download)
                if path == "/api/bootstrap":
                    availability = {}
                    for role in items:
                        try:
                            audio(role)
                            availability[role] = dict(available=True)
                        except (ReviewError, OSError, EOFError) as exc:
                            availability[role] = dict(available=False, error=type(exc).__name__)
                    with mutex:
                        latest = store.latest()
                    return self.json(
                        dict(
                            review=review,
                            token=token,
                            latest=latest,
                            feedback_scope=feedback_name,
                            availability=availability,
                        )
                    )
                prefix = "/media/" + review["record_hash"] + "/"
                if path.startswith(prefix) and path[len(prefix) :] in items:
                    return self.file(audio(path[len(prefix) :]), "audio/wav", 16 * 1024 * 1024)
                if path.startswith("/feedback/") and re.fullmatch(r"[a-f0-9]{64}\.json", path[10:]):
                    with mutex:
                        values = store.snapshots()
                    value = next((v for v in values if v["record_hash"] == path[10:-5]), None)
                    if value is not None:
                        return self.body(
                            (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode(),
                            "application/json",
                            download="D04-feedback.json",
                        )
                self.json(dict(error="Outside this review's finite file/media allowlist"), 404)
            except (ReviewError, OSError, ValueError, KeyError, EOFError):
                self.json(
                    dict(error="Saved review item unavailable or invalid; no substitute used"), 409
                )

        def do_POST(self):
            try:
                self.host()
                if self.headers.get("Origin") != origin or not secrets.compare_digest(
                    self.headers.get("X-D04-Token", ""), token
                ):
                    return self.json(
                        dict(error="Stale session or untrusted origin; reload first"), 403
                    )
                path = self.target()
                if path not in {"/api/feedback", "/api/validate-feedback"}:
                    return self.json(
                        dict(error="No application operations exist on this server"), 404
                    )
                if self.headers.get("Content-Type") != "application/json":
                    raise ReviewError("Feedback requires JSON")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ReviewError("Feedback body must fit 64 KiB")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ReviewError("Incomplete feedback body")
                value = json.loads(raw)
                if path == "/api/validate-feedback":
                    return self.json(feedback.validate(value, review))
                if set(value) != {"document", "parent", "provenance"}:
                    raise ReviewError("Invalid feedback submission fields")
                with mutex:
                    saved = store.save(value["document"], value["parent"], value["provenance"])
                return self.json(saved, 201)
            except feedback.Conflict as exc:
                self.json(dict(error=str(exc)), 409)
            except (ReviewError, OSError, ValueError, KeyError, TypeError):
                self.json(
                    dict(error="Feedback validation/save failed; keep your draft or export it"), 400
                )
            finally:
                # Refused/oversized bodies must not be parsed as another keep-alive request.
                self.close_connection = True

    return LoopbackServer(("127.0.0.1", port), Handler)
