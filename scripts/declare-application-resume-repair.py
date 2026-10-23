"""Pin semantic resume validation across the already declared coordinator repairs."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "1d020e188cc24dde7187fc1e4697859c8821340dd28a1f9af74394f707737699":
    raise RuntimeError("Resume repair must follow exact coordinator repair")
code = code_identity()
if {k for k in code if code[k] != old["code"].get(k)} != {"application/job.py"}:
    raise RuntimeError("Unexpected resume repair drift")
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
if {k for k in set(a) | set(b) if a.get(k) != b.get(k)} != {"worker", "validate_resumed"}:
    raise RuntimeError("Unclassified function drift")


def numerical_calls(s):
    return sorted(
        ast.dump(n, include_attributes=False)
        for n in ast.walk(ast.parse(s))
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id in {"pipeline", "queries", "media"}
    )


if numerical_calls(before) != numerical_calls(after):
    raise RuntimeError("Numerical call arguments changed")
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    resume_repair=dict(
        previous_source=before,
        numerical_calls_unchanged=True,
        reason="Fresh consumer identity differs after declared coordinator edits. Compare exact "
        "semantic source/score dependencies; retain both consumer proofs and a new resume receipt.",
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
