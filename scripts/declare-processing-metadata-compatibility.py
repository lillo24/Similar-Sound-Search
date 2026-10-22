"""Declare only the lossless metadata codec/proof-reference upgrade, preserving plans."""

import ast
import hashlib
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity, source_function_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
target = root / "manifests/processing/metadata-compatibility.json"
if target.exists():
    raise RuntimeError("C04 metadata compatibility already declared; preserve it")
path = root / "manifests/processing/consumer.json"
old = record(path)
current = code_identity()
allowed = {
    "processing/api.py",
    "processing/job.py",
    "processing/contracts.py",
    "processing/engine.py",
}
if {k for k in old["code"] if old["code"][k] != current[k]} != allowed or set(current) - set(
    old["code"]
) != {"processing/records.py"}:
    raise RuntimeError("C04 metadata upgrade has unclassified drift")
base = "bb2721c"
proofs, originals = {}, {}
for name, functions in {
    "processing/contracts.py": (
        "source_key",
        "row_identity",
        "row_key",
        "validate_input",
        "native_rows",
    ),
    "processing/job.py": ("reserve", "settle", "worker"),
    "processing/engine.py": ("features", "query", "query_vectors", "load_scores", "aggregate"),
}.items():
    source = subprocess.check_output(
        ["git", "show", base + ":src/similar_sound_search/" + name]
    ).decode()
    if hashlib.sha256(source.replace("\r\n", "\n").encode()).hexdigest() != old["code"][name]:
        raise RuntimeError("C04 original source proof differs: " + name)
    expected = source_function_identity(source, functions)
    if expected != source_function_identity(
        (root / "src/similar_sound_search" / name).read_text(), functions
    ):
        raise RuntimeError("C04 numerical/reservation boundary changed: " + name)
    proofs[name], originals[name] = expected, source


def numerical_calls(source):
    return sorted(
        ast.dump(n, include_attributes=False)
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "engine"
    )


if numerical_calls(originals["processing/job.py"]) != numerical_calls(
    (root / "src/similar_sound_search/processing/job.py").read_text()
):
    raise RuntimeError("C04 unit numerical arguments changed")


def scoring_body(source):
    node = next(
        n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "score"
    )
    node.body = [
        n
        for n in node.body
        if not (
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "identity" for t in n.targets)
        )
    ]
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


score_body = scoring_body(originals["processing/engine.py"])
if score_body != scoring_body((root / "src/similar_sound_search/processing/engine.py").read_text()):
    raise RuntimeError("C04 scoring computation changed")
classification = {**old["classification"], "processing/records.py": "coordinator"}
numerical = digest({k: v for k, v in current.items() if classification[k] == "numerical"})
before = dict(
    declaration_hash=old["record_hash"],
    code=old["code"],
    numerical_hash=old["numerical_hash"],
    version="c04-consumer-1",
)
value = dict(
    schema_version="c04-metadata-compatibility-1",
    before_consumer=before,
    after_code=current,
    after_numerical_hash=numerical,
    changed_files=sorted(allowed),
    added_coordinator="processing/records.py",
    unchanged_functions=proofs,
    original_sources=originals,
    numerical_calls_unchanged=True,
    unchanged_score_body=score_body,
    scope=(
        "Lossless row-reference codec, compact consumer proofs and exact ordered candidate digest. "
        "Same plan, units, arrays, numerical calls and allowance."
    ),
    accounting=(
        "Old records and charges retained; only future metadata is smaller. "
        "Committed units revalidate on resume."
    ),
)
atomic_json(target, {**value, "record_hash": digest(value)})
archive = root / "manifests/processing/consumers" / (old["record_hash"] + ".json")
archive.write_bytes(path.read_bytes())
consumer = {k: v for k, v in old.items() if k != "record_hash"}
consumer.update(
    code=current,
    classification=classification,
    numerical_hash=numerical,
    previous_consumer=old["record_hash"],
    metadata_compatibility=digest(value),
)
atomic_json(path, {**consumer, "record_hash": digest(consumer)})
print(digest(consumer))
