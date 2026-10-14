"""Search policy, frozen representation bindings, integer grids and array integrity."""

import hashlib
import os
import tempfile
from pathlib import Path

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..evaluation.protocol import comparison_pair
from ..matchers.acoustic import checked
from ..matchers.models import checkpoint_path, descriptor
from ..storage import InputError, contained, digest, is_link, read_json, sha256

CHOICE = "95dce46b16760b002358b1aec3db8adb9b5df1c1f2033ee70b0b5121c2dea051"
PROTOCOL = "07af66b37db00d6a6dd4bea87c9636b06aa9dbd43c75e8164be4568bd94b0048"
SUITE = "d4c59416e5d4bb4aeddfbefa933a3a0f18691a25957e3623f1743d2951806441"
CONFIG = "5a487b946d748d48ec2945dae97e51f07bd0e8b106fa6c49c98df9e84a4035e9"


def configuration(root):
    cfg = read_json(root / "config/search.json")
    if cfg.get("schema_version") != "a06-search-1":
        raise InputError("search configuration: expected a06-search-1")
    integer_fields = (
        "window_milliseconds",
        "hop_milliseconds",
        "windows_per_shard",
        "rank_block_windows",
        "max_query_examples",
        "max_query_seconds",
        "results",
        "playback_context_milliseconds",
    )
    for key in integer_fields:
        v = cfg.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or not 0 < v <= 30000:
            raise InputError("search configuration: invalid " + key)
    if (
        cfg["hop_milliseconds"] > cfg["window_milliseconds"]
        or cfg["windows_per_shard"] > 512
        or cfg["rank_block_windows"] > 512
        or cfg["max_query_examples"] > 8
        or cfg["max_query_seconds"] > 30
        or cfg["results"] > 10
    ):
        raise InputError("search configuration: conservative geometry/query bounds exceeded")
    if (
        cfg.get("pitch_weight_default") != 0
        or cfg.get("pitch_weight_max") != 0.05
        or cfg.get("pitch_tolerance_semitones") != 12
    ):
        raise InputError("search pitch: requires off default, maximum .05 and 12-semitone scale")
    expected = {
        "job_seconds",
        "http_attempts",
        "download_bytes",
        "workers",
        "indexed_windows",
        "processed_window_seconds",
        "read_audio_seconds",
        "feature_bytes",
        "query_jobs",
        "query_preparation_bytes",
        "final_attempts",
        "final_windows",
        "pilot_windows",
        "clips",
        "clip_bytes",
    }
    if set(cfg["policy"]) != {"max_" + k for k in expected}:
        raise InputError("search policy: complete finite ceilings required")
    for key, v in cfg["policy"].items():
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 2**31:
            raise InputError("search policy: invalid " + key)
    if (
        cfg["policy"]["max_download_bytes"] != 0
        or cfg["policy"]["max_http_attempts"] != 0
        or cfg["policy"]["max_final_attempts"] != 1
    ):
        raise InputError("A06 requires offline operation and one final attempt")
    return cfg


def frozen(budget, method="efficientat"):
    root = budget.root
    choice = record(root / "manifests/matchers/choice.json")
    shortlist = record(root / "manifests/matchers/shortlist.json")
    protocol, suite = comparison_pair(root)
    desc = descriptor(root, method)
    if (
        choice["record_hash"] != CHOICE
        or choice["stage"] != "A05"
        or choice["selected_on"] != "development"
        or choice["config_hash"] != CONFIG
        or choice["method_id"] != "efficientat"
        or choice["shortlist_hash"] != shortlist["record_hash"]
        or protocol["record_hash"] != PROTOCOL
        or suite["record_hash"] != SUITE
        or choice["protocol_hash"] != PROTOCOL
        or choice["suite_hash"] != SUITE
        or desc != shortlist["methods"].get(method)
    ):
        raise InputError("A06 frozen choice/shortlist/protocol/suite/representation differs")
    if method == "efficientat":
        receipt = record(root / "manifests/matchers/checkpoint.json")
        path = checkpoint_path(root)
        if (
            receipt["sha256"] != desc["checkpoint"]["sha256"]
            or not path.is_file()
            or path.stat().st_size != receipt["bytes"]
            or sha256(path, budget) != receipt["sha256"]
            or digest(desc) != CONFIG
        ):
            raise InputError(
                "A06 pinned checkpoint missing/corrupt; restore the exact A05 artifact"
            )
    return choice, shortlist, protocol, suite, desc


def code_identity():
    base = Path(__file__).resolve().parents[1]
    paths = list(base.rglob("*.py"))
    # New coordinator identity canonicalizes line endings. Frozen A05 descriptors
    # deliberately continue hashing their exact pinned source bytes.
    return {
        p.relative_to(base).as_posix(): hashlib.sha256(
            p.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for p in sorted(paths)
    }


def grid(frames, rate, cfg):
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (frames, rate)):
        raise InputError("search grid: positive integer native frames/rate required")
    size = (cfg["window_milliseconds"] * rate + 999) // 1000
    hop = max(1, (cfg["hop_milliseconds"] * rate + 500) // 1000)
    if frames <= size:
        return [(0, frames)]
    starts = list(range(0, frames - size + 1, hop))
    if starts[-1] != frames - size:
        starts.append(frames - size)
    return [(s, s + size) for s in starts]


def union_frames(bounds):
    end, count = 0, 0
    for a, b in sorted(bounds):
        count += max(0, b - max(a, end))
        end = max(end, b)
    return count


def save_array(directory, identity, array, budget):
    """Publish one immutable array+record bundle; crashes leave charged partials."""
    array = np.asarray(array, dtype=np.float32)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise InputError("search array: finite float32 matrix required")
    key = digest(identity)
    target = contained(directory / key, budget.root)
    if target.exists():
        return load_array(target, identity, budget)[1]
    budget.reserve(array.nbytes + 65536, array.nbytes * 3)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".a06-partial-", dir=target.parent))
    with (staging / "features.npy").open("wb") as stream:
        np.save(stream, array, allow_pickle=False)
        stream.flush()
        os.fsync(stream.fileno())
    value = {
        "schema_version": "a06-shard-1",
        "identity": identity,
        "shape": list(array.shape),
        "dtype": "float32",
        "sha256": sha256(staging / "features.npy", budget),
        "bytes": (staging / "features.npy").stat().st_size,
    }
    write_record(staging / "record.json", value, budget)
    staging.rename(target)
    budget.refresh_disk()
    return record(target / "record.json")


def load_array(directory, identity, budget):
    directory = contained(directory, budget.root)
    if directory.name != digest(identity):
        raise InputError("search shard: content key differs from identity")
    if is_link(directory) or is_link(directory / "features.npy"):
        raise InputError("search shard: links refused")
    meta = record(directory / "record.json")
    if meta["identity"] != identity or sha256(directory / "features.npy", budget) != meta["sha256"]:
        raise InputError("search shard: changed source/config or corrupt array")
    if (
        len(meta["shape"]) != 2
        or not 1 <= meta["shape"][0] <= 512
        or meta["shape"][1] != identity["dimension"]
        or meta["bytes"] != (directory / "features.npy").stat().st_size
    ):
        raise InputError("search shard: unbounded/stale shape or byte count")
    budget.reserve(0, meta["bytes"] * 3)
    array = np.load(directory / "features.npy", allow_pickle=False)
    if list(array.shape) != meta["shape"] or array.dtype != np.float32:
        raise InputError("search shard: array shape/precision differs")
    for row in array:
        checked(row, identity["dimension"])
    return array, meta
