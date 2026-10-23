"""One prospective remaining-path correction within the original finite D01 pool."""

from pathlib import Path

from similar_sound_search.application import api, job
from similar_sound_search.application.context import Context
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.storage import digest

root = Path.cwd()
key = "1c0ef69a1a5156319dec8a976cab164de576d13ba9cc00f5c24b4355b361a678"
owner = Context(root, "finalization-admission-1")
budget = CatalogueBudget(root, load_limits(root / "config/resource_limits.json", "starter"))
graph = job.units(owner, api.job(owner, key))
remaining = [u for u in graph if job.committed(owner, key, u) is None]
if remaining != ["media:4", "publish"]:
    raise RuntimeError("Expected exactly the blocked final media and complete publication units")
owner.admit(owner.allocation, 1048576, acceptance=True)
path = owner.directory / "recovery-admissions" / (key + ".json")
if path.exists():
    raise RuntimeError("Recovery admission already exists; do not add another allowance")
correction = sum(
    (v["identity"]["last_frame"] - v["identity"]["first_frame"]) / v["identity"]["rate"]
    for v in [record(p) for p in (owner.audio / "media").glob("*.json")]
)
owner.charge(budget, read_audio_seconds=correction)
value = dict(
    schema_version="d01-finalization-admission-1",
    job_id=key,
    remaining=remaining,
    additional_ordinary_bytes=8388608,
    estimate=dict(
        fresh_byte_array_audit=2097152,
        remaining_media=1048576,
        final_result_and_transitions=2097152,
        recovery_margin=3145728,
    ),
    unchanged_ceilings=owner.pool()["ceilings"],
    aggregate=job.committed(owner, key, "aggregate-final"),
    chain=job.committed(owner, key, "chain"),
    prior_completed=97,
    prior_charges_retained=True,
    conservative_additional_clip_read_seconds=correction,
    reason="Retained consumer-repair revalidation consumed the initial per-request estimate. "
    "Reserve the bounded remaining path from the SAME D01 pool; no ceiling/refund/reset.",
)
ref = owner.put(budget, "admission-plans", value)
owner.extend(budget, key, 8388608, ref)
owner.publish(budget, path, value, immutable=True)
owner.release(owner.allocation)
print(digest(value))
