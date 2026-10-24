"""Measured remaining-path reservation within the original D02 metadata ceiling."""

from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import load_limits
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation.budget import CatalogueBudget
from sound_search_evaluation.context import MIB, Context

root = Path.cwd()
owner = Context(root, "development")
pool = owner.pool()
if (
    pool["ceilings"]["metadata_bytes"] != 256 * MIB
    or owner.cfg["protected_metadata_bytes"] != 32 * MIB
):
    raise RuntimeError("D02 metadata admission must retain original fixed/protected ceilings")
measured = record(
    owner.directory / "states/1c599801e9eea5a6bb12a3e00b6d636cd3c0f538df61f6e15a93fed1c327e6b3.json"
)
if measured["state"] != "complete":
    raise RuntimeError("D02 four-case storage measurement is incomplete")
amount = 18 * MIB
value = dict(
    schema_version="d02-metadata-admission-1",
    protocol=owner.protocol["record_hash"],
    measured_batch=measured["job_id"],
    additional_development_bytes=amount,
    reason=(
        "Measured cold cases plus lossless compaction; 2 MiB publication margin "
        "over the initial 16 MiB forecast"
    ),
    fixed_metadata_ceiling=pool["ceilings"]["metadata_bytes"],
    protected_bytes=32 * MIB,
    confirmation_reserved=pool["allocations"]["confirmation"]["remaining"],
    report_reserved=pool["allocations"]["report"]["remaining"],
    no_spent_charge_refunded=True,
)
path = root / "manifests/assessment/metadata-admission.json"
if path.exists():
    if record(path) != {**value, "record_hash": digest(value)}:
        raise RuntimeError("D02 metadata admission differs; preserve old receipts")
else:
    atomic_json(path, {**value, "record_hash": digest(value)})
owner.extend(
    CatalogueBudget(root, load_limits(root / "config/resource_limits.json", "starter")),
    "development",
    amount,
    digest(value),
)
print(digest(value))
