"""Read-only historical inventory; C04 never removes retained staging or caches."""

import hashlib
import json
import sys
from pathlib import Path

OWNED = (
    "data/runs/processing/", "data/features/processing/", "data/indexes/processing/",
    "data/audio/processing/", "reports/local/c04/", "manifests/processing/",
)
NAVIGATION = "\n## C04 processing\n\n`processing.json` fixes one cumulative pool for every explicit revision, job and retry.\n[PROCESSING.md](../docs/PROCESSING.md) owns the dependency table, transactional API,\nread-only adoption and D01 handoff. No automatic garbage collection is provided.\n"


def inventory(root):
    paths = [p for name in ("data", "manifests", "reports/local", "config")
             for p in (root / name).rglob("*")]
    paths += list(root.glob("*.mp3"))
    paths += [root / p for p in ("AGENTS.md", ".gitattributes",
              "src/similar_sound_search/search/pitch.py",
              "src/similar_sound_search/matchers/acoustic.py",
              "src/similar_sound_search/matchers/efficientat.py",
              "src/similar_sound_search/matchers/efficientat_model.py")]
    result = {}
    for path in sorted(set(paths)):
        name = path.relative_to(root).as_posix()
        if not path.is_file() or name.startswith(OWNED) or name in {
            "config/processing.json", "data/runs/.c04-worker.lock",
            "data/runs/.c04-control.lock", "data/runs/.c04-coordinator.lock",
        }:
            continue
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
        result[name] = {"bytes": path.stat().st_size, "sha256": h.hexdigest()}
    return result


def main():
    root = Path.cwd()
    directory = root / "reports/local/c04"
    directory.mkdir(parents=True, exist_ok=True)
    before = directory / "preservation-before.json"
    if sys.argv[1:] == ["capture"]:
        if before.exists():
            raise RuntimeError("C04 preservation baseline already exists")
        value = inventory(root)
        before.write_text(json.dumps(value, indent=2), encoding="utf-8")
        (directory / "config-readme-before.md").write_bytes((root / "config/README.md").read_bytes())
        print(json.dumps({"captured": len(value)}))
        return
    old = json.loads(before.read_text(encoding="utf-8"))
    now = inventory(root)
    changed = [k for k in old if old[k] != now.get(k)]
    allowed = []
    if "config/README.md" in changed:
        saved = directory / "config-readme-before.md"
        if hashlib.sha256(saved.read_bytes()).hexdigest() != old["config/README.md"]["sha256"]:
            raise RuntimeError("config README baseline changed")
        if (root / "config/README.md").read_text(encoding="utf-8") == saved.read_text(
            encoding="utf-8"
        ) + NAVIGATION:
            changed.remove("config/README.md")
            allowed.append("exact C04 configuration navigation addition")
    added = sorted(set(now) - set(old))
    value = {"state": "verified" if not changed and not added else "failed",
             "files": len(old), "unchanged": len(old) - len(changed) - len(allowed),
             "changed_or_missing": changed, "unexpected_additions": added,
             "allowed": allowed, "c01_denied_staging": "inventoried and retained"}
    (directory / "preservation-after.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    print(json.dumps(value, indent=2))
    if changed or added:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
