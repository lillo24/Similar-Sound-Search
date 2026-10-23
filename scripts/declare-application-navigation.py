"""Declare completed-result metadata navigation without changing numerical producers."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "2aa105179be086ef84f5e4436eca7fbfc552616a29e7f49928e11afeea6f4e3e":
    raise RuntimeError("Navigation declaration must follow the exact resume-state consumer")
code = code_identity()
changed = {k for k in code if code[k] != old["code"].get(k)}
if changed != {"application/api.py", "application/server.py"}:
    raise RuntimeError("Unexpected completed-result navigation drift")


def functions(source):
    return {
        n.name: ast.dump(n, include_attributes=False)
        for n in ast.parse(source).body
        if isinstance(n, ast.FunctionDef)
    }


previous = {}
for name in sorted(changed):
    before = subprocess.check_output(
        ["git", "show", old["source_commit"] + ":src/similar_sound_search/" + name]
    ).decode()
    after = (root / "src/similar_sound_search" / name).read_text(encoding="utf-8")
    a, b = functions(before), functions(after)
    differences = {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
    expected = {"completed_searches"} if name == "application/api.py" else {"make_server"}
    if differences != expected:
        raise RuntimeError("Changed non-navigation function: " + name)
    previous[name] = before
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    completed_navigation=dict(
        previous_sources=previous,
        reason="List at most 64 complete search results in bootstrap; opening a saved "
        "result restores its exact resolved query and policy without a worker or pool write. "
        "No numerical code, prior producer or compatibility boundary changes.",
    ),
)
key = digest(proof)
value = {k: v for k, v in old.items() if k != "record_hash"}
value.update(
    code=code,
    compatibility=key,
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
)
atomic_json(root / "manifests/application/compatibility.json", {**proof, "record_hash": key})
atomic_json(root / "manifests/application/consumer.json", {**value, "record_hash": digest(value)})
print(digest(value))
