"""Pin the pre-inference report-manifest owner correction; preserve all earlier producers."""

import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation.contracts import own_code

root = Path.cwd()
base = root / "manifests/assessment"
old = record(base / "consumer.json")
if old["record_hash"] != "a926eee13356c64b8c0a10c73651f641a9f1c8f19f6a4a028aabea73562c8e56":
    raise RuntimeError("D02 publication correction requires its exact pre-inference predecessor")
pool = record(root / "data/runs/assessment/pool.json")
if pool["counts"]["feature_windows"] or list(
    (root / "data/runs/assessment/execution-claims").glob("*.json")
):
    raise RuntimeError("D02 publication correction must precede model encoding and scoring")
code = code_identity()
own = own_code()
changed = {
    k for k in set(own) | set(old["evaluation_code"]) if own.get(k) != old["evaluation_code"].get(k)
}
if code != old["code"] or changed != {"report.py", "runtime.py"}:
    raise RuntimeError("D02 publication correction changed an unexpected source")
prior = record(base / "compatibility.json")
atomic_json(base / "consumers" / (old["record_hash"] + ".json"), old)
atomic_json(base / "proofs" / (prior["record_hash"] + ".json"), prior)
reference = dict(
    declaration_hash=old["record_hash"],
    numerical_hash=old["numerical_hash"],
    code_hash=digest(old["code"]),
    version="d02-consumer-1",
)
proof = {
    k: v
    for k, v in prior.items()
    if k not in {"record_hash", "reason", "predecessor", "accepted_previous"}
}
proof.update(
    predecessor=prior["record_hash"],
    accepted_previous=[*prior["accepted_previous"], reference],
    reason=(
        "Before inference: report allowlist manifest stays within the record owner; "
        "static HTML/audio remain separate allowlisted artifacts. No renderer, model, "
        "metric, rank or gate changes."
    ),
)
atomic_json(base / "compatibility.json", {**proof, "record_hash": digest(proof)})
value = dict(
    schema_version="d02-consumer-1",
    code=code,
    evaluation_code=own,
    compatibility=digest(proof),
    numerical_hash=old["numerical_hash"],
    predecessor=old["record_hash"],
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
)
atomic_json(base / "consumer.json", {**value, "record_hash": digest(value)})
print(digest(value))
