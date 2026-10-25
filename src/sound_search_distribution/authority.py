"""External allocation registry fences copied/relocated workspaces and holds request bounds.

The registry is outside workspace backups. Its durable checkpoint is a lower bound
on each local share's cumulative counters. A request reserves its complete bounds
before ordinary admission; interrupted work keeps that reservation until reconciled.
Only explicit relocation changes the single canonical workspace binding.
"""

import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from similar_sound_search.application.locks import lock
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import InputError, ResourceError, digest

from .policy import MIB, SHARE


def anchor():
    """One host/user authorization, shared by installs and workspace backups."""
    return (
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share")))
        / "SimilarSoundSearch/D03"
    )


def initialize(root, registry_root=None):
    """Deliberate one-time initialization. Alternate roots are for isolated tests only."""
    from .context import empty_pool

    root = Path(root).resolve()
    registry_root = Path(registry_root or anchor()).resolve()
    registry_root.mkdir(parents=True, exist_ok=True)
    path = registry_root / "allocation.json"
    with lock(registry_root, "library"):
        if path.exists() or (root / "workspace.json").exists():
            raise InputError(
                "D03 authorization already initialized; reopen or relocate, never reset"
            )
        if any((root / ("data/runs/runtime-" + s)).exists() for s in ("normal", "verification")):
            raise InputError("D03 initialization refuses existing runtime state")
        wid, aid = str(uuid.uuid4()), str(uuid.uuid4())
        pools = {s: empty_pool(aid, s) for s in ("verification", "normal")}
        # Initialization/identity/registry publication is charged to verification.
        pools["verification"]["ordinary_used"] = 65536
        pools["verification"]["counts"]["metadata_bytes"] = 65536
        value = dict(
            schema_version="d03-allocation-1",
            allocation_id=aid,
            workspace_id=wid,
            canonical_workspace=os.path.normcase(str(root)),
            verification_closed=False,
            checkpoint={s: p["counts"] for s, p in pools.items()},
            generations={s: 0 for s in pools},
            active=None,
        )
        save(path, value)  # Fence the allowance before publishing any initialized pool.
        save(
            root / "workspace.json",
            dict(
                schema_version="d03-workspace-1",
                workspace_id=wid,
                allocation_id=aid,
                registry=str(path),
            ),
        )
        for s, p in pools.items():
            save(root / ("data/runs/runtime-" + s) / "pool.json", p)
    return binding(root)


def relocate(source, destination):
    """Move the same private workspace on this host; never copy or issue an allowance."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    path, _ = read(source)
    if destination.exists() or destination.is_relative_to(source):
        raise InputError("D03 relocation requires an absent destination outside the source")
    with lock(path.parent, "server"), lock(path.parent, "library"):
        _, a = read(source)
        if a["active"]:
            raise InputError("D03 finish/resume the admitted request before relocation")
        for s in ("verification", "normal"):
            verify_pool(source, s, record(source / ("data/runs/runtime-" + s) / "pool.json"))
        # Same-volume rename preserves bytes and identity. A crash between rename
        # and registry update is repaired by restoring the old path, then retrying.
        source.rename(destination)
        a["canonical_workspace"] = os.path.normcase(str(destination))
        save(path, a)
    return binding(destination)


def binding(root):
    p = Path(root) / "workspace.json"
    if not p.is_file():
        raise InputError(
            "D03 workspace is not initialized; use explicit prepare/init on an empty root"
        )
    value = record(p)
    if value.get("schema_version") != "d03-workspace-1":
        raise InputError("D03 workspace identity/schema differs; do not reset it")
    return value


def read(root):
    b = binding(root)
    p = Path(b["registry"])
    if not p.is_file():
        raise InputError(
            "D03 allocation registry missing; restore the external registry, never reinit"
        )
    value = record(p)
    if (
        value.get("schema_version") != "d03-allocation-1"
        or value["allocation_id"] != b["allocation_id"]
        or value["workspace_id"] != b["workspace_id"]
        or os.path.normcase(str(Path(root).resolve())) != value["canonical_workspace"]
    ):
        raise InputError("D03 copied/stale workspace binding; use explicit relocation/recovery")
    return p, value


def save(path, value):
    clean = {k: v for k, v in value.items() if k != "record_hash"}
    raw = (
        json.dumps({**clean, "record_hash": digest(clean)}, separators=(",", ":")).encode() + b"\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".d03-write-", dir=path.parent)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    # Windows readers can briefly deny replacement. Retry the SAME fully paid
    # temporary, with no additional data writes. Permanent failure stays loud and
    # retains the temporary; this is not a state/result fallback.
    for attempt in range(21):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 20:
                raise
            time.sleep(0.05)


def verify_pool(root, share, pool):
    _, a = read(root)
    if pool.get("allocation_id") != a["allocation_id"] or pool.get("share") != share:
        raise InputError("D03 pool ownership differs from the external allocation")
    if pool.get("generation", 0) < a["generations"][share]:
        raise InputError("D03 stale pool generation; restore the latest durable ledger")
    if any(pool["counts"][k] < n for k, n in a["checkpoint"][share].items()):
        raise InputError(
            "D03 stale backup ledger below durable checkpoint; explicit recovery required"
        )


def availability(root, share, pool, estimate):
    _, a = read(root)
    if share == "verification" and a["verification_closed"]:
        return False, "D03 verification share is sealed; completed results remain readable"
    if a["active"]:
        return False, "D03 has an admitted request; complete/resume it before another operation"
    if (
        shutil.disk_usage(root).free
        < 4 * 1024**3 + estimate["managed_output_bytes"] + SHARE["metadata_bytes"]
    ):
        return False, "D03 insufficient free disk for the complete request plus 4 GiB headroom"
    protected = estimate["metadata_bytes"] - estimate["ordinary_bytes"]
    if pool["protected_used"] + pool["protected_reserved"] + protected > 32 * MIB:
        return False, "D03 protected terminal capacity cannot fund the complete request"
    for k, amount in estimate.items():
        if k == "ordinary_bytes":
            continue
        if pool["counts"][k] + amount > SHARE[k]:
            return False, "D03 remaining " + k + " cannot admit the complete request"
    if (
        pool["ordinary_used"] + pool["ordinary_reserved"] + estimate["ordinary_bytes"]
        > 224 * 1024**2
    ):
        return False, "D03 remaining ordinary metadata cannot fund complete publication"
    if (
        pool["counts"]["managed_output_bytes"]
        + estimate["managed_output_bytes"]
        + SHARE["metadata_bytes"]
        > SHARE["managed_output_bytes"]
    ):
        return False, "D03 managed output cannot retain the full metadata envelope"
    return True, "D03 complete-path capacity available"


def reserve(owner, key, kind, estimate):
    path, _ = read(owner.root)
    with lock(path.parent, "library"):
        _, a = read(owner.root)
        active = a["active"]
        if active and active["job_id"] == key and active["share"] == owner.share:
            return
        pool = owner.pool()
        ok, reason = availability(owner.root, owner.share, pool, estimate)
        if not ok:
            raise ResourceError(reason)
        a["active"] = dict(
            job_id=key,
            share=owner.share,
            kind=kind,
            before=pool["counts"],
            ordinary_before=pool["ordinary_used"],
            estimate=estimate,
        )
        save(path, a)


def checkpoint(owner, key, finished=False):
    path, _ = read(owner.root)
    with lock(path.parent, "library"):
        _, a = read(owner.root)
        if not a["active"] or a["active"]["job_id"] != key:
            raise InputError("D03 checkpoint requires the exact active immutable request")
        a["checkpoint"][owner.share] = owner.pool()["counts"]
        if finished:
            a["active"] = None
        save(path, a)
