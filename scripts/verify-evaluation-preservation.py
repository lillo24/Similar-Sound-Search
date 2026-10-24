"""Read-only D02 historical inventory; retain every old stage and denied C01 staging."""

import hashlib
import json
import sys
from pathlib import Path

OWNED = (
    "data/runs/assessment/",
    "data/features/assessment/",
    "data/audio/assessment/",
    "reports/local/d02/",
    "manifests/assessment/",
)


def inventory(root):
    result = {}
    paths = [
        p
        for name in ("data", "manifests", "reports/local", "config")
        for p in (root / name).rglob("*")
    ]
    paths += list(root.glob("*.mp3")) + [root / "AGENTS.md", root / ".gitattributes"]
    for p in sorted(set(paths)):
        name = p.relative_to(root).as_posix()
        if not p.is_file() or name.startswith(OWNED) or name == "config/assessment.json":
            continue
        h = hashlib.sha256()
        with p.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1048576), b""):
                h.update(chunk)
        result[name] = dict(bytes=p.stat().st_size, sha256=h.hexdigest())
    return result


def main():
    root = Path.cwd()
    directory = root / "reports/local/d02"
    directory.mkdir(parents=True, exist_ok=True)
    baseline = directory / "preservation-before.json"
    now = inventory(root)
    if sys.argv[1:] == ["capture"]:
        if baseline.exists():
            raise RuntimeError("D02 baseline already captured; never replace history")
        baseline.write_text(json.dumps(now, indent=2), encoding="utf-8")
        print(json.dumps(dict(captured=len(now))))
        return
    before = json.loads(baseline.read_text(encoding="utf-8"))
    changed = [k for k in before if before[k] != now.get(k)]
    added = sorted(set(now) - set(before))
    prepared = [k for k in added if k.startswith("data/audio/prepared/")]
    unexpected = sorted(set(added) - set(prepared))
    value = dict(
        state="verified" if not changed and not unexpected else "failed",
        historical_files=len(before),
        changed_or_missing=changed,
        unexpected_additions=unexpected,
        new_shared_preparation=prepared,
        c01_denied_staging="retained; no deletion retried",
    )
    (directory / "preservation-after.json").write_text(
        json.dumps(value, indent=2), encoding="utf-8"
    )
    print(json.dumps({**value, "new_shared_preparation": len(prepared)}))
    if changed or unexpected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
