"""Prospective exact D02 adapter proof; never changes any historical consumer map."""

import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation.contracts import D01_CONSUMER, own_code

root = Path.cwd()
target = root / "manifests/assessment/consumer.json"
if target.exists():
    raise RuntimeError("D02 consumer exists; preserve it and explicitly archive/review any repair")
old = record(root / "manifests/application/consumer.json")
if old["record_hash"] != D01_CONSUMER:
    raise RuntimeError("Unexpected D01 predecessor; no implicit adoption")
code = code_identity()
changed = sorted(k for k, h in old["code"].items() if code.get(k) != h)
allowed = {
    "application/api.py",
    "application/server.py",
    "application/queries.py",
    "application/history.py",
    "application/context.py",
}
if set(changed) != allowed or set(code) != set(old["code"]):
    raise RuntimeError("D02 exact provider seam differs; inherited numerical files may not change")
previous = dict(
    declaration_hash=old["record_hash"],
    numerical_hash=old["numerical_hash"],
    code_hash=digest(old["code"]),
    version="d01-consumer-1",
)
proof = dict(
    schema_version="d02-scoped-compatibility-1",
    before_consumer=old["record_hash"],
    before_code=old["code"],
    after_code=code,
    changed_files=changed,
    accepted_previous=[previous],
    reason=(
        "Trusted provider injection, separate D02 owner, actual job settlemen"
        "t IDs and query ancestry/model sharing; original D01 defaults and al"
        "l numerical code unchanged"
    ),
)
atomic_json(
    root / "manifests/assessment/compatibility.json", {**proof, "record_hash": digest(proof)}
)
value = dict(
    schema_version="d02-consumer-1",
    code=code,
    evaluation_code=own_code(),
    compatibility=digest(proof),
    numerical_hash=old["numerical_hash"],
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
)
atomic_json(target, {**value, "record_hash": digest(value)})
pilot = dict(
    schema_version="d02-resource-pilot-1",
    protocol=record(root / "manifests/assessment/protocol.json")["record_hash"],
    split="development",
    ordinals=[0, 4],
    passes=["cold", "exact-reuse"],
    policy=(
        "Index only; no query distances or quality scores. Measure actual PID"
        " startup/decode/model/cache/write/settlement before remaining index."
        " Stop if projected complete path violates preflight; no pool increas"
        "es."
    ),
)
atomic_json(root / "manifests/assessment/pilot.json", {**pilot, "record_hash": digest(pilot)})
print(digest(value))
