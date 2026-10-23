"""Prospective same-pool recovery for the two-example UI acceptance request."""

from pathlib import Path

from similar_sound_search.application import api, job
from similar_sound_search.application.context import Context
from similar_sound_search.resources import CatalogueBudget, load_limits

root = Path.cwd()
key = "589ac27a30d60007e1a7f8ad6fdd695499d23ca0f17b55e858b00d624be0fd6b"
owner = Context(root, "query-finalization-admission-1")
budget = CatalogueBudget(root, load_limits(root / "config/resource_limits.json", "starter"))
graph = job.units(owner, api.job(owner, key))
remaining = [u for u in graph if job.committed(owner, key, u) is None]
if remaining != ["media:2", "media:3", "media:4", "publish"]:
    raise RuntimeError("Expected only three remaining media chunks and final publication")
path = owner.directory / "recovery-admissions" / (key + ".json")
if path.exists():
    raise RuntimeError("Admission already exists; never add another pool/extension")
owner.admit(owner.allocation, 1048576, acceptance=True)
value = dict(
    schema_version="d01-finalization-admission-1",
    job_id=key,
    remaining=remaining,
    additional_ordinary_bytes=8388608,
    mode="committed-outputs",
    estimate=dict(
        array_score_audit=2097152,
        remaining_media=2097152,
        final_result_and_transitions=2097152,
        recovery_margin=2097152,
    ),
    aggregate=job.committed(owner, key, "aggregate-final"),
    prior_completed=94,
    prior_charges_retained=True,
    unchanged_ceilings=owner.pool()["ceilings"],
    reason="New per-example score payloads exceeded the initial request estimate. "
    "All numerical units are committed; validate outputs/query/arrays, then publish "
    "remaining native clips under the same fixed pool. No repeated catalogue-original scan.",
)
ref = owner.put(budget, "admission-plans", value)
owner.extend(budget, key, 8388608, ref)
owner.publish(budget, path, value, immutable=True)
owner.release(owner.allocation)
print(ref["record_hash"])
