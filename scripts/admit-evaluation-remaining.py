"""Record measured cold/reuse pilot and admit the unchanged remaining finite matrix."""

from pathlib import Path

from similar_sound_search.application.job import committed
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation.context import Context

root = Path.cwd()
owner = Context(root)
pilots = []
for key, expected in (
    ("6ab43f6a7671c415cfd6bf4087b692d264e538189a35c7d956bd0fd74171c409", 32),
    ("2148e09a8452dc99345de0ba1a7bf9b9dde7be0aea2805667418f53305aa70b5", 0),
):
    state = record(owner.directory / "states" / (key + ".json"))
    evidence = state["worker_evidence"]
    count = sum(committed(owner, key, u)["new_encodes"] for u in ("0", "4"))
    if (
        state["state"] != "complete"
        or count != expected
        or evidence["peak_working_bytes"] >= 1024**3
    ):
        raise RuntimeError("D02 cold/reuse pilot did not satisfy exact finite admission")
    pilots.append(
        dict(job_id=key, new_encodes=count, peak_working_bytes=evidence["peak_working_bytes"])
    )
pool = owner.pool()
remaining_seconds_forecast = 2400
if pool["counts"]["job_seconds"] + remaining_seconds_forecast > pool["ceilings"]["job_seconds"]:
    raise RuntimeError("D02 complete remaining-path forecast cannot fit; no limit increase")
value = dict(
    schema_version="d02-remaining-admission-1",
    protocol=owner.protocol["record_hash"],
    pilots=pilots,
    spent_seconds=pool["counts"]["job_seconds"],
    remaining_seconds_forecast=remaining_seconds_forecast,
    forecast=(
        "Descriptive conservative admission estimate; actual 120s worker reservations "
        "and every pool guard remain authoritative. Reassess from measured work "
        "before confirmation; no cap increase."
    ),
    metadata_allocations={k: v["size"] for k, v in pool["allocations"].items()},
    maximum_candidate_memberships=904,
    query_examples_bound=48,
    total_new_windows_bound=952,
    numerical_concurrency=1,
    default="legacy-mean/original/pitch-off",
    quality_scores_inspected=False,
)
target = root / "manifests/assessment/resource-admission.json"
if target.exists():
    raise RuntimeError("D02 remaining-path admission already recorded; preserve it")
atomic_json(target, {**value, "record_hash": digest(value)})
print(digest(value))
