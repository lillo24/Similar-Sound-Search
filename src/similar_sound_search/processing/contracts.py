"""Exact semantic rows, classified consumers and strict explicit input revisions."""

from ..evaluation.artifacts import record
from ..indexing.banks import original_signal, sample_identity
from ..search.contracts import code_identity, grid
from ..storage import InputError, digest

INHERITED_NUMERICAL = (
    "inputs.py",
    "preparation.py",
    "records.py",
    "matchers/acoustic.py",
    "matchers/efficientat.py",
    "matchers/efficientat_model.py",
    "matchers/models.py",
    "matchers/windows.py",
    "queries/assets.py",
    "queries/features.py",
    "queries/materialization.py",
    "search/contracts.py",
    "search/ranking.py",
    "search/sources.py",
    "indexing/banks.py",
    "indexing/reader.py",
    "retrieval/fusion.py",
    "retrieval/engine.py",
    "refinement/geometry.py",
    "refinement/importing.py",
    "refinement/engine.py",
    "events/compatibility.py",
)


def source_key(source):
    # File bytes remain part of identity even for equal PCM; ancestry/labels do not.
    return digest(sample_identity(original_signal(source)))


def row_identity(source, bounds, desc):
    a, b = bounds
    if (
        any(isinstance(v, bool) or not isinstance(v, int) for v in bounds)
        or not 0 <= a < b <= source["source"]["sample_count"]
    ):
        raise InputError("C04 row: native support outside original source")
    return dict(
        version="c04-native-row-1",
        samples=sample_identity(original_signal(source)),
        native_bounds=list(bounds),
        representation=desc,
        preparation="native-original-1",
    )


def row_key(source, bounds, desc):
    return digest(row_identity(source, bounds, desc))


def consumer(owner):
    value = record(owner.root / "manifests/processing/consumer.json")
    current = code_identity()
    if (
        value.get("schema_version") != "c04-consumer-1"
        or value["code"] != current
        or set(value["classification"]) != set(current)
        or any(
            v not in {"numerical", "coordinator", "historical"}
            for v in value["classification"].values()
        )
    ):
        raise InputError(
            "C04 consumer drift/unclassified source; declare and verify compatibility first"
        )
    numerical = {k: v for k, v in current.items() if value["classification"][k] == "numerical"}
    if value["numerical_hash"] != digest(numerical):
        raise InputError("C04 numerical compatibility proof differs")
    previous = record(owner.root / "manifests/refinement/report-repair.json")["consumer_code"]
    if value.get("inherited_numerical") != {k: previous[k] for k in INHERITED_NUMERICAL}:
        raise InputError("C04 inherited numerical scope/proof differs")
    for key in INHERITED_NUMERICAL:
        if current[key] != previous[key] or value["classification"][key] != "numerical":
            raise InputError("C04 inherited primitive changed: " + key)
    return dict(
        declaration_hash=value["record_hash"],
        code=current,
        numerical_hash=value["numerical_hash"],
        version="c04-consumer-1",
    )


def validate_input(owner, value):
    required = {
        "schema_version",
        "label",
        "sources",
        "banks",
        "query",
        "policy",
        "packing",
        "refinement",
        "historical",
    }
    if set(value) != required or value["schema_version"] != "c04-input-1":
        raise InputError("C04 input: expected complete c04-input-1 schema")
    if not isinstance(value["label"], str) or not 1 <= len(value["label"]) <= 200:
        raise InputError("C04 input: bounded display label required")
    if (
        isinstance(value["packing"], bool)
        or not isinstance(value["packing"], int)
        or not 1 <= value["packing"] <= 128
    ):
        raise InputError("C04 input: packing requires 1..128 rows")
    if value["historical"] not in (True, False) or value["refinement"] not in {"off", "historical"}:
        raise InputError("C04 input: unsupported historical/refinement mode")
    keys = []
    if not 1 <= len(value["sources"]) <= owner.cfg["max_sources"]:
        raise InputError("C04 explicit nonempty source population exceeds bound")
    for source in value["sources"]:
        for key in ("recording_id", "group", "source", "rights", "kind", "title", "offset"):
            if key not in source:
                raise InputError("C04 source missing " + key)
        source_key(source)
        keys.append(source["recording_id"])
    if len(set(keys)) != len(keys):
        raise InputError("C04 duplicate recording identity in population")
    if not 1 <= len(value["banks"]) <= 2:
        raise InputError("C04 supports one or two complete original banks")
    labels = []
    for bank in value["banks"]:
        if set(bank) != {"label", "grid"}:
            raise InputError("C04 bank: label and native grid required")
        cfg = bank["grid"]
        if (
            set(cfg) != {"window_milliseconds", "hop_milliseconds"}
            or any(
                isinstance(v, bool) or not isinstance(v, int) or not 0 < v <= 4800
                for v in cfg.values()
            )
            or cfg["hop_milliseconds"] > cfg["window_milliseconds"]
        ):
            raise InputError("C04 bank: bounded native original grid required")
        labels.append(bank["label"])
    if len(set(labels)) != len(labels):
        raise InputError("C04 bank labels duplicated")
    p = value["policy"]
    if set(p) != {"arm", "association"} or p["arm"] not in {
        "legacy-mean",
        "event-legacy",
        "event-multi",
    }:
        raise InputError("C04 policy: unsupported objective/aggregation")
    query = value["query"]
    if query.get("kind") == "native":
        if set(query) != {"kind", "source", "bounds", "excluded_groups", "lineage"}:
            raise InputError(
                "C04 native query: exact audio, bounds, exclusion and lineage required"
            )
        if not 1 <= len(query["bounds"]) <= 8 or not isinstance(query["lineage"], dict):
            raise InputError("C04 native query: 1..8 examples and explicit lineage required")
        for bounds in query["bounds"]:
            row_identity(query["source"], bounds, {})
            if (bounds[1] - bounds[0]) / query["source"]["source"]["sample_rate_hz"] > 30:
                raise InputError("C04 query example exceeds 30 seconds")
        if query["lineage"] != {
            "source_sha256": query["source"]["source"]["sha256"],
            "cue": None,
            "transform": "original",
        }:
            raise InputError("C04 query/cue lineage mismatch or unsupported transform")
    elif query.get("kind") in {"saved", "saved-derived"}:
        if set(query) != {"kind", "revision", "materialization"}:
            raise InputError("C04 saved query: immutable revision/materialization required")
        for k in ("revision", "materialization"):
            if not isinstance(query[k], str) or len(query[k]) != 64:
                raise InputError("C04 saved query invalid " + k)
    else:
        raise InputError("C04 unsupported query schema/transform")
    if value["refinement"] == "historical" and not value["historical"]:
        raise InputError("C04 historical refinement requires its exact historical population")
    return value


def native_rows(source, banks):
    return sorted(
        {
            tuple(b)
            for bank in banks
            for b in grid(
                source["source"]["sample_count"], source["source"]["sample_rate_hz"], bank["grid"]
            )
        }
    )
