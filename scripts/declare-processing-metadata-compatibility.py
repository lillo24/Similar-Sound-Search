"""Declare only the lossless metadata codec/proof-reference upgrade, preserving plans."""

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity, source_function_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
target = root / "manifests/processing/metadata-compatibility.json"
revision = sys.argv[1:] == ["--revision-2"]
if target.exists() and not revision:
    raise RuntimeError("C04 metadata compatibility already declared; preserve it")
path = root / "manifests/processing/consumer.json"
latest = record(path)
old = (
    record(
        root
        / "manifests/processing/consumers"
        / "792dbd5d1f6cfc223e83b9565ee0f77e668cdfed8c4d551e50ad791c02677fdf.json"
    )
    if revision
    else latest
)
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
    "processing/job.py": ("reserve", "settle"),
    "processing/engine.py": ("features", "query", "query_vectors", "load_scores"),
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

    def target(n):
        return (
            n.targets[0].id
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
            else None
        )

    prefix = [n for n in node.body if target(n) in {"refs", "q", "query_hash", "matrix"}]
    numerical, active = [], False
    for n in node.body:
        if target(n) == "examples":
            active = True
        if active:
            numerical.append(n)
        if target(n) == "result":
            break
    node.body = prefix + numerical
    for call in ast.walk(node):
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "query_vectors_cached"
        ):
            call.func.id = "query_vectors"
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


score_body = scoring_body(originals["processing/engine.py"])
if score_body != scoring_body((root / "src/similar_sound_search/processing/engine.py").read_text()):
    raise RuntimeError("C04 scoring computation changed")


def aggregation_body(source):
    node = next(
        n
        for n in ast.parse(source).body
        if isinstance(n, ast.FunctionDef) and n.name == "aggregate"
    )
    node.body = [
        n
        for n in node.body
        if not (
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "arms_to_publish" for t in n.targets)
        )
        and not (
            isinstance(n, ast.If)
            and any(isinstance(x, ast.Name) and x.id == "arms_to_publish" for x in ast.walk(n))
        )
    ]
    for n in node.body:
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "arm":
            n.iter = ast.parse("('legacy-mean','event-legacy','event-multi')", mode="eval").body
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


aggregate_body = aggregation_body(originals["processing/engine.py"])
if aggregate_body != aggregation_body(
    (root / "src/similar_sound_search/processing/engine.py").read_text()
):
    raise RuntimeError("C04 aggregation computation changed")
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
    unchanged_aggregation_body=aggregate_body,
    worker_query_cache="Exact query/feature identity within one worker; loader/math unchanged",
    publication="Complete legacy and multi-event groups; event-legacy when requested",
    validation_batch=8,
    cancellation="Stop admission on cancel; in-progress state during validation",
    scope=(
        "Lossless row-reference codec, compact consumer proofs and exact ordered candidate digest. "
        "Same plan, units, arrays, numerical calls and allowance."
    ),
    accounting=(
        "Old records and charges retained; only future metadata is smaller. "
        "Committed units revalidate on resume."
    ),
)
if revision:
    earlier = record(target)
    preserved = (
        root / "manifests/processing/metadata-compatibilities" / (earlier["record_hash"] + ".json")
    )
    preserved.parent.mkdir(parents=True, exist_ok=True)
    if preserved.exists():
        raise RuntimeError(
            "C04 prior metadata declaration already retained; do not repeat revision"
        )
    preserved.write_bytes(target.read_bytes())
atomic_json(target, {**value, "record_hash": digest(value)})
archive = root / "manifests/processing/consumers" / (latest["record_hash"] + ".json")
archive.write_bytes(path.read_bytes())
consumer = {k: v for k, v in latest.items() if k != "record_hash"}
consumer.update(
    code=current,
    classification=classification,
    numerical_hash=numerical,
    previous_consumer=latest["record_hash"],
    metadata_compatibility=digest(value),
)
atomic_json(path, {**consumer, "record_hash": digest(consumer)})
print(digest(consumer))
