"""Select and stage the actual private dependency graph without copying old experiments."""

import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path

from similar_sound_search.application.codec import decode
from similar_sound_search.storage import InputError, atomic_json, digest, read_json

from .files import inventory, sha, target, verify_files
from .policy import MIB

BASELINES = (
    "1c0ef69a1a5156319dec8a976cab164de576d13ba9cc00f5c24b4355b361a678",
    "12941fbd35737b6fb7df959d4fbbf9a1425fd5d5c1ba208cb01eb55e943ebef0",
    "589ac27a30d60007e1a7f8ad6fdd695499d23ca0f17b55e858b00d624be0fd6b",
)


def discover(root):
    """Follow explicit paths/content-addressed records from selected product seeds.

    Hash-only cache/bundle references are resolved from a metadata filename index.
    Array directories contribute their exact record/data files, never a whole
    historical run. Pools are read-only leaf evidence, never graph expansion seeds.
    """
    root = Path(root).resolve()
    hashes = defaultdict(list)
    for p in (root / "data").rglob("*"):
        if p.is_file() and p.suffix == ".json" and re.fullmatch("[a-f0-9]{64}", p.stem):
            hashes[p.stem].append(p)
        elif p.is_dir() and re.fullmatch("[a-f0-9]{64}", p.name) and (p / "record.json").is_file():
            hashes[p.name].append(p / "record.json")
    proto = read_json(root / "manifests/application/protocol.json")
    pending = [root / "data/runs/application/pool.json"]
    for key in BASELINES:
        pending += [
            root / "data/runs/application" / k / (key + ".json") for k in ("jobs", "states")
        ]
    pending += [
        root / "data/runs/processing" / k / (proto["c04_job"] + ".json")
        for k in ("jobs", "progress")
    ]
    for key in proto["delivery"].values():
        pending += hashes[key]
    pending += list((root / "data/models").rglob("mn04_as_mAP_432.pt"))
    pending += list(
        (root / "reports/local/c03").rglob(
            "b91a8bffd1e5170651feaa874190096201a2df647833d41a621a5e09ef07bf79.wav"
        )
    )
    # The historical library uses contextual metadata addressed by directory,
    # rather than content-ID filenames. Keep only metadata; follow its audio refs.
    pending += list((root / "data/runs/queries/contexts").glob("*.json"))
    included = set()

    def add_string(text, parent):
        if re.fullmatch("[a-f0-9]{64}", text):
            pending.extend(hashes[text])
            return
        if "\\" in text or ":" in text or ".." in Path(text).parts:
            return
        candidates = []
        if text.startswith(("data/", "manifests/", "config/", "reports/local/")):
            candidates.append(root / text)
        if (
            text
            and "/" not in text
            and Path(text).suffix in {".json", ".npy", ".wav", ".mp3", ".pt"}
        ):
            candidates.append(parent / text)
            candidates.append(root / text)
        for p in candidates:
            if p.is_file():
                pending.append(p)
            elif p.is_dir() and (p / "record.json").is_file():
                pending.extend(x for x in p.iterdir() if x.is_file())

    def walk(value, parent):
        if isinstance(value, dict):
            value = decode(value)
            for k, v in value.items():
                add_string(k, parent)
                walk(v, parent)
        elif isinstance(value, list):
            for v in value:
                walk(v, parent)
        elif isinstance(value, str):
            add_string(value, parent)

    while pending:
        p = pending.pop()
        name = p.relative_to(root).as_posix()
        if name in included or name.startswith(("manifests/", "config/")):
            continue
        if not p.is_file():
            raise InputError("D03 private dependency missing: " + str(p))
        target(root, name)
        if name.startswith(
            ("data/runs/assessment/", "data/audio/assessment/", "data/features/assessment/")
        ):
            raise InputError("D03 ordinary catalogue closure unexpectedly depends on D02 fixtures")
        included.add(name)
        if p.stat().st_size > 256 * MIB or len(included) > 12000:
            raise InputError("D03 dependency closure exceeds per-file/entry bounds")
        if p.suffix == ".json" and p.name not in {"pool.json", "work.json", "ledger.json"}:
            if p.stat().st_size > MIB:
                raise InputError("D03 private JSON exceeds 1 MiB")
            walk(json.loads(p.read_text(encoding="utf-8")), p.parent)
        if p.name == "record.json":
            pending.extend(x for x in p.parent.iterdir() if x.is_file())
    files = {
        n: dict(bytes=(root / n).stat().st_size, sha256=sha(root / n)) for n in sorted(included)
    }
    if sum(v["bytes"] for v in files.values()) > 900 * MIB:
        raise InputError("D03 private closure cannot retain staging headroom within 1 GiB")
    value = dict(
        schema_version="d03-private-closure-1",
        files=files,
        baseline_jobs=list(BASELINES),
        mode="real-catalogue-and-three-completed-results",
        optional_history=dict(c03=False, d02=False),
    )
    return {**value, "record_hash": digest(value)}


def prepare(source, destination, public_root):
    """Verified copy into a genuinely empty target; publish by same-volume rename."""
    source, destination, public_root = (
        Path(source).resolve(),
        Path(destination).resolve(),
        Path(public_root).resolve(),
    )
    if destination.exists():
        raise InputError("D03 private preparation refuses an existing destination")
    manifest = discover(source)
    from .policy import limits
    from .runtime import Runtime

    private_bytes = sum(v["bytes"] for v in manifest["files"].values())
    inherited_bytes = Runtime.budget(source, limits(source)).managed_bytes()
    if inherited_bytes + private_bytes + 1024 * MIB > 4 * 1024**3:
        raise InputError("D03 combined inherited/private/runtime reserved storage exceeds 4 GiB")
    if shutil.disk_usage(destination.parent).free < private_bytes + 4 * 1024**3:
        raise InputError("D03 private staging would violate 4 GiB free headroom")
    stage = destination.with_name(destination.name + ".d03-staging")
    if os.name == "nt" and any(len(str(stage / n)) > 240 for n in manifest["files"]):
        raise InputError(
            "D03 workspace path too long for this Windows target; choose a short root "
            "such as C:\\SSS D03 è\\w. No staging writes were made."
        )
    if stage.exists():
        raise InputError("D03 staging already exists; retain/inspect the earlier attempt")
    stage.mkdir(parents=True)
    for folder in ("config", "manifests"):
        for p in (public_root / folder).rglob("*"):
            if p.is_file():
                name = p.relative_to(public_root).as_posix()
                q = target(stage, name)
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, q)
    for name in ("requirements.lock", "requirements-models.lock"):
        shutil.copyfile(public_root / name, stage / name)
    for name, info in manifest["files"].items():
        p, q = target(source, name), target(stage, name)
        if p.stat().st_size != info["bytes"] or sha(p) != info["sha256"]:
            raise InputError("D03 source changed during private staging: " + name)
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, q)
    verify_files(stage, manifest["files"])
    atomic_json(stage / "private-assets.json", manifest)
    # Exact historical B03 records are also exposed through the shared runtime
    # library for completed-query loading. Bindings continue to reference their
    # original private paths; producers, feature IDs and bytes are unchanged.
    legacy = stage / "data/runs/application/library"
    if legacy.is_dir():
        for p in legacy.rglob("*"):
            if p.is_file():
                q = stage / "data/runs/runtime-library" / p.relative_to(legacy)
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, q)
    if sum(p["bytes"] for p in inventory(stage).values()) > 1024 * MIB:
        raise InputError("D03 staging exceeds the 1 GiB live-copy ceiling")
    stage.rename(destination)
    return manifest
