"""Standalone stdlib-only verifier and offline installer, also copied into the archive."""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


def checked(root, name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Invalid archive/inventory path")
    p = PurePosixPath(name)
    if p.is_absolute() or any(
        x in {"", ".", ".."} or x.endswith((".", " ")) for x in name.split("/")
    ):
        raise ValueError("Unsafe archive/inventory path: " + name)
    if any(re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?", x) for x in p.parts):
        raise ValueError("Reserved archive path")
    out = root.joinpath(*p.parts)
    if not out.resolve().is_relative_to(root.resolve()):
        raise ValueError("Archive path escapes destination")
    for parent in [out, *out.parents]:
        if parent.exists() and (parent.is_symlink() or os.path.isjunction(parent)):
            raise ValueError("Archive target contains a link/junction")
    return out


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024**2), b""):
            h.update(b)
    return h.hexdigest()


def verify(root):
    value = json.loads((root / "release.json").read_text(encoding="utf-8"))
    files = value["files"]
    if value["release"] != "d03-1.0.0" or len(files) > 20000:
        raise ValueError("Unsupported release/inventory")
    if sum(v["bytes"] for v in files.values()) > 512 * 1024**2:
        raise ValueError("Release exceeds 512 MiB code/wheelhouse bound")
    seen = set()
    for name, info in files.items():
        if name.casefold() in seen:
            raise ValueError("Duplicate release path")
        seen.add(name.casefold())
        path = checked(root, name)
        if (
            not path.is_file()
            or path.stat().st_size != info["bytes"]
            or sha(path) != info["sha256"]
        ):
            raise ValueError("Missing/changed release file: " + name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(files) | {"release.json"}:
        raise ValueError("Release contains undeclared files")
    return value


def extract(archive, destination, expected_hash):
    """Check hash, all names, duplicates, type and expansion before writing any file."""
    if sha(archive) != expected_hash:
        raise ValueError("Archive SHA256 differs")
    if destination.exists():
        raise ValueError("Extraction destination must be absent")
    with zipfile.ZipFile(archive) as z:
        seen, size = set(), 0
        for i in z.infolist():
            checked(destination, i.filename)
            mode = i.external_attr >> 16
            if i.is_dir() or mode & 0o170000 not in {0, 0o100000}:
                raise ValueError("Only regular archive files are accepted")
            if i.filename.casefold() in seen:
                raise ValueError("Duplicate archive member")
            seen.add(i.filename.casefold())
            size += i.file_size
        if len(seen) > 20000 or size > 512 * 1024**2:
            raise ValueError("Archive expansion exceeds fixed bound")
        if shutil.disk_usage(destination.parent).free < size + 4 * 1024**3:
            raise ValueError("Insufficient archive disk headroom")
        destination.mkdir()
        for i in z.infolist():
            p = checked(destination, i.filename)
            p.parent.mkdir(parents=True, exist_ok=True)
            with z.open(i) as source, p.open("xb") as target:
                shutil.copyfileobj(source, target, 1024**2)
    return verify(destination)


def install(root, environment):
    if (
        sys.version_info[:3] != (3, 12, 14)
        or struct.calcsize("P") != 8
        or platform.system() != "Windows"
        or platform.machine().upper() != "AMD64"
    ):
        raise ValueError("Setup requires Windows AMD64 exact Python 3.12.14 (64 bit)")
    release = verify(root)
    if environment.exists():
        raise ValueError("Setup refuses an existing environment; inspect it instead of overwriting")
    required = release["installed_bytes_bound"]
    if (
        required > 2 * 1024**3
        or shutil.disk_usage(environment.parent).free < required + 4 * 1024**3
    ):
        raise ValueError("Insufficient environment disk headroom / invalid install bound")
    subprocess.run([sys.executable, "-I", "-m", "venv", str(environment)], check=True)
    python = environment / "Scripts/python.exe"
    wheels = [str(checked(root, n)) for n in release["files"] if n.endswith(".whl")]
    env = {
        **os.environ,
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONNOUSERSITE": "1",
    }
    subprocess.run(
        [
            str(python),
            "-I",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-cache-dir",
            "--no-deps",
            *wheels,
        ],
        env=env,
        check=True,
    )
    subprocess.run([str(python), "-I", "-m", "pip", "check"], env=env, check=True)
    return dict(python=str(python), release=release["release"], offline=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["verify", "install", "extract"])
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--environment", type=Path)
    p.add_argument("--archive", type=Path)
    p.add_argument("--destination", type=Path)
    p.add_argument("--sha256")
    args = p.parse_args()
    try:
        if args.command == "extract":
            if not all((args.archive, args.destination, args.sha256)):
                p.error("extract requires --archive --destination --sha256")
            result = extract(args.archive, args.destination, args.sha256)
        elif args.command == "install":
            if not args.environment:
                p.error("install requires --environment")
            result = install(args.root.resolve(), args.environment.resolve())
        else:
            result = verify(args.root.resolve())
        print(json.dumps(dict(ok=True, release=result["release"]), indent=2))
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as exc:
        print(json.dumps(dict(ok=False, step=args.command, error=str(exc))), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
