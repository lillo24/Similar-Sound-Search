"""Nonblocking OS ownership; persistent lock files are never process evidence."""

import os
import time
from contextlib import contextmanager

from ..storage import InputError, ResourceError, contained


@contextmanager
def lock(root, name):
    if name not in {"pool", "coordinator", "worker", "server", "library"}:
        raise InputError("D01 unknown internal lock")
    path = contained(root / "data/runs/application" / (name + ".lock"), root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        started = time.monotonic()
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if name == "pool" and time.monotonic() - started < 2:
                    time.sleep(0.02)
                    continue
                raise ResourceError("D01 " + name + " is owned by another active process") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def active(root, name):
    """Probe only an existing file, without creating or rewriting it."""
    path = root / "data/runs/application" / (name + ".lock")
    if not path.exists():
        return False
    try:
        with lock(root, name):
            return False
    except ResourceError:
        return True
