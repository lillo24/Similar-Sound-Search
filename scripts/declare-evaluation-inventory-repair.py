"""One pre-inference D02 inventory/publication repair; archive every prior declaration."""

import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation.contracts import D01_CONSUMER, own_code

root = Path.cwd()
directory = root / "manifests/assessment"
before = record(directory / "consumer.json")
if before["record_hash"] != "7ab65b5c1f60aa00fbada7ef297887b1b5aa342d7794c654422d93d30fa1331f":
    raise RuntimeError("D02 inventory repair requires the exact original pre-inference consumer")
if list((root / "data/runs/assessment/execution-claims").glob("*.json")):
    raise RuntimeError("D02 pre-inference repair cannot follow comparative scoring")
pool = record(root / "data/runs/assessment/pool.json")
if pool["counts"]["feature_windows"]:
    raise RuntimeError("D02 pre-inference inventory repair cannot follow model encoding")
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != D01_CONSUMER:
    raise RuntimeError("D01 predecessor differs")
code = code_identity()
changed = sorted(k for k, h in old["code"].items() if code.get(k) != h)
if set(changed) != {
    "application/api.py",
    "application/server.py",
    "application/queries.py",
    "application/history.py",
    "application/context.py",
} or set(code) != set(old["code"]):
    raise RuntimeError("D02 repair alters inherited numerical files")
own = own_code()
delta = {
    k
    for k in set(own) | set(before["evaluation_code"])
    if own.get(k) != before["evaluation_code"].get(k)
}
if delta != {"budget.py", "commands.py", "context.py", "jobs.py", "runtime.py"}:
    raise RuntimeError("D02 repair changes unexpected evaluation definitions: " + str(delta))
prior = record(directory / "compatibility.json")
atomic_json(directory / "consumers" / (before["record_hash"] + ".json"), before)
atomic_json(directory / "proofs" / (prior["record_hash"] + ".json"), prior)
reference = dict(
    declaration_hash=before["record_hash"],
    numerical_hash=before["numerical_hash"],
    code_hash=digest(before["code"]),
    version="d02-consumer-1",
)
proof = dict(
    schema_version="d02-scoped-compatibility-1",
    before_consumer=old["record_hash"],
    before_code=old["code"],
    after_code=code,
    changed_files=changed,
    accepted_previous=[*prior["accepted_previous"], reference],
    predecessor=prior["record_hash"],
    reason=(
        "Before any model/scored query: fresh native directory-entry inventory with "
        "unchanged caps; refresh coordinator publication transaction; lossless bounded "
        "assessment storage. No retrieval, renderer, metric or gate definition changed."
    ),
)
atomic_json(directory / "compatibility.json", {**proof, "record_hash": digest(proof)})
value = dict(
    schema_version="d02-consumer-1",
    code=code,
    evaluation_code=own,
    compatibility=digest(proof),
    numerical_hash=before["numerical_hash"],
    predecessor=before["record_hash"],
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
)
atomic_json(directory / "consumer.json", {**value, "record_hash": digest(value)})
print(digest(value))
