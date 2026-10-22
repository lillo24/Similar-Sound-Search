"""One explicit C04 correctness repair; retain first consumer and all spent work."""

import ast
import hashlib
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity, source_function_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
target = root / "manifests/processing/consumer-repair.json"
if target.exists():
    raise RuntimeError("C04 correctness repair already declared; do not overwrite")
path = root / "manifests/processing/consumer.json"
old = record(path)
current = code_identity()
changed = {k for k in old["code"] if old["code"][k] != current[k]}
if changed != {
    "cli.py",
    "processing/engine.py",
    "processing/job.py",
    "processing/commands.py",
} or set(current) - set(old["code"]) != {"processing/runner.py"}:
    raise RuntimeError("C04 repair drift outside exact declared scope")
base = "ff6d36a"
source = subprocess.check_output(
    ["git", "show", base + ":src/similar_sound_search/processing/engine.py"]
).decode()
now = (root / "src/similar_sound_search/processing/engine.py").read_text()
if (
    hashlib.sha256(source.replace("\r\n", "\n").encode()).hexdigest()
    != old["code"]["processing/engine.py"]
):
    raise RuntimeError("Original numerical source proof differs")
names = ("features", "score", "query_vectors", "load_scores")
proof = source_function_identity(source, names)
if proof != source_function_identity(now, names):
    raise RuntimeError("C04 feature/score computation changed")


def query_prefix(text):
    node = next(
        n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "query"
    )
    return ast.dump(ast.Module(body=node.body[:11], type_ignores=[]), include_attributes=False)


if query_prefix(source) != query_prefix(now):
    raise RuntimeError("C04 native query encoding prefix changed")
if (
    current["processing/cache.py"] != old["code"]["processing/cache.py"]
    or current["processing/contracts.py"] != old["code"]["processing/contracts.py"]
):
    raise RuntimeError("C04 semantic row/array contracts changed")
archive = root / "manifests/processing/consumers" / (old["record_hash"] + ".json")
archive.parent.mkdir(parents=True, exist_ok=True)
archive.write_bytes(path.read_bytes())
repair = dict(
    schema_version="c04-correctness-repair-1",
    previous_consumer=old["record_hash"],
    before_code=old["code"],
    consumer_code=current,
    changed_files=sorted(changed),
    added_coordinator="processing/runner.py",
    original_engine_source=source,
    unchanged_feature_score_functions=proof,
    query_encoding_prefix_sha256=hashlib.sha256(query_prefix(source).encode()).hexdigest(),
    changes=[
        "Windows single actual worker PID under deadline using the same venv paths/prefix",
        "native parent group excluded; event witnesses match actual native lineage",
        "preserve domain step/target/unit errors instead of overwriting at dispatcher boundary",
    ],
    accounting=(
        "Same pool; retain first results, failed clean timeout and reservations. "
        "Compatible rows are not re-embedded."
    ),
)
atomic_json(target, {**repair, "record_hash": digest(repair)})
classification = {**old["classification"], "processing/runner.py": "coordinator"}
value = {k: v for k, v in old.items() if k != "record_hash"}
value.update(
    code=current,
    classification=classification,
    previous_consumer=old["record_hash"],
    correctness_repair=digest(repair),
    numerical_hash=digest({k: v for k, v in current.items() if classification[k] == "numerical"}),
)
atomic_json(path, {**value, "record_hash": digest(value)})
print(digest(value))
