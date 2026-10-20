"""Exact bounded ranking: only feature distances, one passage per duplicate group."""

import time

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..matchers.runner import memory_check
from ..storage import InputError, digest
from . import sources
from .contracts import load_array
from .index import coverage, open_index
from .job import charge
from .pitch import estimate, penalty
from .query import load_query


def distances(examples, candidates, kind):
    """Float64 reduction for stable order-invariant exact mean distances."""
    a, b = np.asarray(examples, dtype=np.float64), np.asarray(candidates, dtype=np.float64)
    if (
        a.ndim != 2
        or b.ndim != 2
        or a.shape[1] != b.shape[1]
        or not np.isfinite(a).all()
        or not np.isfinite(b).all()
    ):
        raise InputError("exact ranking: compatible finite feature matrices required")
    if kind == "cosine":
        denominators = np.linalg.norm(a, axis=1)[:, None] * np.linalg.norm(b, axis=1)[None, :]
        if np.any(denominators <= 0):
            raise InputError("exact cosine: zero feature norm")
        per_example = 1 - (a @ b.T) / denominators
    elif kind == "euclidean":
        per_example = np.stack([np.linalg.norm(b - v, axis=1) for v in a])
    else:
        raise InputError("exact ranking: unsupported distance")
    return per_example, np.mean(per_example, axis=0)


def sort_key(hit):
    return hit["score"], hit["recording_id"], hit["start_frame"], hit["end_frame"]


def timbre_key(hit):
    return hit["timbre_distance"], hit["recording_id"], hit["start_frame"], hit["end_frame"]


def excluded_source(source, query, include_self=False):
    if include_self:
        return False
    if source["group"] in query["identity"]["excluded_groups"]:
        return True
    for example in query["examples"]:
        prepared = example["prepared"]
        if (
            source["source"]["sha256"] == prepared["source"]["sha256"]
            or source["source"]["canonical_pcm"]["sha256"]
            == prepared["technical_metadata"]["canonical_pcm"]["sha256"]
        ):
            return True
    return False


def rank(request, budget, context=None):
    consumer = {} if context is None else {"context": context}
    base, manifest, desc, cfg = open_index(
        budget, request["index"], request.get("allow_partial", False), **consumer
    )
    query, features = load_query(budget, request["query"], desc, **consumer)
    weight = request.get("pitch_weight") or 0
    if not np.isfinite(weight) or not 0 <= weight <= cfg["pitch_weight_max"]:
        raise InputError("pitch preference: weight outside 0..0.05")
    if weight and desc["distance"] != "cosine":
        raise InputError("pitch preference: only explicit EfficientAT cosine search supports it")
    identity = {
        "version": "a06-result-1",
        "index_id": manifest["index_id"],
        "indexed_shards_hash": digest(
            {
                k: record(base / "entries" / (k + ".json"))["shards"]
                for k in sorted(manifest["entries"])
            }
        ),
        "coverage_state": manifest["state"],
        "query_id": query["query_id"],
        "pitch_weight": weight,
        "diagnostic_include_self": request.get("include_self", False),
    }
    if context is not None:
        identity["consumer"] = context.result_binding()
    key = digest(identity)
    path = (
        context.results if context is not None else budget.root / "data/runs/search/results"
    ) / (key + ".json")
    # Initial ranks and repeats validate originals/shards under finite read/time caps.
    excluded = set() if request.get("include_self") else set(query["identity"]["excluded_groups"])
    cursor = request.get("cursor", 0)
    progress_path = (
        context.progress if context is not None else budget.root / "data/runs/search/rank-progress"
    ) / (key + ".json")
    if cursor == 0:
        if not progress_path.exists() and not path.exists():
            charge(budget, context=context, query_jobs=1)
        progress_state = {
            "identity": identity,
            "best": {},
            "scored": 0,
            "seconds": 0,
            "state": "in_progress",
        }
        write_record(progress_path, progress_state, budget)
    else:
        progress_state = record(progress_path)
        if progress_state["identity"] != identity:
            raise InputError("rank progress: index/query recipe differs")
    best, scored = progress_state["best"], progress_state["scored"]
    started = time.perf_counter()
    entries = sorted(manifest["entries"])
    for entry in entries[cursor : cursor + 4]:
        progress = record(base / "entries" / (entry + ".json"))
        source = progress["source"]
        samples = sources.load(budget, source, **consumer)
        if excluded_source(source, query, request.get("include_self", False)):
            del samples
            continue
        for shard in progress["shards"]:
            directory = base / "shards" / shard
            metadata = record(directory / "record.json")
            array, _ = load_array(directory, metadata["identity"], budget)
            per, aggregate = distances(features, array, desc["distance"])
            for i, (start, end) in enumerate(metadata["identity"]["bounds"]):
                hit = {
                    "recording_id": entry,
                    "group": source["group"],
                    "start_frame": start,
                    "end_frame": end,
                    "score": float(aggregate[i]),
                    "timbre_distance": float(aggregate[i]),
                    "per_example_distances": per[:, i].tolist(),
                    "pitch_contribution": 0,
                    "pitch": {"hz": None, "reason": "pitch preference off"},
                    "source": source,
                    "duration_mismatch_seconds": [
                        (end - start) / source["source"]["sample_rate_hz"]
                        - v["audio"]["duration_seconds"]
                        for v in query["examples"]
                    ],
                }
                group = source["group"]
                if group not in best or timbre_key(hit) < timbre_key(best[group]):
                    best[group] = hit
            scored += len(array)
        # Timbre chooses the passage. Optional pitch only adjusts distinct-recording
        # ordering, once per best passage, rather than analysing every overlapping window.
        best_hit = best.get(source["group"])
        if weight and best_hit and best_hit["recording_id"] == entry:
            candidate_pitch = estimate(
                samples[best_hit["start_frame"] : best_hit["end_frame"]],
                source["source"]["sample_rate_hz"],
            )
            contribution = penalty([v["pitch"] for v in query["examples"]], candidate_pitch, weight)
            best_hit.update(
                pitch=candidate_pitch,
                pitch_contribution=contribution,
                score=best_hit["timbre_distance"] + contribution,
            )
        del samples
        memory_check(budget)
    cursor = min(len(entries), cursor + 4)
    progress_state.update(
        best=best,
        scored=scored,
        seconds=progress_state["seconds"] + time.perf_counter() - started,
        cursor=cursor,
        state="complete" if cursor == len(entries) else "in_progress",
    )
    write_record(progress_path, progress_state, budget)
    if cursor < len(entries):
        return {
            "status": "ok",
            "state": "in_progress",
            "cursor": cursor,
            "recordings_validated": cursor,
            "expected_recordings": len(entries),
        }
    if context is not None and hasattr(context, "save_winners"):
        # Explicit consumers may retain all timbre winners for a later preference;
        # passage selection and the default top-ten behavior remain unchanged.
        context.save_winners(budget, identity, query, best, scored)
    hits = sorted(best.values(), key=sort_key)[: cfg["results"]]
    value = {
        "schema_version": "a06-result-1",
        "result_id": key,
        "identity": identity,
        "state": "complete" if manifest["state"] == "complete" else "partial",
        "score_direction": "lower_better",
        "metric": desc["distance"],
        "representation": desc,
        "query": query,
        "candidates": hits,
        "excluded_groups": sorted(excluded),
        "eligible_distinct_groups": len(best),
        "scored_windows": scored,
        "coverage": coverage(base, manifest),
        "interpretation": "Ranked candidates; no calibrated probability or presence threshold",
        "ranking_validation_seconds": progress_state["seconds"],
        "peak_working_bytes": memory_check(budget),
    }
    if path.exists():
        old = record(path)
        if old["identity"] != identity or old["candidates"] != hits:
            raise InputError("result reuse: ranking/source identity differs")
        reused = True
    else:
        write_record(path, value, budget)
        reused = False
    return {
        "status": "ok",
        "result": path.relative_to(budget.root).as_posix(),
        "candidates": len(hits),
        "scored_windows": scored,
        "reused": reused,
        "coverage_state": value["state"],
    }
