"""Optional, review-bound responses with append-only revisions and explicit conflicts."""

import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone

from .common import MIB, ReviewError, encoded, inside, output_limits, put_new, read, seal, verified

RATINGS = ("similar", "different", "unsure", "not-listened")


class Conflict(ReviewError):
    pass


def blank(manifest):
    return dict(
        schema_version="d04-feedback-1",
        review_hash=manifest["record_hash"],
        listener="",
        participation="pending",
        reference=dict(section="not-listened", sound="", note=""),
        items={c["review_id"]: dict(rating="not-listened", note="") for c in manifest["cards"]},
    )


def text(value, limit):
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        raise ReviewError("Feedback text is invalid or exceeds its character limit")


def validate(document, manifest):
    expected = blank(manifest)
    if not isinstance(document, dict) or set(document) != set(expected):
        raise ReviewError("Feedback fields differ from d04-feedback-1")
    if document["schema_version"] != expected["schema_version"]:
        raise ReviewError("Unsupported feedback version")
    if document["review_hash"] != manifest["record_hash"]:
        raise ReviewError("Feedback belongs to another review; opinions cannot migrate")
    if not isinstance(document["items"], dict) or set(document["items"]) != set(expected["items"]):
        raise ReviewError("Missing, stale or foreign review item IDs")
    text(document["listener"], 80)
    if document["participation"] not in ("pending", "reviewing", "declined"):
        raise ReviewError("Invalid participation state")
    ref = document["reference"]
    if not isinstance(ref, dict) or set(ref) != {"section", "sound", "note"}:
        raise ReviewError("Invalid reference response")
    if ref["section"] not in ("not-listened", "yes", "no", "unsure"):
        raise ReviewError("Invalid reference section response")
    text(ref["sound"], 2000)
    text(ref["note"], 2000)
    for item in document["items"].values():
        if not isinstance(item, dict) or set(item) != {"rating", "note"}:
            raise ReviewError("Invalid per-card response")
        if item["rating"] not in RATINGS:
            raise ReviewError("Invalid rating; technical playback is not a human judgment")
        text(item["note"], 2000)
    if len(encoded(document)) > 65536:
        raise ReviewError("Feedback exceeds 64 KiB")
    return document


def counts(document):
    result = dict(shown=10, listened_rated=0, similar=0, different=0, unsure=0, unanswered=0)
    for item in document["items"].values():
        rating = item["rating"]
        result["unanswered" if rating == "not-listened" else rating] += 1
    result["listened_rated"] = 10 - result["unanswered"]
    ref = document["reference"]
    responded = (
        result["listened_rated"] > 0
        or any(i["note"] for i in document["items"].values())
        or any(ref[k] if k != "section" else ref[k] != "not-listened" for k in ref)
    )
    result["state"] = (
        "declined"
        if document["participation"] == "declined"
        else "completed"
        if result["listened_rated"] == 10 and ref["section"] != "not-listened"
        else "partial"
        if responded
        else "pending"
    )
    return result


class Store:
    def __init__(self, root, directory, manifest):
        self.root, self.directory, self.manifest = root, directory, manifest
        if not directory.resolve().is_relative_to((root / "metadata").resolve()):
            raise ReviewError("Feedback must stay in the D04 metadata allowance")
        if directory.is_symlink() or directory.is_junction():
            raise ReviewError("Feedback links are forbidden")
        directory.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def lock(self):
        """Coordinate separate companion processes without an application lock/pool."""
        path = inside(self.root, "metadata/" + self.directory.name + ".lock")
        with path.open("a+b") as stream:
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise Conflict(
                    "Another feedback reader/writer is active; retry your preserved draft"
                ) from exc
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)

    def snapshots(self):
        with self.lock():
            return self._snapshots()

    def _snapshots(self):
        files = sorted(self.directory.iterdir())
        if len(files) > 512 or sum(f.stat().st_size for f in files) > 16 * MIB:
            raise ReviewError("Feedback storage cap reached; retain existing revisions")
        parent = None
        result = []
        for number, file in enumerate(files, 1):
            if (
                file.is_symlink()
                or file.is_junction()
                or not re.fullmatch(r"[0-9]{6}-[a-f0-9]{64}\.json", file.name)
            ):
                raise ReviewError("Unexpected feedback file; explicit recovery required")
            value = verified(read(file, 128 * 1024))
            if (
                value["revision"] != number
                or value["parent"] != parent
                or file.name != f"{number:06}-{value['record_hash']}.json"
            ):
                raise ReviewError("Feedback revision chain differs; no silent fallback")
            validate(value["document"], self.manifest)
            if (
                value["schema_version"] != "d04-feedback-revision-1"
                or value["review_hash"] != self.manifest["record_hash"]
                or value["counts"] != counts(value["document"])
            ):
                raise ReviewError("Saved feedback binding/counts differ")
            parent = value["record_hash"]
            result.append(value)
        return result

    def latest(self):
        values = self.snapshots()
        return values[-1] if values else None

    def save(self, document, parent, provenance):
        validate(document, self.manifest)
        if provenance not in ("local-form", "imported-file", "attributed-text-reply"):
            raise ReviewError("Feedback provenance is required")
        with self.lock():
            return self._save(document, parent, provenance)

    def _save(self, document, parent, provenance):
        snapshots = self._snapshots()
        previous = snapshots[-1] if snapshots else None
        if parent != (previous["record_hash"] if previous else None):
            raise Conflict("A newer response exists. Export your preserved draft before merging.")
        value = seal(
            dict(
                schema_version="d04-feedback-revision-1",
                review_hash=self.manifest["record_hash"],
                revision=previous["revision"] + 1 if previous else 1,
                parent=parent,
                recorded_at=datetime.now(timezone.utc).isoformat(),
                provenance=provenance,
                attribution="listener field is self-reported; no identity verification",
                document=document,
                counts=counts(document),
            )
        )
        output_limits(self.root, len(encoded(value)) + 1)
        if len(snapshots) >= 512:
            raise ReviewError("Feedback revision cap reached")
        file = self.directory / f"{value['revision']:06}-{value['record_hash']}.json"
        put_new(file, value)
        return value
