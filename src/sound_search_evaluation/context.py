"""D02 pool and compact storage using the product's protected accounting machinery."""

import base64
import hashlib
import json
import math
import zlib
from pathlib import Path

from similar_sound_search.application.codec import decode
from similar_sound_search.application.context import CEILINGS as APPLICATION_LIMITS
from similar_sound_search.application.context import Context as ApplicationContext
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.matchers.models import adapter
from similar_sound_search.storage import InputError, contained, digest, read_json

MIB = 1024**2
CEILINGS = {
    **APPLICATION_LIMITS,
    "feature_windows": 4096,
    "processed_window_seconds": 20000,
    "query_jobs": 128,
    "metadata_bytes": 256 * MIB,
    "managed_output_bytes": 1024 * MIB,
}
PACKED_KINDS = {"score-results", "aggregates", "predictions"}


def expand(value):
    """Strict lossless JSON stream, bounded independently of compressed size."""
    if value.get("encoding") != "zlib-json-utf8":
        raise InputError("D02 packed record encoding differs")
    packed = base64.b64decode(value["payload"], validate=True)
    inflater = zlib.decompressobj()
    raw = inflater.decompress(packed, 8 * MIB + 1)
    if (
        len(raw) > 8 * MIB
        or not inflater.eof
        or inflater.unused_data
        or inflater.unconsumed_tail
        or len(raw) != value["plain_bytes"]
        or hashlib.sha256(raw).hexdigest() != value["plain_sha256"]
    ):
        raise InputError("D02 compressed record size/hash/stream differs")
    restored = json.loads(raw)
    if not isinstance(restored, dict):
        raise InputError("D02 packed record must decode to an object")
    return {**restored, "record_hash": value["record_hash"]}


def pack(value, schema, kind=None):
    raw = json.dumps(
        {k: v for k, v in value.items() if k != "record_hash"},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(raw) > 8 * MIB:
        raise InputError("D02 record exceeds 8 MiB decoded bound")
    return dict(
        schema_version=schema,
        encoding="zlib-json-utf8",
        plain_bytes=len(raw),
        plain_sha256=hashlib.sha256(raw).hexdigest(),
        payload=base64.b64encode(zlib.compress(raw, 9)).decode("ascii"),
        **(dict(kind=kind) if kind else {}),
    )


class Context(ApplicationContext):
    """Same reserve/serialized-write/settlement methods; genuine separate D02 ledger.

    Counter keys intentionally match the shared machinery. import_bytes counts
    generated audio and controlled uploads together, under the D02 128 MiB cap.
    Shared application OS locks also prevent cross-owner numerical overlap.
    """

    def __init__(self, root, allocation=None, split="development"):
        self.root = Path(root).resolve()
        self.cfg = read_json(self.root / "config/assessment.json")
        if (
            self.cfg.get("schema_version") != "d02-assessment-1"
            or set(self.cfg["policy"]) != {"max_" + k for k in CEILINGS}
            or self.cfg["protected_metadata_bytes"] < 32 * MIB
            or self.cfg["attempt_bookkeeping_bytes"] != 262144
            or self.cfg["host"] != "127.0.0.1"
            or split not in {"development", "confirmation"}
        ):
            raise InputError("D02 fixed owner, protected reserve and explicit split required")
        for k, cap in CEILINGS.items():
            n = self.cfg["policy"]["max_" + k]
            if isinstance(n, bool) or not isinstance(n, int) or not 0 < n <= cap:
                raise InputError("D02 invalid/increased ceiling: " + k)
        self.protocol = record(self.root / "manifests/assessment/protocol.json")
        self.directory = self.root / "data/runs/assessment"
        self.features = self.root / "data/features/assessment"
        self.audio = self.root / "data/audio/assessment"
        self.reports = self.root / "reports/local/d02"
        self.split = split
        self.allocation = allocation
        self.query_vectors_cache = {}

    def pool(self):
        path = self.directory / "pool.json"
        if not path.exists():
            return dict(
                schema_version="d02-pool-1",
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
        if (
            value["schema_version"] != "d02-pool-1"
            or set(value["counts"]) != set(CEILINGS)
            or set(value["ceilings"]) != set(CEILINGS)
        ):
            raise InputError("D02 corrupt pool; never reset or substitute a historical pool")
        for k in CEILINGS:
            n = value["counts"][k]
            if (
                isinstance(n, bool)
                or not isinstance(n, (int, float))
                or not math.isfinite(n)
                or n < 0
                or n > value["ceilings"][k]
                or value["ceilings"][k] > self.cfg["policy"]["max_" + k]
            ):
                raise InputError("D02 persisted ceiling exceeds fixed policy")
        return {k: v for k, v in value.items() if k != "record_hash"}

    def get(self, ref, kind):
        if kind in PACKED_KINDS:
            value = super().get(ref, kind)
            if value.get("schema_version") != "d02-packed-record-1":
                return value
            if value.get("kind") != kind:
                raise InputError("D02 packed record kind differs")
            return expand(value)
        if kind == "assessments":
            value = super().get(ref, kind)
            if value.get("schema_version") != "d02-packed-assessment-1":
                return value
            restored = expand(value)
            if restored.get("schema_version") != "d02-scores-1":
                raise InputError("D02 packed assessment schema differs")
            return {**restored, "record_hash": value["record_hash"]}
        if kind == "group-results" and "container" in ref:
            path = contained(self.root / ref["path"], self.directory / "group-batches")
            container = record(path)
            if (
                path.stem != ref["container"]
                or container["record_hash"] != ref["container"]
                or container["schema_version"] != "d02-group-batch-1"
                or isinstance(ref["slot"], bool)
                or not isinstance(ref["slot"], int)
                or not 0 <= ref["slot"] < len(container["items"])
            ):
                raise InputError("D02 group batch reference differs")
            value = container["items"][ref["slot"]]
            if (
                value["record_hash"] != ref["record_hash"]
                or digest({k: v for k, v in value.items() if k != "record_hash"})
                != ref["record_hash"]
            ):
                raise InputError("D02 packed group content/hash differs")
            return decode(value)
        return super().get(ref, kind)

    def put(self, budget, kind, value):
        if kind in PACKED_KINDS:
            # Preserve every pre-transition reference and byte, including exact
            # product/component replay roots. Only genuinely new content packs.
            old_key = digest({k: v for k, v in value.items() if k != "record_hash"})
            if (self.directory / kind / (old_key + ".json")).exists():
                return super().put(budget, kind, value)
            value = pack(value, "d02-packed-record-1", kind)
        if kind == "assessments":
            value = pack(value, "d02-packed-assessment-1")
        return super().put(budget, kind, value)

    def model(self, budget, desc):
        if not hasattr(self, "feature_model"):
            self.feature_model = desc, adapter(budget, "efficientat", desc)[0]
        if self.feature_model[0] != desc:
            raise InputError("D02 representation changed inside a bounded worker")
        return self.feature_model[1]

    def query_ancestry(self, item):
        """Only actual PCM parents, never generator/family relevance labels."""
        if item["kind"] != "asset":
            raise InputError("D02 evaluation supports original assets only")
        asset = record(self.directory / "library/assets" / (item["asset_id"] + ".json"))
        audio = asset["identity"]["audio"]
        pcm = audio["canonical_pcm"]["sha256"]
        groups = {digest(["d02-reference-parent-1", pcm])}
        path = self.directory / "populations" / (self.split + ".json")
        if path.exists():
            for source in record(path)["sources"]:
                if (
                    source["source"]["sha256"] == audio["sha256"]
                    or source["source"]["canonical_pcm"]["sha256"] == pcm
                ):
                    groups.add(source["group"])
        return groups
