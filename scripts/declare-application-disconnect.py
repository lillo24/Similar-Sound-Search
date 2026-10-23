"""Declare narrow idle HTTP disconnect handling without changing numerical producers."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "05ac2f64bbe559db786aa2e3b95427d47b4afe977a34a356522494d0de064a45":
    raise RuntimeError("Disconnect declaration must follow the exact navigation consumer")
code = code_identity()
changed = {k for k in code if code[k] != old["code"].get(k)}
if changed != {"application/server.py"}:
    raise RuntimeError("Unexpected HTTP disconnect drift")


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
    expected = {"make_server"}
    if differences != expected:
        raise RuntimeError("Changed non-HTTP function: " + name)
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
    idle_disconnect=dict(
        previous_sources=previous,
        reason="Handle only peer abort/reset/broken-pipe at the HTTP request-line boundary, "
        "where a Windows browser refresh can close an idle socket. Other I/O/domain "
        "errors propagate. No worker dispatch, DSP, pool, result or media identity changes.",
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
