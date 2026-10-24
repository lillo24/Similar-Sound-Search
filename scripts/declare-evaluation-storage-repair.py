"""Pin a lossless storage/publication change; all scientific definitions remain frozen."""

import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation.contracts import own_code

root = Path.cwd()
base = root / "manifests/assessment"
old = record(base / "consumer.json")
if old["record_hash"] != "2f8652261914e5ccc00291fc641183ffc639a4090ef568d5e102e0908a853a5d":
    raise RuntimeError("D02 storage repair requires the exact membership consumer")
code = code_identity()
own = own_code()
changed = {
    k for k in set(own) | set(old["evaluation_code"]) if own.get(k) != old["evaluation_code"].get(k)
}
if code != old["code"] or changed != {"context.py", "report.py"}:
    raise RuntimeError("D02 storage repair changes a scientific or product module")
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
        "Lossless bounded score/aggregate/prediction storage with preservation of existing "
        "plain references, plus playable links for the predeclared failure example. "
        "All model, audio generation, scoring, metric, gate, matrix and population "
        "definitions unchanged."
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
