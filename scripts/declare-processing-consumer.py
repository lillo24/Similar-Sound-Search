"""Explicit pre-inference declaration; refuses to overwrite an earlier consumer."""

import hashlib
import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.processing.contracts import INHERITED_NUMERICAL
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
path = root / "manifests/processing/consumer.json"
if path.exists():
    raise RuntimeError("C04 consumer already declared; preserve it and review drift explicitly")
code = code_identity()
before = record(root / "manifests/refinement/report-repair.json")["consumer_code"]
base = "9140a76cc46efd75c4daebd0525923f3e8128d5c"
for key in INHERITED_NUMERICAL:
    source = subprocess.check_output(["git", "show", base + ":src/similar_sound_search/" + key])
    sha = hashlib.sha256(source.replace(b"\r\n", b"\n")).hexdigest()
    if code[key] != before[key] or sha != before[key]:
        raise RuntimeError("C04 unchanged numerical primitive proof failed: " + key)
owned_numeric = {
    "processing/contracts.py",
    "processing/cache.py",
    "processing/engine.py",
    "processing/historical.py",
}
coordinators = {
    "cli.py",
    "resources.py",
    "storage.py",
    "processing/__init__.py",
    "processing/context.py",
    "processing/api.py",
    "processing/job.py",
    "processing/commands.py",
    "processing/validation.py",
}
new = set(code) - set(before)
if new != owned_numeric | {k for k in coordinators if k.startswith("processing/")}:
    raise RuntimeError("C04 new source classification incomplete")
changed = {k for k in before if before[k] != code[k]}
if changed != {"cli.py", "resources.py", "storage.py"}:
    raise RuntimeError("C04 inherited source drift outside declared coordinator changes")
classification = {
    k: "numerical"
    if k in set(INHERITED_NUMERICAL) | owned_numeric
    else "coordinator"
    if k in coordinators
    else "historical"
    for k in code
}
value = dict(
    schema_version="c04-consumer-1",
    baseline_commit=base,
    code=code,
    classification=classification,
    inherited_numerical={k: before[k] for k in INHERITED_NUMERICAL},
    numerical_hash=digest({k: v for k, v in code.items() if classification[k] == "numerical"}),
    policy="Exact source map; unknown drift blocks. Historical full-package guards unchanged.",
)
atomic_json(path, {**value, "record_hash": digest(value)})
print(digest(value))
