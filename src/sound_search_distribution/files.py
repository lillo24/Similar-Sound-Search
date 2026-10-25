"""Strict portable paths, inventories and checked publication for distribution inputs."""

import hashlib
import os
import re
from pathlib import Path, PurePosixPath

from similar_sound_search.storage import InputError, is_link


def relative(name):
    if not isinstance(name, str):
        raise InputError("D03 portable relative path must be a string")
    p = PurePosixPath(name)
    if (
        not isinstance(name, str)
        or not name
        or "\\" in name
        or ":" in name
        or p.is_absolute()
        or any(x in {"", ".", ".."} or x.endswith((".", " ")) for x in name.split("/"))
        or any(re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?", x) for x in p.parts)
    ):
        raise InputError("D03 invalid portable relative path: " + str(name))
    return p


def target(root, name):
    p = root.joinpath(*relative(name).parts)
    for parent in [root, *p.parents, p]:
        if parent.exists() and is_link(parent):
            raise InputError("D03 links/junctions are not permitted: " + str(parent))
    if not p.resolve().is_relative_to(root.resolve()):
        raise InputError("D03 target escapes selected root")
    return p


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(MIB), b""):
            value.update(block)
    return value.hexdigest()


MIB = 1024**2


def inventory(root):
    """Fresh complete regular-file walk; never follow a junction or skip a failed stat."""
    answer, seen, pending = {}, set(), [Path(root)]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                p = Path(entry.path)
                name = p.relative_to(root).as_posix()
                if is_link(p):
                    raise InputError("D03 inventory refuses a link/junction: " + name)
                if name.casefold() in seen:
                    raise InputError("D03 conflicting case-insensitive path: " + name)
                seen.add(name.casefold())
                relative(name)
                if entry.is_dir(follow_symlinks=False):
                    pending.append(p)
                elif entry.is_file(follow_symlinks=False):
                    answer[name] = dict(bytes=entry.stat().st_size, sha256=sha(p))
                else:
                    raise InputError("D03 non-regular entry: " + name)
                if len(seen) > 100000:
                    raise InputError("D03 inventory exceeds 100000 entries")
    return answer


def verify_files(root, files, maximum=1024**3):
    if sum(v["bytes"] for v in files.values()) > maximum:
        raise InputError("D03 inventory exceeds its declared copy/output ceiling")
    seen = set()
    for name, info in files.items():
        if name.casefold() in seen:
            raise InputError("D03 duplicate case-insensitive inventory path")
        seen.add(name.casefold())
        p = target(root, name)
        if not p.is_file() or p.stat().st_size != info["bytes"] or sha(p) != info["sha256"]:
            raise InputError("D03 missing/changed inventory file: " + name)
