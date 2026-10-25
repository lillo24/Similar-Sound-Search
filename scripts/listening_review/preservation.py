"""Hash the old accounting/guards and frozen code; D04 writes only its own artifacts."""

import os
import shutil
from pathlib import Path

from .common import MIB, ReviewError, put_new, read, sha


def snapshot(project, workspace):
    paths = {}
    for label, root in (("original", project), ("installed-workspace", workspace)):
        choices = set()
        for sub in ("config", "manifests"):
            choices.update(p for p in (root / sub).rglob("*") if p.is_file())
        for p in (root / "data/runs").rglob("*.json"):
            if any(s in p.name.lower() for s in ("pool", "ledger", "guard")):
                choices.add(p)
        if label == "original":
            for sub in ("src/similar_sound_search", "src/sound_search_distribution"):
                choices.update(
                    p
                    for p in (root / sub).rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts
                )
        else:
            choices.update(
                root / s for s in ("binding.json", "private-assets.json") if (root / s).is_file()
            )
        for path in sorted(choices):
            paths[label + "/" + path.relative_to(root).as_posix()] = dict(
                bytes=path.stat().st_size, sha256=sha(path)
            )
    registry = Path(os.environ["LOCALAPPDATA"]) / "SimilarSoundSearch/D03/allocation.json"
    paths["external-allocation-registry"] = dict(
        bytes=registry.stat().st_size, sha256=sha(registry)
    )
    return paths


def audit(project, workspace, output, before=False):
    current = snapshot(project, workspace)
    target = output / "metadata/preservation-before.json"
    if before:
        if shutil.disk_usage(output).free < 4 * 1024**3 + 128 * MIB:
            raise ReviewError("D04 requires 4 GiB free after its entire output allowance")
        package = project / "dist/similar-sound-search-d03-1.0.0.zip"
        if package.stat().st_size != 292441732 or sha(package) != (
            "062f97ac056f75f664440c0bfc45caaea3ed7e52023d6568704098dda7808901"
        ):
            raise ReviewError("Delivered D03 archive size/checksum differs")
        put_new(target, dict(files=current, archive_verified=True))
    else:
        old = read(target, 8 * MIB)["files"]
        # New D04 manifests are allowed, but every pre-existing file must remain exact.
        differences = [k for k, v in old.items() if current.get(k) != v]
        if differences:
            raise ReviewError("Historical accounting/code changed: " + ", ".join(differences))
        put_new(
            output / "metadata/preservation-after.json",
            dict(
                checked_files=len(old),
                changed_or_missing=differences,
                files={k: current[k] for k in old},
            ),
        )
