"""Verify historical delivery bytes; only explicit C02 roots/navigation are excluded."""

import hashlib
import json
from pathlib import Path

OWNED = (
    "data/runs/retrieval/",
    "data/features/retrieval/",
    "data/audio/retrieval/",
    "manifests/retrieval/",
    "reports/local/c02/",
)
NAVIGATION = """
## C02 candidate retrieval

`retrieval.json` fixes the independent C02 allowance, baseline default, experimental
event/rank fusion, raw support cap, overlap rule and shortlist/display limits.
[RETRIEVAL.md](../docs/RETRIEVAL.md) owns historical adapters, exact evidence,
event/variant semantics, native scored/context support and the C03 export.
"""


def inventory(root):
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
    values = {}
    for path in sorted(set(candidates)):
        name = path.relative_to(root).as_posix()
        if (
            path.is_file()
            and name not in {"data/runs/.c02-worker.lock", "config/retrieval.json"}
            and not name.startswith(OWNED)
        ):
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            values[name] = {"bytes": path.stat().st_size, "sha256": h.hexdigest()}
    return values


def main():
    root = Path.cwd()
    directory = root / "reports/local/c02"
    old = json.loads((directory / "preservation-before.json").read_text(encoding="utf-8"))
    current = inventory(root)
    changed = [k for k, v in old.items() if current.get(k) != v]
    added = sorted(set(current) - set(old))
    navigation = []
    name = "config/README.md"
    if name in changed:
        before = directory / "config-readme-before.md"
        if hashlib.sha256(before.read_bytes()).hexdigest() != old[name]["sha256"]:
            raise RuntimeError("C02 config navigation baseline differs")
        if (root / name).read_text(encoding="utf-8") == before.read_text(
            encoding="utf-8"
        ) + NAVIGATION:
            changed.remove(name)
            navigation.append(
                {
                    "path": name,
                    "before": old[name],
                    "after": current[name],
                    "change": "exact C02 navigation addition; runtime configuration JSON unchanged",
                }
            )
    result = {
        "state": "verified" if not changed and not added else "failed",
        "files": len(old),
        "unchanged": len(old) - len(changed) - len(navigation),
        "changed_or_missing": changed,
        "unexpected_additions": added,
        "documented_navigation_changes": navigation,
        "c01_staging": "inventoried and retained; denied deletion untouched",
    }
    (directory / "preservation-after.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return int(result["state"] != "verified")


if __name__ == "__main__":
    raise SystemExit(main())
