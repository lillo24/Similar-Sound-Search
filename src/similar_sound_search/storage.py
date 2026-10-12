"""Local artifact identity, atomic JSON, and single-operation process locking."""

import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


class InputError(Exception):
    """Actionable input/contract failure, never a successful empty operation."""


class ResourceError(InputError):
    """A configured resource boundary refused an operation."""


def is_link(path):
    path = Path(path)
    return path.is_symlink() or path.is_junction()


def read_json(path):
    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise InputError(f"parse {path}: JSON exceeds 1 MiB metadata limit")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise InputError(f"parse {path}: expected UTF-8 JSON: {exc}") from exc


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256(path, budget, limit_key="max_input_bytes"):
    result = hashlib.sha256()
    count = 0
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            budget.check_time("hash", path)
            count += len(chunk)
            budget.cap(limit_key, count, f"hash {path}")
            result.update(chunk)
    return result.hexdigest()


def local_path(path, root):
    path = Path(path).resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        # External explicit inputs are allowed; this record must stay private.
        return str(path)


def atomic_json(path, value):
    """Replace the caller-owned report only after the complete JSON is flushed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, allow_nan=False) + "\n"
    fd, name = tempfile.mkstemp(prefix=".a02-report-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def bounded_json(path, value, budget):
    """Catalogue metadata uses the same 1 MiB reader contract and managed disk budget."""
    if is_link(path):
        raise InputError(f"metadata {path}: symlink output refused")
    path = contained(path, budget.root)
    size = len((json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    if size > 1024 * 1024:
        raise InputError(f"metadata {path.name}: exceeds 1 MiB reader limit")
    budget.reserve(size + 4096)
    if hasattr(budget, "track_file"):
        budget.track_file(path)
    atomic_json(path, value)
    if hasattr(budget, "account_file"):
        budget.account_file(path, size)


def contained(path, root):
    path = Path(path).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise InputError(f"path {path}: must stay inside {root}")
    return path


@contextmanager
def project_lock(root, name=".a02.lock"):
    """OS lock releases on exit/crash; the persistent byte is not a stale lock."""
    if name not in {".a02.lock", ".a03-worker.lock", ".a04-worker.lock"}:
        raise InputError("project lock: unsupported internal lock name")
    path = contained(Path(root) / "data/runs" / name, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
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
            raise ResourceError(
                "concurrency: another A02 operation holds the project lock"
            ) from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)
