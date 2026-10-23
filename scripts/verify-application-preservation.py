"""D01 read-only baseline: retain C04 partial records and every earlier artifact."""

import hashlib
import json
import sys
from pathlib import Path

OWNED = (
    "data/runs/application/",
    "data/features/application/",
    "data/audio/application/",
    "reports/local/d01/",
    "manifests/application/",
)


def inventory(root):
    paths = [
        p
        for name in ("data", "manifests", "reports/local", "config")
        for p in (root / name).rglob("*")
    ]
    paths += list(root.glob("*.mp3")) + [root / "AGENTS.md", root / ".gitattributes"]
    result = {}
    for path in sorted(set(paths)):
        name = path.relative_to(root).as_posix()
        if not path.is_file() or name.startswith(OWNED) or name == "config/application.json":
            continue
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1048576), b""):
                h.update(chunk)
        result[name] = {"bytes": path.stat().st_size, "sha256": h.hexdigest()}
    return result


def main():
    root = Path.cwd()
    directory = root / "reports/local/d01"
    directory.mkdir(parents=True, exist_ok=True)
    before = directory / "preservation-before.json"
    now = inventory(root)
    if sys.argv[1:] == ["capture"]:
        if before.exists():
            raise RuntimeError("D01 baseline already exists; never reset history")
        before.write_text(json.dumps(now, indent=2), encoding="utf-8")
        print(json.dumps({"captured": len(now)}))
        return
    old = json.loads(before.read_text(encoding="utf-8"))
    changed = [k for k in old if old[k] != now.get(k)]
    added = sorted(set(now) - set(old))
    allowed = [p for p in added if p.startswith("data/audio/prepared/")]
    unexpected = sorted(set(added) - set(allowed))
    value = dict(
        state="verified" if not changed and not unexpected else "failed",
        historical_files=len(old),
        changed_or_missing=changed,
        unexpected_additions=unexpected,
        new_shared_immutable_preparation=allowed,
        c01_denied_staging="inventoried and retained; no deletion attempted",
    )
    (directory / "preservation-after.json").write_text(
        json.dumps(value, indent=2), encoding="utf-8"
    )
    print(json.dumps({**value, "new_shared_immutable_preparation": len(allowed)}, indent=2))
    if changed or unexpected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
