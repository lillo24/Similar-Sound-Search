"""Pin result-scoped media authorization; all numerical and media producers unchanged."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "b44a78a24dbf5c637f7e35317db5a56ae823c39c1ef1711c0e06d4ba9555c922":
    raise RuntimeError("Media scope must follow exact settlement declaration")
code = code_identity()
if {k for k in code if code[k] != old["code"].get(k)} != {
    "application/api.py",
    "application/server.py",
}:
    raise RuntimeError("Unexpected result-scope drift")
sources = {
    k: subprocess.check_output(
        ["git", "show", old["source_commit"] + ":src/similar_sound_search/" + k]
    ).decode()
    for k in ("application/api.py", "application/server.py")
}
before = ast.parse(sources["application/api.py"])
after = ast.parse(
    (root / "src/similar_sound_search/application/api.py").read_text(encoding="utf-8")
)
after.body = [
    n for n in after.body if not (isinstance(n, ast.FunctionDef) and n.name == "result_media")
]
if ast.dump(before, include_attributes=False) != ast.dump(after, include_attributes=False):
    raise RuntimeError("Existing query/job/result validation changed")
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    media_scope=dict(
        original_sources=sources,
        reason="Authorize each candidate clip through its immutable complete result membership. "
        "The preview route accepts reference crops only. HEAD has no body. "
        "No producer/math change.",
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
