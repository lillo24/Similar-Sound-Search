"""Pin conservative new-score geometry and committed-output finalization adapters."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "c4160fd7b7a47026e6de0c804b6c68d921979d8fe26004255e4d1c057bd43093":
    raise RuntimeError("Admission correction must follow exact result-media declaration")
code = code_identity()
changed = {k for k in code if code[k] != old["code"].get(k)}
expected = {
    "application/api.py": {"submit"},
    "application/history.py": {"compatible"},
    "application/job.py": {"worker", "_run"},
    "application/pipeline.py": {"geometry_estimate"},
    "application/server.py": {"make_server"},
    "application/validation.py": {"finalization"},
}
if changed != set(expected):
    raise RuntimeError("Unexpected recovery scope")
sources = {
    k: subprocess.check_output(
        ["git", "show", old["source_commit"] + ":src/similar_sound_search/" + k]
    ).decode()
    for k in changed
}


def functions(s):
    return {
        n.name: ast.dump(n, include_attributes=False)
        for n in ast.parse(s).body
        if isinstance(n, ast.FunctionDef)
    }


for k, s in sources.items():
    a, b = (
        functions(s),
        functions((root / "src/similar_sound_search" / k).read_text(encoding="utf-8")),
    )
    if {n for n in a if a[n] != b[n]} != expected[k]:
        raise RuntimeError("Unclassified function drift: " + k)
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
prior = dict(
    declaration_hash=old["record_hash"],
    numerical_hash=old["numerical_hash"],
    code_hash=digest(old["code"]),
    version="d01-consumer-1",
)
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    additional_before=[prior],
    admission_repair=dict(
        original_sources=sources,
        changed_functions={k: sorted(v) for k, v in expected.items()},
        reason="Conservatively include new per-example source-score writes, metadata "
        "duplication and finalization in admission. Reject unsupported settings before "
        "reservation. Remaining media recovery validates committed arrays/query/scores "
        "and consumes originals only for new clips. No re-encoding or ranking/sample "
        "rule changes. Windows client aborts end HTTP delivery.",
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
