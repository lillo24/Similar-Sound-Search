"""Declare the exact first D01 storage-path/accounting repair, preserving all attempts."""

import ast
import hashlib
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "04526995ee400bf9b50661d63da0a005fb9313fca02ce16be9171a1aed44ab73":
    raise RuntimeError("Only the initial D01 repair is supported; retain later declarations")
code = code_identity()
changed = {k for k in old["code"] if code[k] != old["code"][k]}
if changed != {"application/history.py", "application/context.py", "application/job.py"}:
    raise RuntimeError("Unexpected repair scope")
base = root / "src/similar_sound_search"
sources = {
    k: subprocess.check_output(
        ["git", "show", old["source_commit"] + ":src/similar_sound_search/" + k]
    ).decode()
    for k in changed
}
for k, s in sources.items():
    if hashlib.sha256(s.replace("\r\n", "\n").encode()).hexdigest() != old["code"][k]:
        raise RuntimeError("Original source hash changed")


def functions(source):
    return {
        n.name: ast.dump(n, include_attributes=False)
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.FunctionDef)
    }


allowed = {
    "application/history.py": {"bank_reader", "compatible"},
    "application/context.py": {"charge", "publish"},
    "application/job.py": {"worker"},
}
for k, s in sources.items():
    before, after = functions(s), functions((base / k).read_text(encoding="utf-8"))
    drift = {n for n in set(before) | set(after) if before.get(n) != after.get(n)}
    if drift != allowed[k]:
        raise RuntimeError("Unclassified function drift: " + k + str(drift))
before = functions(sources["application/history.py"])["bank_reader"]
after_text = (
    (base / "application/history.py")
    .read_text(encoding="utf-8")
    .replace('"data/indexes/a06"', '"data/features"')
)
if functions(after_text)["bank_reader"] != before:
    raise RuntimeError("Historical reader changed beyond exact containment fix")


def proof(value):
    return dict(
        declaration_hash=value["record_hash"],
        numerical_hash=value["numerical_hash"],
        code_hash=digest(value["code"]),
        version="d01-consumer-1",
    )


new = {k: v for k, v in old.items() if k != "record_hash"}
new.update(
    code=code,
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
)
# Compatibility hashes exclude the self-referential declaration hash. Pin the after source
# map/numerical hash; the runtime computes the final declaration reference explicitly.
transition = dict(
    schema_version="d01-repair-1",
    before=proof(old),
    after_code=code,
    changed_files=sorted(changed),
    changed_functions={k: sorted(v) for k, v in allowed.items()},
    changed_inherited_files=[],
    numerical_functions_unchanged=True,
    original_sources=sources,
    reason="A06 arrays are in data/indexes/a06; tracked atomic writes replace repeated inventory. "
    "No samples/features/distances/aggregation changed. Failed attempts/charges retained.",
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
key = digest(transition)
new["compatibility"] = key
new["record_hash"] = digest(new)
atomic_json(root / "manifests/application/compatibility.json", {**transition, "record_hash": key})
atomic_json(root / "manifests/application/consumer.json", new)
print(new["record_hash"])
