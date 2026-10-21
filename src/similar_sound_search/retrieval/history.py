"""Read-only C01 membership paths, with a separate freshly audited legacy binding."""

from ..evaluation.artifacts import record
from ..indexing import reader
from ..indexing.context import Context as IndexContext
from ..storage import InputError, contained, digest


class BankView(IndexContext):
    def __init__(self, owner):
        super().__init__(owner.root)
        self.owner = owner

    def charge(self, budget, **amounts):
        return self.owner.charge(budget, **amounts)

    def publish(self, *args, **kwargs):
        raise InputError("C02 historical bank view is read-only")


def open_snapshot(budget, owner, receipt_path):
    view = BankView(owner)
    key = owner.protocol["snapshot"]
    snapshot = record(view.indexes / "snapshots" / (key + ".json"))
    if snapshot["record_hash"] != key or snapshot["schema_version"] != "c01-index-snapshot-1":
        raise InputError("C02 historical snapshot identity/schema differs")
    values = []
    for expected in owner.protocol["primary_banks"]:
        matches = [v for v in snapshot["banks"] if v["record_hash"] == expected]
        if len(matches) != 1:
            raise InputError("C02 required bank is missing/duplicated in snapshot")
        ref = matches[0]
        path = contained(owner.root / ref["path"], view.indexes)
        if expected == owner.protocol["primary_banks"][0]:
            old = record(path)
            if old["record_hash"] != expected:
                raise InputError("C02 historical legacy bank record hash differs")
            fresh = reader.legacy(budget, owner, receipt_path)
            ignore = {"record_hash", "receipt", "receipt_hash"}
            if {k: v for k, v in old.items() if k not in ignore} != {
                k: v for k, v in fresh.items() if k not in ignore
            }:
                raise InputError("C02 fresh legacy view differs from historical row membership")
            expanded = []
            for unit in fresh["committed"]:
                meta = record(owner.root / unit["path"] / "record.json")
                if (
                    meta["record_hash"] != unit["array_record_hash"]
                    or meta["shape"][0] != unit["rows"]
                ):
                    raise InputError("C02 legacy shard membership changed")
                expanded.append({**unit, "identity": meta["identity"], "array": meta})
            value = {**fresh, "committed": expanded}
            binding = {
                "historical_bank_hash": old["record_hash"],
                "fresh_receipt_hash": fresh["receipt_hash"],
                "identical_membership": True,
                "new_features": 0,
                "copied_features": 0,
            }
        else:
            value = reader.read_bank(budget, view, path)
            if value["record_hash"] != expected:
                raise InputError("C02 historical bank record hash differs")
            binding = {"historical_bank_hash": value["record_hash"]}
        if value["coverage"]["state"] != "complete" or value["scope"] != "discovery":
            raise InputError("C02 primary fusion requires complete discovery banks")
        if value["bank"]["bank_id"] != ref["bank_id"]:
            raise InputError("C02 bank reference identity differs")
        values.append({"value": value, "binding": binding, "path": ref["path"]})
    memberships = [
        digest({k: v["original"] for k, v in b["value"]["signals"].items()}) for b in values
    ]
    if len(set(memberships)) != 1 or any(
        b["value"]["bank"]["identity"]["representation"]
        != values[0]["value"]["bank"]["identity"]["representation"]
        for b in values
    ):
        raise InputError("C02 primary bank source/representation populations differ")
    return snapshot, view, values
