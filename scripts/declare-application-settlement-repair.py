"""Pin exactly-once worker settlement even when later control attempts settle first."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "a2d1daf118b604a4e2b9e7b389ca07d2583244ef18ed47d957be01e37e97ad10":
    raise RuntimeError("Settlement declaration must follow exact UI consumer")
code = code_identity()
if {k for k in code if code[k] != old["code"].get(k)} != {"application/context.py"}:
    raise RuntimeError("Unexpected settlement drift")
before = subprocess.check_output(
    ["git", "show", old["source_commit"] + ":src/similar_sound_search/application/context.py"]
).decode()
after = (root / "src/similar_sound_search/application/context.py").read_text(encoding="utf-8")


def functions(s):
    return {
        n.name: ast.dump(n, include_attributes=False)
        for n in ast.walk(ast.parse(s))
        if isinstance(n, ast.FunctionDef)
    }


a, b = functions(before), functions(after)
if {n for n in a if a[n] != b[n]} != {"__init__", "reserve_attempt", "terminal"}:
    raise RuntimeError("Changed non-settlement function")
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    settlement_repair=dict(
        previous_source=before,
        reason="Merge this attempt's idempotent settlement delta without rolling back "
        "later controls. Pre-admit state/journal/recovery geometry with a bounded "
        "256KiB slot inside the unchanged 32MiB protected ceiling. Historical attempts, "
        "counters and ceilings retained.",
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
