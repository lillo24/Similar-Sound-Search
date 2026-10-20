"""Exact revision executions and pitch reranking of complete eligible timbre winners."""

import copy
from pathlib import Path

import numpy as np

from ..evaluation.artifacts import record
from ..events.compatibility import INDEX
from ..matchers.runner import memory_check
from ..search import ranking, sources
from ..search.contracts import load_array
from ..search.index import open_index
from ..storage import InputError, contained, digest
from . import materialization, pitch


def lookup_path(owner, query_id, receipt_hash):
    identity = {"index_id": INDEX, "query_id": query_id, "receipt": receipt_hash}
    return owner.directory / "winner-bindings" / (digest(identity) + ".json")


def validate_winners(budget, owner, path, index_path, query_value):
    base, manifest, desc, cfg = open_index(budget, index_path, context=owner)
    value = record(contained(path, owner.directory / "winners"))
    identity = value["identity"]
    if (
        value.get("schema_version") != "b03-winners-1"
        or value["complete"] is not True
        or value["query_hash"] != query_value["record_hash"]
        or identity["query_id"] != query_value["query_id"]
        or identity["index_id"] != manifest["index_id"]
        or identity["consumer"] != owner.result_binding()
        or identity["pitch_weight"] != 0
        or identity["diagnostic_include_self"]
    ):
        raise InputError("B03 complete winners: query/index/consumer/support binding changed")
    nodes = {k: record(base / "entries" / (k + ".json")) for k in sorted(manifest["entries"])}
    if identity["indexed_shards_hash"] != digest({k: v["shards"] for k, v in nodes.items()}):
        raise InputError("B03 complete winners: index/shards changed")
    groups = {
        v["source"]["group"]
        for v in nodes.values()
        if not ranking.excluded_source(v["source"], query_value)
    }
    winners = value["winners"]
    if (
        len(winners) != len(groups)
        or value["eligible_groups"] != len(groups)
        or {v["group"] for v in winners} != groups
        or winners != sorted(winners, key=ranking.timbre_key)
    ):
        raise InputError(
            "B03 complete winners: incomplete/duplicate candidate set; top-ten reranking refused"
        )
    for winner in winners:
        node = nodes.get(winner["recording_id"])
        if (
            node is None
            or node["source"] != winner["source"]
            or winner["source"]["group"] != winner["group"]
            or winner["score"] != winner["timbre_distance"]
            or not np.isfinite(winner["timbre_distance"])
        ):
            raise InputError("B03 complete winners: source or timbre score changed")
        supported = any(
            [winner["start_frame"], winner["end_frame"]]
            in record(base / "shards" / key / "record.json")["identity"]["bounds"]
            for key in node["shards"]
        )
        if not supported:
            raise InputError("B03 complete winners: candidate native interval not in frozen grid")
    return value, base, nodes, desc, cfg


def step(request, budget, owner, revision):
    saved = materialization.receipt(owner, revision)
    receipt_path = contained(Path(request["receipt"]), owner.directory / "compatibility")
    receipt_hash = record(receipt_path)["record_hash"]
    lookup = lookup_path(owner, saved["identity"]["query_id"], receipt_hash)
    index_path = Path(request["index"])
    fresh_rank = False
    if not lookup.exists():
        result = ranking.rank(
            {
                **request,
                "query": str(owner.root / saved["query"]),
                "pitch_weight": 0,
                "include_self": False,
            },
            budget,
            context=owner,
        )
        if result.get("state") == "in_progress":
            return result
        fresh_rank = True
    binding = record(lookup)
    winners_path = contained(owner.root / binding["winners"], owner.directory / "winners")
    # Reopening always validates the actual revision media and feature array; a
    # historical result cannot hide a missing original or conditioning cue.
    _, query_value, _ = materialization.load(budget, owner, revision)
    winners, base, nodes, _, cfg = validate_winners(
        budget, owner, winners_path, index_path, query_value
    )
    policy = revision["recipe"]["pitch"]
    identity = {
        "version": "b03-execution-1",
        "revision_id": revision["revision_id"],
        "materialization_id": saved["materialization_id"],
        "query_hash": query_value["record_hash"],
        "winners_hash": winners["record_hash"],
        "receipt_hash": receipt_hash,
        "pitch_policy": policy,
        "policy_code": pitch.estimate_identity(np.zeros((1, 1), np.float32), 8000)[
            "estimator_code"
        ],
        "consumer": owner.result_binding(),
    }
    key = digest(identity)
    output = owner.directory / "executions" / (key + ".json")
    existing = output.exists()
    if existing:
        old = record(output)
        if old["identity"] != identity:
            raise InputError("B03 execution: immutable result binding changed")
    if existing or (policy["weight"] == 0 and not fresh_rank):
        verification_path = owner.directory / "execution-verification" / (key + ".json")
        verification = record(verification_path) if verification_path.exists() else None
        if verification is None or (verification["complete"] and request.get("cursor", 0) == 0):
            verification = {"identity": identity, "cursor": 0, "complete": False}
        if verification["identity"] != identity:
            raise InputError("B03 execution reuse: validation identity changed")
        start = verification["cursor"]
        for winner in winners["winners"][start : start + 4]:
            samples = sources.load(budget, winner["source"], context=owner)
            for shard in nodes[winner["recording_id"]]["shards"]:
                directory = base / "shards" / shard
                load_array(directory, record(directory / "record.json")["identity"], budget)
            del samples
        verification["cursor"] = min(len(winners["winners"]), start + 4)
        verification["complete"] = verification["cursor"] == len(winners["winners"])
        owner.publish(
            budget, verification_path, {k: v for k, v in verification.items() if k != "record_hash"}
        )
        if not verification["complete"]:
            return {
                "status": "ok",
                "state": "in_progress",
                "cursor": verification["cursor"],
                "reuse_sources_validated": verification["cursor"],
            }
        if existing:
            return {
                "status": "ok",
                "execution": output.relative_to(owner.root).as_posix(),
                "reused": True,
                "revision_id": revision["revision_id"],
                "candidates": len(old["candidates"]),
            }
    progress_path = owner.directory / "pitch-progress" / (key + ".json")
    if policy["weight"] == 0:
        ranked = copy.deepcopy(winners["winners"])
        for hit in ranked:
            hit["pitch"] = {"hz": None, "reason": "pitch preference off", "reliable_blocks": 0}
            hit["pitch_detail"] = pitch.contribution(
                [v["pitch"] for v in query_value["examples"]], hit["pitch"], policy
            )
    else:
        if progress_path.exists():
            progress = record(progress_path)
            if progress["identity"] != identity:
                raise InputError("B03 pitch resumption: revision/winners/policy changed")
        else:
            owner.charge(budget, query_jobs=1)
            progress = {"identity": identity, "cursor": 0, "ranked": []}
        start = progress["cursor"]
        for original in winners["winners"][start : start + 4]:
            hit = copy.deepcopy(original)
            samples = sources.load(budget, hit["source"], context=owner)
            # Validate the complete feature closure used to choose this winner;
            # no new vectors or alternate passage selections are computed.
            for shard in nodes[hit["recording_id"]]["shards"]:
                directory = base / "shards" / shard
                load_array(directory, record(directory / "record.json")["identity"], budget)
            a, b = hit["start_frame"], hit["end_frame"]
            estimate = pitch.cached_estimate(
                budget, owner, samples[a:b], hit["source"]["source"]["sample_rate_hz"]
            )
            detail = pitch.contribution(
                [v["pitch"] for v in query_value["examples"]], estimate, policy
            )
            hit.update(
                pitch=estimate,
                pitch_detail=detail,
                pitch_contribution=detail["value"],
                score=hit["timbre_distance"] + detail["value"],
            )
            progress["ranked"].append(hit)
            del samples
            memory_check(budget)
        progress["cursor"] = len(progress["ranked"])
        owner.publish(
            budget, progress_path, {k: v for k, v in progress.items() if k != "record_hash"}
        )
        if progress["cursor"] < len(winners["winners"]):
            return {
                "status": "ok",
                "state": "in_progress",
                "cursor": 0,
                "pitch_validated": progress["cursor"],
            }
        ranked = progress["ranked"]
    ranked = sorted(ranked, key=ranking.sort_key)
    value = {
        "schema_version": "b03-execution-1",
        "execution_id": key,
        "identity": identity,
        "revision": revision,
        "materialization": saved,
        "query": query_value,
        "index": str(index_path.relative_to(owner.root)),
        "winners": winners_path.relative_to(owner.root).as_posix(),
        "state": "complete",
        "candidates": ranked[: cfg["results"]],
        "complete_ranking": ranked,
        "eligible_distinct_groups": len(ranked),
        "scored_windows": winners["scored_windows"],
        "excluded_groups": query_value["identity"]["excluded_groups"],
        "interpretation": "timbre selects passages; optional bounded pitch reorders complete "
        "group winners; no calibrated relevance/presence",
    }
    owner.publish(budget, output, value, immutable=True)
    return {
        "status": "ok",
        "execution": output.relative_to(owner.root).as_posix(),
        "reused": False,
        "revision_id": revision["revision_id"],
        "candidates": len(value["candidates"]),
        "eligible_distinct_groups": len(ranked),
        "scored_windows": value["scored_windows"],
    }
