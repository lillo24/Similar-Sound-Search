"""D03 share-local accounting reuses the protected application transaction machinery."""

import math
from pathlib import Path

from similar_sound_search.application.context import Context as BaseContext
from similar_sound_search.application.context import payload
from similar_sound_search.application.locks import lock
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import InputError, ResourceError, atomic_json, digest, read_json

from . import authority
from .policy import PROTECTED, SHARE


def empty_pool(allocation_id, share):
    return dict(
        schema_version="d03-pool-1",
        allocation_id=allocation_id,
        share=share,
        generation=0,
        counts={k: 0 for k in SHARE},
        ceilings=SHARE,
        ordinary_used=0,
        ordinary_reserved=0,
        protected_used=0,
        protected_reserved=0,
        allocations={},
        attempts={},
        acceptance_held=0,
        measured_worker_seconds=0,
        uncertain_worker_seconds=0,
        last_settled=0,
        attempt_sequence=0,
    )


class Context(BaseContext):
    def __init__(self, root, allocation=None, share="normal"):
        self.root = Path(root).resolve()
        if share not in {"verification", "normal"}:
            raise InputError("D03 explicit verification/normal share required")
        self.share, self.allocation, self.job_id = share, allocation, allocation
        self.binding = authority.binding(self.root)
        authority.read(self.root)
        self.directory = self.root / ("data/runs/runtime-" + share)
        self.features = self.root / ("data/features/runtime-" + share)
        self.audio = self.root / ("data/audio/runtime-" + share)
        self.reports = self.root / "reports/local/runtime"
        self.library_root = self.root / "data/runs/runtime-library"
        self.query_features_root = self.root / "data/features/runtime-queries"
        self.protocol = read_json(self.root / "manifests/application/protocol.json")
        self.cfg = dict(
            schema_version="d03-runtime-1",
            host="127.0.0.1",
            port=8776,
            protected_metadata_bytes=PROTECTED,
            attempt_bookkeeping_bytes=262144,
            acceptance_ordinary_bytes=0,
            policy={"max_" + k: v for k, v in SHARE.items()},
        )
        self.operation = "upload" if allocation and allocation.startswith("upload-") else None

    def pool(self):
        path = self.directory / "pool.json"
        if not path.is_file():
            raise InputError(
                "D03 initialized pool missing; restore/reconcile it, never reset usage"
            )
        p = record(path)
        if (
            p.get("schema_version") != "d03-pool-1"
            or p["ceilings"] != SHARE
            or set(p["counts"]) != set(SHARE)
        ):
            raise InputError("D03 pool schema or fixed partition changed")
        for k, cap in SHARE.items():
            n = p["counts"][k]
            if (
                isinstance(n, bool)
                or not isinstance(n, (int, float))
                or not math.isfinite(n)
                or not 0 <= n <= cap
            ):
                raise InputError("D03 corrupt/exhausted counter: " + k)
        authority.verify_pool(self.root, self.share, p)
        return {k: v for k, v in p.items() if k != "record_hash"}

    def publish(self, budget, path, value, immutable=False):
        if not path.resolve().is_relative_to(self.library_root):
            return super().publish(budget, path, value, immutable)
        from similar_sound_search.storage import contained

        path = contained(path, self.library_root)
        saved, cost = payload(value)
        if immutable and path.exists():
            if record(path) != saved:
                raise InputError("D03 common immutable query record conflicts")
            return saved
        self.charge(budget, metadata_bytes=cost)
        budget.reserve(cost)
        budget.track_file(path)
        atomic_json(path, saved)
        budget.account_file(path, path.stat().st_size)
        return saved

    def _save(self, p):
        _, a = authority.read(self.root)
        active = a["active"]
        if active and active["share"] == self.share:
            for k, cap in active["estimate"].items():
                if k == "ordinary_bytes":
                    used = p["ordinary_used"] - active["ordinary_before"]
                else:
                    used = p["counts"][k] - active["before"][k]
                if used > cap:
                    raise ResourceError("D03 complete-request " + k + " bound exhausted")
        elif any(p["counts"][k] != a["checkpoint"][self.share][k] for k in SHARE):
            raise InputError("D03 write without an externally reserved request")
        p["generation"] = p.get("generation", 0) + 1
        # Every durable write advances the external lower bound. The existing
        # prepaid pool-write slot covers the compact pool and external checkpoint;
        # refuse if their combined replacement/temporary geometry no longer fits.
        import json

        from similar_sound_search.application.context import POOL_WRITE

        a["checkpoint"][self.share] = p["counts"]
        a["generations"][self.share] = p["generation"]
        size = (
            len(json.dumps(p, separators=(",", ":")))
            + len(json.dumps(a, separators=(",", ":")))
            + 150
        )
        if size * 2 + 8192 > POOL_WRITE:
            raise ResourceError("D03 pool/registry serialized geometry exceeds prepaid slot")
        super()._save(p)
        authority.save(Path(self.binding["registry"]), a)

    def admit(self, key, ordinary, acceptance=False, jobs=0):
        from .policy import estimate

        receipt = self.directory / "closed-allocations" / (key + ".json")
        if receipt.exists():
            raise InputError("D03 completed allocation is closed; retry its immutable request")
        bounds = estimate(self.operation or "control", getattr(self, "examples", 2))
        bounds["ordinary_bytes"] = ordinary
        authority.reserve(self, key, self.operation or "control", bounds)
        super().admit(key, ordinary, acceptance=False, jobs=jobs)

    def release(self, key):
        p = self.pool()
        if key not in p["allocations"]:
            if (self.directory / "closed-allocations" / (key + ".json")).exists():
                return
            raise InputError("D03 cannot close an unknown allocation")
        saved = p["allocations"][key]
        slot = "close-" + key
        self.reserve_attempt(slot, seconds=0)
        self.terminal(
            slot,
            self.directory / "closed-allocations" / (key + ".json"),
            dict(
                schema_version="d03-closed-allocation-1",
                allocation=key,
                original=saved,
                spent_bytes=saved["size"] - saved["remaining"],
            ),
            elapsed=0,
        )
        super().release(key)
        # Completed entries move to immutable receipts to keep the same bounded
        # pool-write geometry. Cumulative counts and all attempt journals remain.
        with lock(self.root, "pool"):
            p = self.pool()
            del p["allocations"][key]
            self._book_pool(p)
            self._save(p)
        authority.checkpoint(self, key, finished=True)

    def query_ancestry(self, item):
        """Add every actual real-catalogue parent; character labels never exclude."""
        asset = record(self.library_root / "assets" / (item["asset_id"] + ".json"))
        audio = asset["identity"]["audio"]
        from similar_sound_search.application import history

        groups = {digest(["d03-reference-1", audio["canonical_pcm"]["sha256"]])}
        for source in history.inputs(self)[1]["input"]["sources"]:
            if (
                source["source"]["sha256"] == audio["sha256"]
                or source["source"]["canonical_pcm"]["sha256"] == audio["canonical_pcm"]["sha256"]
            ):
                groups.add(source["group"])
        return groups
