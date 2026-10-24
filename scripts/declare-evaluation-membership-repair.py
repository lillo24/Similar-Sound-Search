"""Declare genuine alias memberships before accepting the first D02 prediction."""

import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation.contracts import own_code

root = Path.cwd()
base = root / "manifests/assessment"
old = record(base / "consumer.json")
if old["record_hash"] != "ca63340adb13c9e9707fed8162470c0e877d9b59495466432ec35c190bd84d74":
    raise RuntimeError("D02 membership repair requires the exact publication consumer")
if list((root / "data/runs/assessment/prediction-bindings").glob("*.json")):
    raise RuntimeError("D02 membership repair cannot follow an accepted prediction")
code = code_identity()
own = own_code()
changed = {
    k for k in set(own) | set(old["evaluation_code"]) if own.get(k) != old["evaluation_code"].get(k)
}
if code != old["code"] or changed != {"membership.py", "pipeline.py"}:
    raise RuntimeError("D02 membership repair changes unexpected scientific or product code")
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
        "Before any accepted prediction/quality summary: genuine recording-specific "
        "native memberships for aliases sharing PCM cache rows. Raw feature vectors, "
        "distances, grids, support counts, C02 fusion, metrics, gate and population "
        "remain unchanged; retain the first aggregation refusal and its charges."
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
