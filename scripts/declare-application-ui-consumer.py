"""Pin query-independent metadata/media reuse and original saved-query navigation."""

import ast
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != "1081f28094960bc7d1c0bda5280bafbea644b97969c9ec6fda65c586cc3520a8":
    raise RuntimeError("UI consumption declaration must follow exact finalization repair")
code = code_identity()
changed = {k for k in code if code[k] != old["code"].get(k)}
if changed != {"application/job.py", "application/media.py", "application/queries.py"}:
    raise RuntimeError("Unexpected consumption drift")
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


expected = {
    "application/job.py": {"perform"},
    "application/media.py": {"cached_clip", "cards"},
    "application/queries.py": {"inventory"},
}
for k, s in sources.items():
    a, b = funcs(s), funcs((root / "src/similar_sound_search" / k).read_text(encoding="utf-8"))
    if {n for n in a if a[n] != b[n]} != expected[k]:
        raise RuntimeError("Unclassified function change: " + k)


def clip_tail(s):
    n = next(
        n for n in ast.parse(s).body if isinstance(n, ast.FunctionDef) and n.name == "cached_clip"
    )
    start = next(
        i
        for i, x in enumerate(n.body)
        if isinstance(x, ast.Expr)
        and isinstance(x.value, ast.Call)
        and isinstance(x.value.func, ast.Attribute)
        and x.value.func.attr == "charge"
    )
    n.body = n.body[start:]
    return ast.dump(n, include_attributes=False)


if clip_tail(sources["application/media.py"]) != clip_tail(
    (root / "src/similar_sound_search/application/media.py").read_text(encoding="utf-8")
):
    raise RuntimeError("Actual clip conversion/verification/publication changed")
proof = record(root / "manifests/application/compatibility.json")
atomic_json(
    root / "manifests/application/compatibilities" / (proof["record_hash"] + ".json"), proof
)
atomic_json(root / "manifests/application/consumers" / (old["record_hash"] + ".json"), old)
proof = {k: v for k, v in proof.items() if k != "record_hash"}
proof.update(
    after_code=code,
    previous_declaration=old["record_hash"],
    ui_consumption=dict(
        original_sources=sources,
        changed_functions={k: sorted(v) for k, v in expected.items()},
        clip_numerical_tail_unchanged=True,
        reason="Committed aggregation uses query metadata, cached media uses immutable clips; "
        "one successful "
        "source decode retained only inside a bounded worker when creating scored/context clips. "
        "Saved original B03 revisions are navigable and explicitly imported into D01. "
        "All feature/scoring/fusion/native/decoder primitives stay unchanged.",
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
