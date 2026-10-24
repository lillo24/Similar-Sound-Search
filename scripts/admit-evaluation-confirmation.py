"""Reserve the measured confirmation remainder without increasing any D02 ceiling."""

from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import load_limits
from similar_sound_search.storage import atomic_json, digest
from sound_search_evaluation.budget import CatalogueBudget
from sound_search_evaluation.context import MIB, Context

root = Path.cwd()
owner = Context(root, "confirmation", "confirmation")
path = root / "manifests/assessment/confirmation-admission.json"
if path.exists():
    raise RuntimeError("D02 confirmation admission already exists; preserve its reservation")
pool = owner.pool()
if (
    pool["ceilings"]["metadata_bytes"] != 256 * MIB
    or owner.cfg["protected_metadata_bytes"] != 32 * MIB
    or any(not a["settled"] for a in pool["attempts"].values())
):
    raise RuntimeError("D02 requires the unchanged ceiling and an idle settled owner")
for split in ("development", "confirmation"):
    if not record(owner.directory / "byte-audits" / (split + ".json"))["passed"]:
        raise RuntimeError("D02 cannot close preparation before both byte audits")
for key in (
    "03890eaf4b78c091dc00d6b6e2b3099a23fcc9ab20a98547a1b01a9f00ead84f",
    "0e62b262ff85f6fdf9bbdcd2666972c5be520958e23b1c9b67bb1d05c47abb99",
    "dc47ca15e8d7101d3d248e87fc5846dbe7604b04663dfc26b47b3d3bf63eddc8",
):
    if record(owner.directory / "states" / (key + ".json"))["state"] != "complete":
        raise RuntimeError("D02 confirmation audit/index/query path is incomplete")
if any(
    record(p)["split"] == "confirmation"
    for p in (owner.directory / "execution-claims").glob("*.json")
):
    raise RuntimeError("D02 reserve confirmation predictions before inspecting them")
amount = 20 * MIB
if pool["allocations"]["confirmation"]["remaining"] + amount < 48 * MIB:
    raise RuntimeError("D02 measured remaining confirmation margin is insufficient")
value = dict(
    schema_version="d02-confirmation-admission-1",
    protocol=owner.protocol["record_hash"],
    candidate=record(root / "manifests/assessment/candidate.json")["record_hash"],
    confirmation_before=pool["allocations"]["confirmation"]["remaining"],
    additional_confirmation_bytes=amount,
    remaining_case_bound=16,
    forecast_bytes_per_case=3 * MIB,
    reason="Measured development cold metadata, with confirmation index/queries now complete",
    unspent_prepare_released=pool["allocations"]["prepare"]["remaining"],
    report_reserved=pool["allocations"]["report"]["remaining"],
    delivery_reserved=pool["allocations"]["delivery"]["remaining"],
    fixed_metadata_ceiling=256 * MIB,
    protected_metadata_bytes=32 * MIB,
    no_spent_charge_refunded=True,
)
atomic_json(path, {**value, "record_hash": digest(value)})
# Generation, both independent audits and byte closure are complete. Release only
# the unused reservation; every actual preparation write/read remains charged.
owner.release("prepare")
owner.extend(
    CatalogueBudget(root, load_limits(root / "config/resource_limits.json", "starter")),
    "confirmation",
    amount,
    digest(value),
)
print(digest(value))
