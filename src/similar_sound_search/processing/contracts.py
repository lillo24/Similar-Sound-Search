"""Exact semantic rows, classified consumers and strict explicit input revisions."""

import ast
import hashlib
from pathlib import Path

from ..evaluation.artifacts import record
from ..indexing.banks import original_signal, sample_identity
from ..search.contracts import code_identity, grid, source_function_identity
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


def consumer_reference(proof):
    return dict(
        declaration_hash=proof["declaration_hash"],
        numerical_hash=proof["numerical_hash"],
        code_hash=digest(proof["code"]),
        version=proof.get("version", "c04-consumer-1"),
    )


def compatible_consumer(owner, previous, current):
    """Only the exact declared metadata codec/coordinator transition is accepted."""
    path = owner.root / "manifests/processing/metadata-compatibility.json"
    if not path.exists():
        return None
    proof = record(path)
    if (
        proof.get("schema_version") != "c04-metadata-compatibility-1"
        or proof["before_consumer"] != previous
        or proof["after_code"] != current["code"]
        or proof["after_numerical_hash"] != current["numerical_hash"]
    ):
        return None
    allowed = {
        "processing/api.py",
        "processing/job.py",
        "processing/contracts.py",
        "processing/engine.py",
    }
    declaration = record(owner.root / "manifests/processing/consumer.json")
    if declaration.get("metadata_compatibility") != proof["record_hash"]:
        raise InputError("C04 metadata compatibility: declaration binding changed")
    if (
        {k for k in previous["code"] if previous["code"][k] != current["code"].get(k)} != allowed
        or set(current["code"]) - set(previous["code"]) != {"processing/records.py"}
        or proof["changed_files"] != sorted(allowed)
        or proof["numerical_calls_unchanged"] is not True
    ):
        raise InputError("C04 metadata compatibility: unclassified drift")
    base = Path(__file__).resolve().parents[1]
    for relative, expected in proof["unchanged_functions"].items():
        original = proof["original_sources"][relative]
        if (
            hashlib.sha256(original.replace("\r\n", "\n").encode()).hexdigest()
            != previous["code"][relative]
        ):
            raise InputError("C04 metadata compatibility: original source differs")
        if (
            source_function_identity(original, expected) != expected
            or source_function_identity((base / relative).read_text(), expected) != expected
        ):
            raise InputError("C04 metadata compatibility: numerical/reservation function changed")

    def calls(source):
        return sorted(
            ast.dump(n, include_attributes=False)
            for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "engine"
        )

    if calls(proof["original_sources"]["processing/job.py"]) != calls(
        (base / "processing/job.py").read_text()
    ):
        raise InputError("C04 metadata compatibility: numerical arguments changed")

    def scoring_body(source):
        node = next(
            n
            for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == "score"
        )

        def target(n):
            return (
                n.targets[0].id
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                else None
            )

        prefix = [n for n in node.body if target(n) in {"refs", "q", "query_hash", "matrix"}]
        numerical, active = [], False
        for n in node.body:
            if target(n) == "examples":
                active = True
            if active:
                numerical.append(n)
            if target(n) == "result":
                break
        node.body = prefix + numerical
        for call in ast.walk(node):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "query_vectors_cached"
            ):
                call.func.id = "query_vectors"
        return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()

    for text in (
        proof["original_sources"]["processing/engine.py"],
        (base / "processing/engine.py").read_text(),
    ):
        if scoring_body(text) != proof["unchanged_score_body"]:
            raise InputError("C04 metadata compatibility: scoring computation changed")

    def aggregation_body(source):
        node = next(
            n
            for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == "aggregate"
        )
        node.body = [
            n
            for n in node.body
            if not (
                isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "arms_to_publish" for t in n.targets)
            )
            and not (
                isinstance(n, ast.If)
                and any(isinstance(x, ast.Name) and x.id == "arms_to_publish" for x in ast.walk(n))
            )
        ]
        for n in node.body:
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "arm":
                n.iter = ast.parse("('legacy-mean','event-legacy','event-multi')", mode="eval").body
        return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()

    for text in (
        proof["original_sources"]["processing/engine.py"],
        (base / "processing/engine.py").read_text(),
    ):
        if aggregation_body(text) != proof["unchanged_aggregation_body"]:
            raise InputError("C04 metadata compatibility: aggregation computation changed")
    return proof["record_hash"]


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
