"""Extend the exact D01 proof for per-worker coordinator deadlines; no numerical drift."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "d7c6491ac1bdd4384cf46136728a2a332de443435daee9f180fb5ab9c0bca90f":
    raise RuntimeError("Coordinator repair must follow the pinned first repair")
code = code_identity()
changed = {k for k in old["code"] if old["code"][k] != code[k]}
if changed != {"application/job.py"}:
    raise RuntimeError("Unclassified source drift")
before = subprocess.check_output(
    ["git", "show", old["source_commit"] + ":src/similar_sound_search/application/job.py"]
).decode()
after = (root / "src/similar_sound_search/application/job.py").read_text(encoding="utf-8")


def functions(s):
    return {
        n.name: ast.dump(n, include_attributes=False)
        for n in ast.parse(s).body
        if isinstance(n, ast.FunctionDef)
    }


a, b = functions(before), functions(after)
if {k for k in a if a[k] != b[k]} != {"_run"}:
    raise RuntimeError("Changed numerical/worker function")
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    coordinator_repair=dict(
        function="_run",
        previous_source=before,
        reason="120s bounds individual children and coordinator transactions; aggregate time remains charged; no timer spans the whole multi-worker request",
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
