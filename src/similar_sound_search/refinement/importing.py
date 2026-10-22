"""Separate C02/development adapters; exact native membership and cosine proofs."""

from ..indexing import reader
from ..retrieval import engine as historical_engine
from ..retrieval import history
from ..retrieval.context import load_query
from ..search.ranking import distances, excluded_source
from ..storage import InputError
from .context import Historical


def shortlist(owner, ref, arm):
    if ref != owner.protocol["execution"] or arm != owner.protocol["arm"]:
        raise InputError("C03 requires its explicit pinned immutable execution and arm")
    old = Historical(owner)
    execution, groups = historical_engine.read_shortlist(old, ref, arm=arm)
    if len(groups) != 20 or len({g["group"] for g in groups}) != 20:
        raise InputError("C03 requires exactly twenty distinct input groups")
    if (
        execution["identity"]["snapshot_hash"] != owner.protocol["snapshot"]
        or execution["identity"]["revision_id"] != owner.protocol["delivery"]["revision"]
        or execution["identity"]["materialization_id"]
        != owner.protocol["delivery"]["materialization"]
        or [v["historical_bank_hash"] for v in execution["identity"]["banks"]]
        != owner.protocol["primary_banks"]
    ):
        raise InputError("C03 execution snapshot/banks/query binding differs")
    return old, execution, groups


def environment(budget, owner, receipt, ref, arm):
    old, execution, groups = shortlist(owner, ref, arm)
    _, view, banks = history.open_snapshot(budget, owner, receipt)
    rev, saved, query, features = load_query(budget, owner)
    if (
        query["record_hash"] != execution["identity"]["query_hash"]
        or query["feature_hash"] != execution["identity"]["query_feature_hash"]
        or query != old.get(execution["query_ref"], "queries")
        or execution["event_map"] != execution["identity"]["events"]
    ):
        raise InputError("C03 exact query/feature/event binding differs")
    return old, execution, groups, view, banks, rev, saved, query, features


def check_row(row, source, bank_hash, passages, array, features, variants):
    if (
        row["recording_id"] != source["recording_id"]
        or row["group"] != source["group"]
        or row["rate"] != source["source"]["sample_rate_hz"]
        or row["bank_hash"] != bank_hash
        or row["row"] not in range(len(passages))
    ):
        raise InputError("C03 semantic row source/group/rate/bank/index differs")
    passage = passages[row["row"]]
    if any(row[k] != passage[k] for k in passage):
        raise InputError("C03 semantic row differs from exact shard/native membership")
    a, b = row["original_bounds"]
    rate = source["source"]["sample_rate_hz"]
    if row["original_context"] != [
        max(0, a - rate),
        min(source["source"]["sample_count"], b + rate),
    ]:
        raise InputError("C03 original context differs from actual scored row")
    per, means = distances(features, array[row["row"] : row["row"] + 1], "cosine")
    # Historical BLAS block shape may affect the final few reduction bits.
    import numpy as np

    if not np.allclose(per[:, 0], row["per_example_distances"], rtol=0, atol=2e-15):
        raise InputError("C03 historical per-example distance differs from exact array")
    expected = means[0] if "variant_id" not in row else per[variants.index(row["variant_id"]), 0]
    if abs(float(expected) - row["distance"]) > 2e-15:
        raise InputError("C03 historical objective distance differs")
    return array[row["row"]]


def group_rows(budget, owner, old, group, view, banks, query, features):
    if (
        group.get("schema_version") != "c02-c03-group-1"
        or group["group"] in query["identity"]["excluded_groups"]
    ):
        raise InputError("C03 invalid/excluded group")
    support = old.get(group["group_support"], "group-supports")
    if support["sources"] != group["sources"]:
        raise InputError("C03 group/source support membership differs")
    variants = [e["example_id"] for e in query["examples"]]
    source_map = {}
    for rid, ref in group["sources"].items():
        source = old.get(ref, "sources")["source"]
        if (
            source["recording_id"] != rid
            or source["group"] != group["group"]
            or excluded_source(source, query)
        ):
            raise InputError("C03 candidate/source/duplicate/query exclusion differs")
        if any(b["value"]["signals"].get(rid, {}).get("original") != source for b in banks):
            raise InputError("C03 source absent/different in selected complete bank")
        source_map[rid] = source
    cache = {}
    for bank in banks:
        bh = bank["binding"]["historical_bank_hash"]
        for unit in bank["value"]["committed"]:
            if unit["signal_id"] in source_map:
                array, passages = reader.rows(budget, view, bank["value"], unit)
                cache[bh, unit["unit_id"]] = array, passages
    rows = []
    for key, obj in support["objectives"].items():
        bh, variant = key.split(":")
        if bh not in owner.protocol["primary_banks"] or variant not in variants:
            raise InputError("C03 unsupported bank/variant objective")
        rows.extend({**r, "variant_id": variant} for r in obj["rows"])
    rows.append(support["baseline_row"])
    for p in group["passages"]:
        if p["scored_bounds"] != p["representative"]["original_bounds"] or p["envelope_is_scored"]:
            raise InputError("C03 display envelope cannot be scored evidence")
        rows.extend(p["supports"])
        rows.append(p["representative"])
    vectors = {}
    for row in rows:
        if (row["bank_hash"], row["shard"]) not in cache or row["recording_id"] not in source_map:
            raise InputError("C03 row shard/source is outside exact membership")
        arr, passages = cache[row["bank_hash"], row["shard"]]
        vectors[row["row_id"]] = check_row(
            row,
            source_map[row["recording_id"]],
            row["bank_hash"],
            passages,
            arr,
            features,
            variants,
        )
    # Lookups allow reuse only for exact original samples/representation/native bounds.
    lookup = {}
    for (bh, shard), (arr, passages) in cache.items():
        for i, passage in enumerate(passages):
            lookup[passage["signal_id"], tuple(passage["original_bounds"])] = {
                "vector": arr[i],
                "reference": {
                    "bank_hash": bh,
                    "shard": shard,
                    "row": i,
                    "row_id": passage["row_id"],
                    "native_bounds": passage["original_bounds"],
                },
            }
    return source_map, vectors, lookup
