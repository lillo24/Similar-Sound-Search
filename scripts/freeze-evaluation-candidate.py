"""Commit the sole unchanged alternative and paired gate before confirmation inference."""

import subprocess
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation import contracts
from sound_search_evaluation.context import Context

root = Path.cwd()
owner = Context(root)
path = root / "manifests/assessment/candidate.json"
if path.exists():
    raise RuntimeError("D02 candidate already frozen; do not revise after confirmation")
if any(
    (owner.directory / "index" / (s["source_id"] + ".json")).exists()
    for s in owner.protocol["splits"]["confirmation"]["sources"]
):
    raise RuntimeError("D02 confirmation encoding preceded candidate freeze")
if any(
    record(p)["split"] == "confirmation"
    for p in (owner.directory / "execution-claims").glob("*.json")
):
    raise RuntimeError("D02 confirmation inference already claimed")
assessment = owner.get(
    record(owner.directory / "scores/development-summary.json")["assessment"], "assessments"
)
if assessment["state"] != "complete" or assessment["declared_queries"] != 24:
    raise RuntimeError("D02 development matrix is incomplete; freeze cannot discard cases")
value = dict(
    schema_version="d02-candidate-1",
    protocol=owner.protocol["record_hash"],
    baseline="legacy-mean",
    candidate="event-multi",
    revision=None,
    consumer=contracts.consumer(owner),
    development_assessment=assessment["record_hash"],
    development_gate=assessment["gate"],
    gate=owner.protocol["decision"],
    confirmation_cases=16,
    confirmation_matrix=digest(owner.protocol["splits"]["confirmation"]),
    decision=(
        "Unchanged sole prospective alternative; no tuning. Development coverage guard "
        "failed; retain baseline. Run the declared confirmation once for complete paired "
        "evidence."
    ),
    defaults=owner.protocol["default"],
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
)
atomic_json(path, {**value, "record_hash": digest(value)})
print(digest(value))
