"""HTTP payload accounting that survives retries, worker kills, and job resumption."""

import http.client
import math
import os
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import truststore

from ..storage import InputError, ResourceError, bounded_json, contained, is_link, read_json

CHUNK = 1024 * 1024


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    """Caller holds the project lock. Unsettled read/time reservations stay charged."""

    def __init__(self, directory, budget, policy):
        self.directory = Path(directory)
        self.path = self.directory / "ledger.json"
        self.budget = budget
        self.policy = policy
        ceilings = {
            "download_bytes": budget.limits["max_download_bytes"],
            "attempts": policy["max_http_attempts"],
            "worker_seconds": policy["max_job_seconds"],
        }
        if self.path.exists():
            self.value = read_json(self.path)
            if self.value.get("schema_version") != "a03-ledger-1":
                raise InputError("catalogue ledger: invalid schema")
            counters = (
                "charged_bytes",
                "received_bytes",
                "http_attempts",
                "charged_worker_seconds",
                "pending_read_bytes",
                "pending_worker_seconds",
            )
            for key in counters:
                value = self.value.get(key)
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not 0 <= value <= 2**63 - 1
                    or not math.isfinite(value)
                ):
                    raise InputError(f"catalogue ledger: invalid counter {key}")
            if self.value["received_bytes"] > self.value["charged_bytes"] or not isinstance(
                self.value.get("ceilings"), dict
            ):
                raise InputError("catalogue ledger: invalid cumulative accounting")
            # A changed tier cannot replenish an already-established allowance.
            for key, limit in ceilings.items():
                old = self.value["ceilings"].get(key)
                if (
                    isinstance(old, bool)
                    or not isinstance(old, (int, float))
                    or not 0 <= old <= 2**63 - 1
                    or not math.isfinite(old)
                ):
                    raise InputError(f"catalogue ledger: invalid ceiling {key}")
                self.value["ceilings"][key] = min(limit, self.value["ceilings"][key])
        else:
            self.value = {
                "schema_version": "a03-ledger-1",
                "created_at": utc_now(),
                "ceilings": ceilings,
                "charged_bytes": 0,
                "received_bytes": 0,
                "http_attempts": 0,
                "charged_worker_seconds": 0,
                "pending_read_bytes": 0,
                "pending_worker_seconds": 0,
            }
        self.save()

    def save(self):
        bounded_json(self.path, self.value, self.budget)

    @property
    def remaining(self):
        return self.value["ceilings"]["download_bytes"] - self.value["charged_bytes"]

    def attempt(self, url):
        if self.value["http_attempts"] >= self.value["ceilings"]["attempts"]:
            raise ResourceError("catalogue: durable HTTP attempt allowance exhausted")
        if self.remaining <= 0:
            raise ResourceError(
                "catalogue: durable download allowance exhausted (smoke is offline)"
            )
        self.value["http_attempts"] += 1
        self.save()
        return self.value["http_attempts"]

    def read(self, response, size):
        # Charge BEFORE asking the HTTP stream for bytes. A killed process cannot refund this.
        if size > self.remaining:
            raise ResourceError(
                f"HTTP read: needs {size} bytes, durable remaining={self.remaining}"
            )
        self.value["charged_bytes"] += size
        self.value["pending_read_bytes"] = size
        self.save()
        try:
            data = response.read(size)
        except http.client.IncompleteRead as exc:
            data = exc.partial
            self._settle_read(size, len(data))
            raise InputError(
                f"HTTP truncated response: received partial {len(data)} bytes"
            ) from exc
        # An unmeasurable socket/read failure conservatively retains the whole reservation.
        self._settle_read(size, len(data))
        return data

    def _settle_read(self, reserved, actual):
        self.value["charged_bytes"] -= reserved - actual
        self.value["received_bytes"] += actual
        self.value["pending_read_bytes"] = 0
        self.save()

    def begin_worker(self, seconds):
        if (
            self.value["charged_worker_seconds"] + seconds
            > self.value["ceilings"]["worker_seconds"]
        ):
            raise ResourceError("catalogue: durable job time allowance exhausted")
        self.value["charged_worker_seconds"] += seconds
        self.value["pending_worker_seconds"] = seconds
        self.save()

    def end_worker(self, actual):
        reserved = self.value["pending_worker_seconds"]
        # A timeout can include a small process-termination overrun. Keep that spent
        # wall time visible even when it puts the cumulative charge past its ceiling.
        self.value["charged_worker_seconds"] += actual - reserved
        self.value["pending_worker_seconds"] = 0
        self.save()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_url(url, allow_local=False):
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        and parsed.path.startswith("/download/")
        or parsed.fragment
    ):
        raise InputError("acquire: expected public HTTP(S) URL without credentials/signed access")
    if allow_local and parsed.hostname in {"127.0.0.1", "localhost"}:
        return url
    host = parsed.hostname
    if parsed.scheme != "https" or not (host == "archive.org" or host.endswith(".archive.org")):
        raise InputError(f"acquire: unsupported source/redirect host {host!r}")
    return url


def fetch(url, destination, ledger, max_bytes, expected_bytes=None, allow_local=False):
    """Two attempts, up to three redirects each; identity encoding, bounded bodies, no ranges.

    Destination is an owned staging file, never a ready asset. All application-read response
    payloads (including error/redirect bodies) and unresolved reservations count cumulatively.
    """
    budget = ledger.budget
    max_bytes = min(max_bytes, budget.limits["max_input_bytes"])
    if expected_bytes is not None and expected_bytes > min(max_bytes, ledger.remaining):
        raise ResourceError(f"acquire {url}: advertised asset exceeds remaining byte allowance")
    if is_link(destination):
        raise InputError("HTTP staging: symlink output refused")
    destination = contained(destination, budget.root / "data/runs/catalogue")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Native trust verifies TLS and fetches missing intermediates on Windows. Never disable TLS.
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    last_error = None
    for retry in range(ledger.policy["attempts_per_url"]):
        current = public_url(url, allow_local)
        try:
            for redirect in range(ledger.policy["max_redirects"] + 1):
                budget.check_time("request", current)
                attempt = ledger.attempt(current)
                started = time.monotonic()
                audit = {"url": current, "started_at": utc_now(), "status": "requesting"}
                audit_path = ledger.directory / "attempts" / f"{attempt:06d}.json"
                bounded_json(audit_path, audit, budget)
                request = urllib.request.Request(
                    current,
                    headers={
                        "User-Agent": "Similar-Sound-Search-A03/0.3 (bounded research acquisition)",
                        "Accept-Encoding": "identity",
                    },
                )
                response = None
                try:
                    try:
                        response = opener.open(
                            request, timeout=ledger.policy["request_timeout_seconds"]
                        )
                    except urllib.error.HTTPError as exc:
                        response = exc
                    with response:
                        status = response.code
                        audit["http_status"] = status
                        if response.headers.get("Content-Encoding", "identity") != "identity":
                            raise InputError("HTTP compressed transfer encoding is unsupported")
                        length = response.headers.get("Content-Length")
                        try:
                            length = None if length is None else int(length)
                            if length is not None and length < 0:
                                raise ValueError("negative length")
                        except ValueError as exc:
                            raise InputError("HTTP invalid Content-Length") from exc
                        if status != 200:
                            # Read at most one bounded chunk, including redirect/error payloads.
                            amount = min(
                                65536, ledger.remaining, length if length is not None else 65536
                            )
                            if amount:
                                ledger.read(response, amount)
                            if status in {301, 302, 303, 307, 308}:
                                if redirect >= ledger.policy["max_redirects"]:
                                    raise InputError("HTTP redirect bound exhausted")
                                location = response.headers.get("Location")
                                if not location:
                                    raise InputError("HTTP redirect has no Location")
                                current = public_url(
                                    urllib.parse.urljoin(current, location), allow_local
                                )
                                audit["status"] = "redirect"
                                continue
                            raise InputError(f"HTTP {status} fetching {current}")
                        if length is not None and length > min(max_bytes, ledger.remaining):
                            raise ResourceError(
                                f"HTTP Content-Length={length} exceeds bounded download"
                            )
                        if expected_bytes is not None and length not in {None, expected_bytes}:
                            raise InputError(
                                f"HTTP changed length: expected {expected_bytes}, found {length}"
                            )
                        budget.reserve((length if length is not None else max_bytes) + 65536)
                        received = 0
                        if hasattr(budget, "track_file"):
                            budget.track_file(destination)
                        with destination.open("wb") as output:
                            if hasattr(budget, "account_file"):
                                budget.account_file(destination, 0)
                            while True:
                                budget.check_time("HTTP stream", current)
                                if length is not None and received == length:
                                    break
                                room = min(CHUNK, ledger.remaining, max_bytes + 1 - received)
                                if room <= 0:
                                    raise ResourceError("HTTP streaming byte allowance exhausted")
                                if length is not None:
                                    room = min(room, length - received)
                                chunk = ledger.read(response, room)
                                if not chunk:
                                    break
                                received += len(chunk)
                                if received > max_bytes:
                                    raise ResourceError("HTTP body exceeds per-file byte limit")
                                budget.reserve(len(chunk) + 65536)
                                output.write(chunk)
                                if hasattr(budget, "account_file"):
                                    budget.account_file(destination, received)
                            output.flush()
                            os.fsync(output.fileno())
                        if length is not None and received != length:
                            raise InputError(
                                f"HTTP truncated: expected {length}, received {received}"
                            )
                        if expected_bytes is not None and received != expected_bytes:
                            raise InputError(
                                f"HTTP changed/truncated: expected {expected_bytes}, "
                                f"received {received}"
                            )
                        audit.update(
                            {"status": "downloaded", "bytes": received, "final_url": current}
                        )
                        return audit
                except (
                    InputError,
                    OSError,
                    urllib.error.URLError,
                    http.client.HTTPException,
                ) as exc:
                    audit.update(
                        {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}
                    )
                    raise
                finally:
                    audit["wall_seconds"] = time.monotonic() - started
                    bounded_json(audit_path, audit, budget)
        except ResourceError:
            raise
        except (
            InputError,
            OSError,
            urllib.error.URLError,
            socket.timeout,
            http.client.HTTPException,
        ) as exc:
            last_error = exc
            if retry + 1 < ledger.policy["attempts_per_url"]:
                budget.check_time("retry", url)
                time.sleep(ledger.policy["backoff_seconds"] * (retry + 1))
    raise InputError(f"acquire {url}: attempts exhausted: {last_error}") from last_error
