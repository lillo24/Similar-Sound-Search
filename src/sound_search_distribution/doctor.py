"""Read-only capability readiness, dependency checks, source proofs and finite capacity."""

import importlib.metadata
import platform
import struct
import sys
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import InputError

from . import authority, contracts
from .context import Context
from .files import sha, target, verify_files
from .policy import estimate


def interpreter():
    if sys.version_info[:3] != (3, 12, 14) or struct.calcsize("P") != 8:
        raise InputError(
            "D03 requires exact Python 3.12.14 / 64-bit; numerical identity is not spoofed"
        )
    if platform.system() != "Windows" or platform.machine().upper() not in {"AMD64", "X86_64"}:
        raise InputError(
            "D03 supported product target is Windows AMD64; other core platforms are unverified"
        )


def dependencies(root):
    expected = {}
    for name in ("requirements.lock", "requirements-models.lock"):
        import re

        for line in (root / name).read_text(encoding="utf-8").splitlines():
            match = re.match(r"^([\w.-]+)==([^\s]+)", line)
            if match:
                expected[match[1]] = match[2]
    for name, version in expected.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise InputError(
                "D03 missing dependency " + name + "; run checked offline setup"
            ) from exc
        if actual != version:
            raise InputError(
                "D03 dependency " + name + " expected " + version + ", found " + actual
            )
    return expected


def capacity(owner):
    ok, reason = authority.availability(
        owner.root, owner.share, owner.pool(), estimate("search", 2)
    )
    return dict(
        ready=ok, reason=reason, required=estimate("search", 2), counts=owner.pool()["counts"]
    )


def inspect(root, share="normal", deep=False):
    root = Path(root).resolve()
    interpreter()
    deps = dependencies(root)
    owner = Context(root, share=share)
    code = contracts.consumer(owner)
    manifest = record(root / "private-assets.json")
    missing = [
        name
        for name, info in manifest["files"].items()
        if not target(root, name).is_file() or target(root, name).stat().st_size != info["bytes"]
    ]
    if deep:
        verify_files(root, manifest["files"])
    from similar_sound_search.application import history

    old, plan, _ = history.inputs(owner)
    _, banks = history.bank_reader(owner)
    model = [n for n in manifest["files"] if n.endswith("mn04_as_mAP_432.pt")]
    model_ok = (
        len(model) == 1
        and model[0] not in missing
        and sha(target(root, model[0])) == manifest["files"][model[0]]["sha256"]
    )
    cap = capacity(owner)
    return dict(
        schema_version="d03-doctor-1",
        core="0.3.0",
        python=sys.version.split()[0],
        platform=platform.platform(),
        dependencies=deps,
        consumer=code,
        capabilities=dict(
            engineering_smoke=True,
            completed_results=all(
                (root / "data/runs/application/states" / (j + ".json")).is_file()
                for j in manifest["baseline_jobs"]
            ),
            real_catalogue_search=not missing and model_ok and cap["ready"],
            c03=False,
            d02=False,
        ),
        missing=missing,
        model_available=model_ok,
        private_bytes_verified=deep,
        catalogue_recordings=len(plan["input"]["sources"]),
        native_rows=sum(b["value"]["coverage"]["windows"] for b in banks),
        capacity=cap,
        allocation_id=owner.binding["allocation_id"],
        installed_module=str(Path(__file__).resolve()),
    )
