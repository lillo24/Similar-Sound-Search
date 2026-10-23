"""Declare exact finalization/accounting adapters, preserving every earlier declaration."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "be3e4cfc30433f3f733f323bd50a67e5142dd5473785db829bd6f404d9087127":
    raise RuntimeError("Finalization repair must follow exact semantic resume declaration")
code = code_identity()
changed = {k for k in code if code[k] != old["code"].get(k)}
allowed = {
    "application/context.py",
    "application/job.py",
    "application/media.py",
    "application/server.py",
    "application/validation.py",
}
if changed != allowed:
    raise RuntimeError("Unclassified finalization drift: " + str(changed))
sources = {
    k: subprocess.check_output(
        ["git", "show", old["source_commit"] + ":src/similar_sound_search/" + k]
    ).decode()
    for k in changed
}


def funcs(s):
    return {
        n.name: ast.dump(n, include_attributes=False)
        for n in ast.parse(s).body
        if isinstance(n, ast.FunctionDef)
    }


before = funcs(sources["application/job.py"])
after = funcs((root / "src/similar_sound_search/application/job.py").read_text(encoding="utf-8"))
for k in ("perform", "committed", "units", "reconcile", "run"):
    if before[k] != after[k]:
        raise RuntimeError("Existing numerical/commit/reconciliation boundary changed: " + k)


def without_charge(s):
    tree = ast.parse(s)
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            n.body = [
                x
                for x in n.body
                if not (
                    isinstance(x, ast.Expr)
                    and isinstance(x.value, ast.Call)
                    and isinstance(x.value.func, ast.Attribute)
                    and isinstance(x.value.func.value, ast.Name)
                    and x.value.func.value.id == "owner"
                    and x.value.func.attr == "charge"
                )
            ]
    return ast.dump(tree, include_attributes=False)


if without_charge(sources["application/media.py"]) != without_charge(
    (root / "src/similar_sound_search/application/media.py").read_text(encoding="utf-8")
):
    raise RuntimeError("Media sample/crop/conversion changed")
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    finalization_repair=dict(
        original_sources=sources,
        changed_files=sorted(changed),
        numerical_units_unchanged=True,
        media_numerical_ast_unchanged=True,
        reason="Bounded remaining-path admission in the same pool; actual source byte/array "
        "revalidation after committed aggregation; keep pool scans outside mutex; "
        "account extra clip verification reads; local projection style and empty favicon "
        "response. No feature/ranking/sample change.",
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
