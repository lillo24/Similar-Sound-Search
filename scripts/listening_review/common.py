"""Small stdlib-only file/identity boundary, independent of the installed product."""

import hashlib
import json
import os
from pathlib import Path

MIB = 1024 * 1024


class ReviewError(ValueError):
    pass


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")


def identity(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def seal(value):
    return {**value, "record_hash": identity(value)}


def verified(value):
    body = {k: v for k, v in value.items() if k != "record_hash"}
    if value.get("record_hash") != identity(body):
        raise ReviewError("Review record checksum differs")
    return value


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(131072), b""):
            h.update(block)
    return h.hexdigest()


def read(path, limit=MIB):
    path = Path(path)
    if path.stat().st_size > limit:
        raise ReviewError("JSON exceeds bounded input size: " + path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def put_new(path, value):
    """Exclusive, immutable writes; an incomplete write remains a visible failure."""
    path = Path(path)
    raw = encoded(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def inside(root, relative):
    root = Path(root).resolve()
    p = root / relative
    if any(q.is_symlink() or q.is_junction() for q in (p, *p.parents) if q.is_relative_to(root)):
        raise ReviewError("Links are not allowed in the review path")
    if not p.resolve().is_relative_to(root):
        raise ReviewError("Path outside the owned review directory")
    return p


def inventory(root, transient=False):
    root = Path(root)
    scan_root = root
    if os.name == "nt" and not str(root).startswith("\\\\?\\"):
        scan_root = Path("\\\\?\\" + str(root.resolve()))
    result = {}

    def walk(folder):
        try:
            with os.scandir(folder) as stream:
                entries = list(stream)
        except FileNotFoundError:
            if not transient:
                raise
            return
        for entry in entries:
            try:
                # On Windows DirEntry caches WIN32_FIND_DATA, including size.
                # Avoid opening every live fixture file while its writer renames it.
                info = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise ReviewError("Links are not allowed in the review directory")
                if entry.is_dir(follow_symlinks=False):
                    walk(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    result[Path(entry.path).relative_to(scan_root).as_posix()] = info.st_size
            except FileNotFoundError:
                if not transient:
                    raise
                # A disposable file removed during a live sample is no longer output.

    walk(scan_root)
    return result


def allowance():
    return read(
        Path(__file__).resolve().parents[2] / "manifests/listening/preparation-allowance.json", 4096
    )


def output_limits(root, additional=0, category="metadata", transient=False):
    files = inventory(root, transient=transient)
    # Category ceilings are independent; their sum does not enlarge the total.
    rules = allowance()
    for prefix, cap in (
        ("qa/", rules["qa_bytes"]),
        ("metadata/", rules["metadata_bytes"]),
        ("bundle/", rules["media_bundle_bytes"]),
    ):
        extra = additional if prefix == category + "/" else 0
        if sum(n for p, n in files.items() if p.startswith(prefix)) + extra > cap:
            raise ReviewError("D04 output cap reached: " + prefix)
    if sum(files.values()) + additional > rules["total_output_bytes"]:
        raise ReviewError("D04 total output cap reached")
    return files
