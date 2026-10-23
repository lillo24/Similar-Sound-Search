"""Declare the HTTP resume acknowledgement race fix, with numerical code unchanged."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "37b5ba9d9fc26c446eceb52b6b4316afda4d0b6422b6119db0556fe217a6e6c7":
    raise RuntimeError("Resume-state declaration must follow exact admission correction")
code = code_identity()
if {k for k in code if code[k] != old["code"].get(k)} != {"application/api.py"}:
    raise RuntimeError("Unexpected resume-state drift")
before = subprocess.check_output(
    ["git", "show", old["source_commit"] + ":src/similar_sound_search/application/api.py"]
).decode()
after = (root / "src/similar_sound_search/application/api.py").read_text(encoding="utf-8")


def functions(s):
    return {
        n.name: ast.dump(n, include_attributes=False)
        for n in ast.parse(s).body
        if isinstance(n, ast.FunctionDef)
    }


a, b = functions(before), functions(after)
if {k for k in a if a[k] != b[k]} != {"resume_control"}:
    raise RuntimeError("Changed non-control function")
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    resume_state=dict(
        previous_source=before,
        reason="Persist a protected pending acknowledgement "
        "before resume returns 202; polling cannot consume the prior terminal state "
        "as the new outcome. "
        "Completed jobs reopen; numerical artifacts and committed work stay unchanged.",
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
