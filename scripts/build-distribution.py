"""Build the local D03 wheel and checked offline archive; never copy private assets."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from sound_search_distribution import RELEASE
from sound_search_distribution.files import inventory, sha


def build(root, output):
    if output.exists():
        raise RuntimeError("Build output exists; retain it and use a new attempt directory")
    output.mkdir(parents=True)
    wheel_dir = output / "wheelhouse"
    wheel_dir.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-index",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
        ],
        cwd=root,
        check=True,
    )
    wheels = json.loads((root / "reports/local/d03/cached-wheels.json").read_text())
    local = root / "reports/local/d03/dependency-download/setuptools-80.9.0-py3-none-any.whl"
    with zipfile.ZipFile(local) as z:
        expanded = sum(i.file_size for i in z.infolist())
    wheels.append(
        dict(
            path=str(local),
            filename=local.name,
            bytes=local.stat().st_size,
            sha256=sha(local),
            expanded=expanded,
        )
    )
    for item in wheels:
        source = Path(item["path"])
        if source.stat().st_size != item["bytes"] or sha(source) != item["sha256"]:
            raise RuntimeError("Cached wheel identity differs: " + item["filename"])
        shutil.copyfile(source, wheel_dir / item["filename"])
    for p in subprocess.check_output(
        ["git", "ls-files", "config", "manifests"], cwd=root, text=True
    ).splitlines():
        q = output / p
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / p, q)
    # The prospective declaration may not be staged yet; include it explicitly.
    for p in (root / "manifests/distribution").glob("*.json"):
        q = output / "manifests/distribution" / p.name
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, q)
    for name in ("requirements.lock", "requirements-models.lock"):
        shutil.copyfile(root / name, output / name)
    shutil.copyfile(root / "src/sound_search_distribution/bootstrap.py", output / "setup.py")
    shutil.copyfile(
        root / "src/sound_search_distribution/resources/THIRD_PARTY_NOTICES.txt",
        output / "THIRD_PARTY_NOTICES.txt",
    )
    (output / "README.txt").write_text(
        "Similar Sound Search " + RELEASE + " / Windows AMD64 Python 3.12.14\n\n"
        "Verify: python setup.py verify\n"
        "Install: python setup.py install --environment C:\\YourFolder\\environment\n"
        "Prepare private workspace separately, once (no private data is in this archive):\n"
        "<environment>\\Scripts\\python.exe -I -m sound_search_distribution prepare "
        "--source <original-private-workspace> --distribution <this-directory> "
        "--workspace <new-empty-workspace>\n"
        "Doctor: <environment>\\Scripts\\python.exe -I -m "
        "sound_search_distribution doctor --workspace <workspace> --deep\n"
        "Start: <environment>\\Scripts\\python.exe -I -m "
        "sound_search_distribution start --workspace <workspace> --port 8776\n"
        "Open http://127.0.0.1:8776/ ; Ctrl+C stops the foreground owner.\n"
        "One host/user allocation is bound outside workspace backups under "
        "LocalAppData/SimilarSoundSearch/D03.\n"
        "No refill/reset: missing state requires restoration of the latest "
        "complete backup and registry.\n"
        "Stop the server before relocating: ... relocate --workspace <old> "
        "--destination <absent-new>\n"
        "Keep the environment at its installed path (Windows launchers embed "
        "it). Code archive extraction is relocatable.\n"
        "Optional C03/D02 result views are omitted; three exact D01 results "
        "and real catalogue are required.\n"
        "Retain completed files. Inventory/export the whole private workspace "
        "plus external allocation registry;\n"
        "keep private backups private. A future explicit policy change must "
        "append an authorization record and\n"
        "retain these cumulative charges; deleting ledgers is never renewal. "
        "D04 listening review has not started.\n",
        encoding="utf-8",
    )
    files = inventory(output)
    value = dict(
        schema_version="d03-release-1",
        release=RELEASE,
        core="0.3.0",
        source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        installed_bytes_bound=2 * 1024**3,
        dependency_expanded_bytes=sum(w["expanded"] for w in wheels),
        files=files,
        dependencies=[{k: v for k, v in w.items() if k != "path"} for w in wheels],
    )
    (output / "release.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    archive = output.with_name(output.name + ".zip")
    if archive.exists():
        raise RuntimeError("Archive already exists")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(output.rglob("*")):
            if p.is_file():
                entry = zipfile.ZipInfo(p.relative_to(output).as_posix(), (2026, 10, 25, 0, 0, 0))
                entry.external_attr = 0o100644 << 16
                z.writestr(entry, p.read_bytes())
    app = next(p for p in wheel_dir.glob("similar_sound_search-*.whl"))
    with zipfile.ZipFile(app) as z:
        payload = {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
    return dict(
        archive=str(archive.resolve()),
        bytes=archive.stat().st_size,
        sha256=sha(archive),
        wheel=app.name,
        wheel_sha256=sha(app),
        wheel_payload=payload,
        release_sha256=sha(output / "release.json"),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build(Path.cwd(), args.output.resolve()), indent=2))
