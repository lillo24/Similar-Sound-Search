"""Read-only history inventory; only C01 namespaces are excluded, never old caches."""

import argparse
import hashlib
import json
from pathlib import Path

OWNED = (
    "data/indexes/c01/",
    "data/features/indexing/",
    "data/runs/indexing/",
    "data/audio/indexing/",
    "manifests/indexing/",
    "reports/local/c01/",
)


def inventory(root):
    values = {}
    candidates = []
    for name in ("data", "manifests", "reports/local", "config"):
        candidates.extend((root / name).rglob("*"))
    candidates.extend(root.glob("*.mp3"))
    candidates.extend(
        root / p
        for p in (
            ".gitattributes",
            "src/similar_sound_search/search/pitch.py",
            "src/similar_sound_search/matchers/acoustic.py",
            "src/similar_sound_search/matchers/efficientat.py",
            "src/similar_sound_search/matchers/efficientat_model.py",
        )
    )
    for path in sorted(set(candidates)):
        name = path.relative_to(root).as_posix()
        if path.is_file() and name != "data/runs/.c01-worker.lock" and not name.startswith(OWNED):
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            values[name] = {"bytes": path.stat().st_size, "sha256": h.hexdigest()}
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "verify"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    baseline = root / "reports/local/c01/preservation-before.json"
    values = inventory(root)
    if args.action == "capture":
        if baseline.exists():
            raise RuntimeError("C01 baseline already exists; preserve it")
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(json.dumps(values, sort_keys=True), encoding="utf-8")
        result = {
            "state": "captured",
            "files": len(values),
            "bytes": sum(v["bytes"] for v in values.values()),
        }
    else:
        old = json.loads(baseline.read_text(encoding="utf-8"))
        changed = [k for k, v in old.items() if values.get(k) != v]
        added = sorted(set(values) - set(old))
        result = {
            "state": "verified" if not changed and not added else "failed",
            "files": len(old),
            "unchanged": len(old) - len(changed),
            "changed_or_missing": changed,
            "unexpected_additions": added,
        }
        (baseline.parent / "preservation-after.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
    print(json.dumps(result, indent=2))
    return 0 if result["state"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
