"""Owned atomic binary publication; interrupted temporaries remain inspectable."""

import os
import tempfile


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".d01-write-", dir=path.parent)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    # No finally/unlink: a refused Windows replace retains the failed temporary.
    os.replace(name, path)
