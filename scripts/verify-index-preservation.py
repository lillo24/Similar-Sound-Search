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
NAVIGATION = """
## C01 passage banks

`indexing.json` fixes C01's separate offline ceilings, two candidate grids,
bounded shards and original/pitch-off defaults. [INDEXING.md](../docs/INDEXING.md)
owns bank identities, native maps, immutable snapshots, component limits,
predeclared admission, exact per-bank verification and charged resume/reuse.
"""


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
        documentation = []
        name = "config/README.md"
        if name in changed:
            before = baseline.parent / "config-readme-before.md"
            if hashlib.sha256(before.read_bytes()).hexdigest() != old[name]["sha256"]:
                raise RuntimeError("C01 navigation-map baseline differs; preserve all evidence")
            if (root / name).read_text(encoding="utf-8") == before.read_text(
                encoding="utf-8"
            ) + NAVIGATION:
                changed.remove(name)
                documentation.append(
                    {
                        "path": name,
                        "before": old[name],
                        "after": values[name],
                        "change": "exact C01 navigation section only; "
                        "runtime JSON configurations unchanged",
                    }
                )
        result = {
            "state": "verified" if not changed and not added else "failed",
            "files": len(old),
            "unchanged": len(old) - len(changed) - len(documentation),
            "changed_or_missing": changed,
            "unexpected_additions": added,
            "documented_navigation_changes": documentation,
        }
        (baseline.parent / "preservation-after.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
    print(json.dumps(result, indent=2))
    return 0 if result["state"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
