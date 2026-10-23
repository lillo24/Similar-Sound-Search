"""One finite D01 pool with prepaid ordinary allocations and protected attempt slots.

Admission counts the entire path, not the next unit. Debits precede writes and
are never refunded for failed publication. Reserved attempt slots are separate
from ordinary allocations; terminal writes do not call ordinary publication.
"""

import json
import math
from pathlib import Path

from ..evaluation.artifacts import record
from ..storage import InputError, ResourceError, atomic_json, contained, digest, read_json
from .locks import lock

MIB = 1024**2
CEILINGS = dict(
    job_seconds=3600,
    workers=256,
    read_audio_seconds=90000,
    feature_windows=1024,
    processed_window_seconds=6000,
    feature_bytes=32 * MIB,
    query_jobs=64,
    clips=64,
    clip_bytes=128 * MIB,
    metadata_bytes=128 * MIB,
    preparation_bytes=64 * MIB,
    import_bytes=128 * MIB,
    managed_output_bytes=512 * MIB,
)
POOL_WRITE = 16384


class PersistenceError(InputError):
    """Observed failure could not be made durable; last persisted state is separate."""


def payload(value):
    value = {k: v for k, v in value.items() if k != "record_hash"}
    saved = {**value, "record_hash": digest(value)}
    raw = (json.dumps(saved, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(raw) > MIB:
        raise InputError("D01 record exceeds 1 MiB; split into immutable references")
    # Serialized destination + concurrent atomic temporary + directory overhead.
    return saved, len(raw) * 2 + 4096


class Context:
    def __init__(self, root, allocation=None):
        self.root = Path(root).resolve()
        self.cfg = read_json(self.root / "config/application.json")
        if self.cfg.get("schema_version") != "d01-application-1" or set(
            self.cfg.get("policy", {})
        ) != {"max_" + k for k in CEILINGS}:
            raise InputError("D01 complete fixed policy required")
        for key, ceiling in CEILINGS.items():
            n = self.cfg["policy"]["max_" + key]
            if isinstance(n, bool) or not isinstance(n, int) or not 0 < n <= ceiling:
                raise InputError("D01 invalid/increased ceiling: " + key)
        if (
            self.cfg["protected_metadata_bytes"] < 32 * MIB
            or self.cfg["attempt_bookkeeping_bytes"] != 65536
            or self.cfg["host"] != "127.0.0.1"
        ):
            raise InputError("D01 protected reserve/loopback policy changed")
        self.protocol = read_json(self.root / "manifests/application/protocol.json")
        self.directory = self.root / "data/runs/application"
        self.features = self.root / "data/features/application"
        self.audio = self.root / "data/audio/application"
        self.reports = self.root / "reports/local/d01"
        self.allocation = allocation

    def pool(self):
        path = self.directory / "pool.json"
        if not path.exists():
            return dict(
                schema_version="d01-pool-1",
                counts={k: 0 for k in CEILINGS},
                ceilings={k: self.cfg["policy"]["max_" + k] for k in CEILINGS},
                ordinary_used=0,
                ordinary_reserved=0,
                protected_used=0,
                protected_reserved=0,
                allocations={},
                attempts={},
                acceptance_held=self.cfg["acceptance_ordinary_bytes"],
                measured_worker_seconds=0,
                uncertain_worker_seconds=0,
                last_settled=0,
                attempt_sequence=0,
            )
        value = record(path)
        if value["schema_version"] != "d01-pool-1" or set(value["counts"]) != set(CEILINGS):
            raise InputError("D01 corrupt pool; never replace/reset it")
        for key in CEILINGS:
            if value["ceilings"][key] > self.cfg["policy"]["max_" + key]:
                raise InputError("D01 persisted ceiling exceeds current policy")
        return {k: v for k, v in value.items() if k != "record_hash"}

    def _save(self, p):
        saved, _ = payload(p)
        raw = json.dumps(saved, separators=(",", ":"), allow_nan=False).encode() + b"\n"
        cost = len(raw) * 2 + 4096
        if cost > POOL_WRITE:
            raise ResourceError("D01 bounded pool geometry exceeded; no further admission")
        from .files import atomic_bytes

        atomic_bytes(self.directory / "pool.json", raw)

    def _book_pool(self, p):
        p["ordinary_used"] += POOL_WRITE
        p["counts"]["metadata_bytes"] += POOL_WRITE

    def admit(self, key, ordinary, acceptance=False, jobs=0):
        """Prepay an entire request including final groups/media/terminal publication."""
        with lock(self.root, "pool"):
            p = self.pool()
            if key in p["allocations"]:
                if p["allocations"][key]["size"] != ordinary:
                    raise InputError("D01 admission identity/estimate changed")
                return
            cap = p["ceilings"]["metadata_bytes"] - self.cfg["protected_metadata_bytes"]
            held = 0 if acceptance else p["acceptance_held"]
            if p["ordinary_used"] + p["ordinary_reserved"] + ordinary + POOL_WRITE + held > cap:
                raise ResourceError(
                    "D01 blocked admission: complete path cannot fit ordinary metadata"
                )
            if p["counts"]["query_jobs"] + jobs > p["ceilings"]["query_jobs"]:
                raise ResourceError("D01 processing/query job ceiling exhausted")
            p["allocations"][key] = dict(size=ordinary, remaining=ordinary, acceptance=acceptance)
            p["ordinary_reserved"] += ordinary
            if acceptance:
                p["acceptance_held"] = max(0, p["acceptance_held"] - ordinary)
            p["counts"]["query_jobs"] += jobs
            self._book_pool(p)
            self._save(p)

    def release(self, key):
        with lock(self.root, "pool"):
            p = self.pool()
            a = p["allocations"][key]
            if a.get("closed"):
                return
            # Unspent reservations only. Actual charged writes are never refunded.
            p["ordinary_reserved"] -= a["remaining"]
            if a["acceptance"]:
                p["acceptance_held"] += a["remaining"]
            a.update(remaining=0, closed=True)
            self._book_pool(p)
            self._save(p)

    def charge(self, budget, **amounts):
        amounts["preparation_bytes"] = amounts.get("preparation_bytes", 0) + amounts.pop(
            "query_preparation_bytes", 0
        )
        amounts["processed_window_seconds"] = amounts.get(
            "processed_window_seconds", 0
        ) + amounts.pop("pitch_audio_seconds", 0)
        amounts["managed_output_bytes"] = amounts.get("managed_output_bytes", 0) + sum(
            amounts.get(k, 0)
            for k in ("feature_bytes", "preparation_bytes", "clip_bytes", "import_bytes")
        )
        if set(amounts) - set(CEILINGS) or any(
            isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0
            for n in amounts.values()
        ):
            raise InputError("D01 invalid accounting debit")
        with lock(self.root, "pool"):
            p = self.pool()
            n = amounts.pop("metadata_bytes", 0) + POOL_WRITE
            a = p["allocations"].get(self.allocation)
            if a is None or a["remaining"] < n:
                raise ResourceError(
                    "D01 ordinary allocation exhausted; reserved bookkeeping intact"
                )
            for key, value in amounts.items():
                if p["counts"][key] + value > p["ceilings"][key]:
                    raise ResourceError("D01 cumulative " + key + " exhausted")
            a["remaining"] -= n
            p["ordinary_reserved"] -= n
            p["ordinary_used"] += n
            p["counts"]["metadata_bytes"] += n
            for key, value in amounts.items():
                p["counts"][key] += value
            # Metadata ceiling is reserved once in managed capacity, including protected writes.
            if (
                p["counts"]["managed_output_bytes"] + p["ceilings"]["metadata_bytes"]
                > p["ceilings"]["managed_output_bytes"]
            ):
                raise ResourceError("D01 managed output exhausted including metadata envelope")
            self._save(p)
        return p

    def publish(self, budget, path, value, immutable=False):
        path = contained(path, self.directory)
        saved, cost = payload(value)
        if immutable and path.exists():
            if record(path) != saved:
                raise InputError("D01 immutable conflict: " + path.name)
            return saved
        self.charge(budget, metadata_bytes=cost)
        budget.reserve(cost)
        atomic_json(path, saved)
        budget.refresh_disk()
        return saved

    def put(self, budget, kind, value):
        from .codec import encode

        value = encode(kind, value)
        saved, _ = payload(value)
        path = self.directory / kind / (saved["record_hash"] + ".json")
        self.publish(budget, path, value, immutable=True)
        return dict(path=path.relative_to(self.root).as_posix(), record_hash=saved["record_hash"])

    def get(self, ref, kind):
        path = contained(self.root / ref["path"], self.directory / kind)
        value = record(path)
        if path.stem != ref["record_hash"] or value["record_hash"] != ref["record_hash"]:
            raise InputError("D01 immutable reference differs")
        from .codec import decode

        return decode(value)

    def reserve_attempt(self, identity, seconds=120):
        """One slot per actual attempt; retries use a new identity and retained charges."""
        with lock(self.root, "pool"):
            p = self.pool()
            journal = self.directory / "settlements" / (identity + ".json")
            if journal.exists():
                return dict(settled=True, remaining=0, seconds=seconds)
            if identity in p["attempts"]:
                return p["attempts"][identity]
            if seconds and any(not a["settled"] for a in p["attempts"].values()):
                raise ResourceError("D01 previous attempt requires explicit reconciliation")
            size = self.cfg["attempt_bookkeeping_bytes"]
            if (
                p["protected_used"] + p["protected_reserved"] + size
                > self.cfg["protected_metadata_bytes"]
            ):
                raise ResourceError("D01 protected bookkeeping admission exhausted")
            if (seconds and p["counts"]["workers"] >= p["ceilings"]["workers"]) or p["counts"][
                "job_seconds"
            ] + seconds > p["ceilings"]["job_seconds"]:
                raise ResourceError("D01 worker admission exhausted")
            p["attempt_sequence"] += 1
            slot = dict(
                remaining=size - POOL_WRITE,
                seconds=seconds,
                settled=False,
                sequence=p["attempt_sequence"],
                job_id=self.allocation,
            )
            p["attempts"] = {k: v for k, v in p["attempts"].items() if not v["settled"]}
            p["attempts"][identity] = slot
            p["protected_reserved"] += size - POOL_WRITE
            p["protected_used"] += POOL_WRITE
            p["counts"]["metadata_bytes"] += POOL_WRITE
            p["counts"]["workers"] += int(bool(seconds))
            p["counts"]["job_seconds"] += seconds
            self._save(p)
            return slot

    def terminal(self, identity, path, value, elapsed=None, uncertain=False):
        """Protected write-ahead terminal + idempotent settlement, no ordinary publication.

        A crash after the journal is durable but before pool update replays the
        exact pool_after. A write failure is explicit and never recurses here.
        """
        path = contained(path, self.directory)
        journal = self.directory / "settlements" / (identity + ".json")
        with lock(self.root, "pool"):
            p = self.pool()
            if journal.exists():
                saved = record(journal)
                if saved["attempt"] != identity:
                    raise InputError("D01 settlement identity changed")
                if saved["pool_after"]["last_settled"] > p["last_settled"]:
                    self._save(saved["pool_after"])
                if not path.exists() or record(path) != saved["terminal"]:
                    atomic_json(path, saved["terminal"])
                return
            slot = p["attempts"][identity]
            if slot["settled"]:
                return
            terminal, cost = payload(value)
            # Journal embeds a bounded pool snapshot + terminal. Allow both atomic temporaries,
            # final state and the pool replacement. 64KiB admission is checked before writing.
            used = cost + POOL_WRITE * 2
            if used > slot["remaining"]:
                raise PersistenceError("D01 terminal geometry exceeds its pre-reserved slot")
            p["protected_reserved"] -= slot["remaining"]
            p["protected_used"] += used
            p["counts"]["metadata_bytes"] += used
            if uncertain:
                p["uncertain_worker_seconds"] += slot["seconds"]
            elif elapsed is not None:
                elapsed = min(slot["seconds"], elapsed)
                p["counts"]["job_seconds"] += elapsed - slot["seconds"]
                p["measured_worker_seconds"] += elapsed
            slot.update(settled=True, remaining=0)
            p["last_settled"] = max(p["last_settled"], slot["sequence"])
            saved, journal_cost = payload(dict(attempt=identity, terminal=terminal, pool_after=p))
            if journal_cost + cost + POOL_WRITE > used:
                raise PersistenceError("D01 settlement exceeds reserved serialized bound")
            try:
                atomic_json(journal, saved)
                self._save(p)
                atomic_json(path, terminal)
            except OSError as exc:
                raise PersistenceError(
                    "D01 persistence failed; inspect last durable attempt/settlement; "
                    "observed process outcome is separate: " + str(exc)
                ) from exc
