"""Pre-inference source declaration. Never edits or weakens a historical guard."""

import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
path = root / "manifests/application/consumer.json"
if path.exists():
    raise RuntimeError("D01 consumer already declared; preserve it and explicitly review drift")
old = record(root / "manifests/processing/consumer.json")
code = code_identity()
if any(code.get(k) != h for k, h in old["code"].items()):
    raise RuntimeError("D01 inherited source changed; no implicit numerical repair is permitted")
added = sorted(set(code) - set(old["code"]))
if any(not k.startswith("application/") for k in added):
    raise RuntimeError("D01 unclassified new subsystem")
value = dict(
    schema_version="d01-consumer-1",
    code=code,
    new_files=added,
    inherited_consumer=old["record_hash"],
    numerical_hash=old["numerical_hash"],
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    policy="Exact inherited files; new application adapters call unchanged primitives. "
    "Unknown Python drift blocks; renderer assets have separate identity.",
)
atomic_json(path, {**value, "record_hash": digest(value)})
print(digest(value))
