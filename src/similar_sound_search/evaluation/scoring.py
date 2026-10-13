"""Model-independent signed ranks, one-to-one event matching and honest denominators."""

import time

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import rankdata

from ..records import finite_number
from ..storage import InputError, digest
from .artifacts import load_asset, record, write_record
from .published import unique_pairs
from .suite import load_suite


def signed_rank(human, scores, direction="lower_better"):
    if direction not in {"lower_better", "higher_better"}:
        raise InputError("rank correlation: explicit score direction required")
    a, b = np.asarray(human, dtype=float), np.asarray(scores, dtype=float)
    if a.ndim != 1 or a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise InputError("rank correlation: equal finite observation vectors required")
    denominator = len(a)
    if denominator < 3:
        return {"rho": None, "pairs": denominator, "reason": "fewer than three valid unique pairs"}
    if len(np.unique(a)) < 2 or len(np.unique(b)) < 2:
        return {"rho": None, "pairs": denominator, "reason": "constant ratings or scores"}
    # Average per-observation ranks, never the argsort ordering permutation.
    ra, rb = rankdata(a, method="average"), rankdata(b, method="average")
    if direction == "higher_better":
        rb = -rb
    rho = float(np.corrcoef(ra, rb)[0, 1])
    return {
        "rho": rho,
        "pairs": denominator,
        "reason": None,
        "uncertainty": "descriptive; no independent-pair CI or unqualified dataset pooling",
    }


def iou(a, b):
    if a["asset_id"] != b["asset_id"]:
        return 0.0
    overlap = max(0, min(a["end_frame"], b["end_frame"]) - max(a["start_frame"], b["start_frame"]))
    union = max(a["end_frame"], b["end_frame"]) - min(a["start_frame"], b["start_frame"])
    return overlap / union


def event_matches(predictions, targets, minimum_iou=0.5):
    if not predictions or not targets:
        return []
    overlaps = np.array([[iou(p, t) for t in targets] for p in predictions])
    valid = overlaps >= minimum_iou
    # Cardinality dominates all possible IoU tie-break contributions.
    weights = valid.astype(float) + np.where(valid, overlaps, 0) / (min(overlaps.shape) + 1)
    rows, columns = linear_sum_assignment(-weights)
    return [
        (int(r), int(c), float(overlaps[r, c]))
        for r, c in zip(rows, columns, strict=True)
        if valid[r, c]
    ]


def ranked(values, direction, assets):
    if not isinstance(values, list) or len(values) > 128:
        raise InputError("prediction stage: expected at most 128 scored intervals per query")
    unique = {}
    for p in values:
        if not isinstance(p, dict) or set(p) != {"asset_id", "start_frame", "end_frame", "score"}:
            raise InputError("prediction interval: expected asset_id/start_frame/end_frame/score")
        key = (p["asset_id"], p["start_frame"], p["end_frame"])
        if key[0] not in assets or not all(
            isinstance(v, int) and not isinstance(v, bool) for v in key[1:]
        ):
            raise InputError("prediction interval: unknown asset or non-integer sample coordinates")
        if not 0 <= key[1] < key[2] <= assets[key[0]]["audio"]["sample_count"]:
            raise InputError("prediction interval: outside decoded available file bounds")
        if not finite_number(p["score"]):
            raise InputError("prediction interval: finite score required")
        if key in unique and unique[key]["score"] != p["score"]:
            raise InputError("prediction duplicate: conflicting scores for the same interval")
        unique[key] = p
    sign = -1 if direction == "higher_better" else 1
    return sorted(
        unique.values(),
        key=lambda p: (sign * p["score"], p["asset_id"], p["start_frame"], p["end_frame"]),
    )


def validate_header(prediction, protocol, split, choice=None):
    if (
        prediction.get("schema_version") != "a04-predictions-1"
        or prediction.get("protocol_hash") != protocol["record_hash"]
    ):
        raise InputError("predictions: stale or unsupported protocol/schema")
    if (
        prediction.get("split") != split
        or prediction.get("coordinate_basis") != "decoded_available_file"
    ):
        raise InputError("predictions: split/coordinate basis mismatch")
    if prediction.get("score_direction") not in {"higher_better", "lower_better"}:
        raise InputError("predictions: missing score direction")
    if not all(
        isinstance(prediction.get(k), str) and prediction[k].strip()
        for k in ("run_id", "method_id")
    ):
        raise InputError("predictions: run and method identity required")
    if not isinstance(prediction.get("configuration"), dict) or prediction.get(
        "config_hash"
    ) != digest(prediction["configuration"]):
        raise InputError("predictions: configuration hash differs")
    if prediction.get("evidence_kind") not in {
        "matcher",
        "harness_oracle",
        "harness_wrong",
        "harness_missing",
        "harness_control",
    }:
        raise InputError("predictions: declare matcher versus harness-only evidence")
    cost = prediction.get("cost")
    fields = {
        "wall_seconds",
        "processed_audio_seconds",
        "storage_bytes",
        "peak_working_bytes_estimate",
    }
    if (
        not isinstance(cost, dict)
        or set(cost) != fields
        or any(not finite_number(v) or v < 0 for v in cost.values())
    ):
        raise InputError(
            "predictions: complete nonnegative measured cost/explicit memory estimate required"
        )
    if prediction.get("human_predictions"):
        raise InputError(
            "Grey1977 human scoring unavailable: unresolved rights and original mapping"
        )
    if split == "held_out" and prediction["evidence_kind"] == "matcher":
        if (
            not choice
            or any(
                choice.get(k) != prediction.get(k)
                for k in ("protocol_hash", "method_id", "config_hash")
            )
            or choice.get("selected_on") != "development"
            or choice.get("stage") != "A06"
        ):
            raise InputError(
                "held-out model scores reserved for A06; "
                "matching frozen development choice required"
            )


def score(prediction, protocol, suite, assets, split="development", choice=None):
    started = time.monotonic()
    validate_header(prediction, protocol, split, choice)
    if prediction.get("suite_hash") != suite["record_hash"]:
        raise InputError("predictions: stale suite/artifact hash")
    queries = {q["query_id"]: q for q in suite["queries"] if q["split"] == split}
    outputs = prediction.get("queries")
    if not isinstance(outputs, list) or len(outputs) > len(queries):
        raise InputError(
            "predictions: expected bounded query list; omitted queries are recorded misses"
        )
    provided = {}
    for output in outputs:
        key = output.get("query_id") if isinstance(output, dict) else None
        if (
            key not in queries
            or key in provided
            or set(output) != {"query_id", "candidate", "refined"}
        ):
            raise InputError("predictions: duplicate/unknown query or incomplete stage fields")
        query = queries[key]
        if any(a not in assets or assets[a]["split"] != split for a in query["candidate_assets"]):
            raise InputError("query: stale/cross-split asset identity")
        permitted = {a: assets[a] for a in query["candidate_assets"]}
        candidate = ranked(output["candidate"], prediction["score_direction"], permitted)
        refined = ranked(output["refined"], prediction["score_direction"], permitted)
        for r in refined:
            if not any(
                c["asset_id"] == r["asset_id"]
                and c["start_frame"] <= r["start_frame"]
                and r["end_frame"] <= c["end_frame"]
                for c in candidate
            ):
                raise InputError(
                    "refined prediction: interval was not contained in any supplied candidate"
                )
        provided[key] = {"candidate": candidate, "refined": refined}
    groups = {}
    for condition in sorted({q["condition"] for q in queries.values()}):
        selected = [q for q in queries.values() if q["condition"] == condition]
        present = [q for q in selected if q["targets"]]
        absent = [q for q in selected if not q["targets"]]
        group = {
            "queries": len(selected),
            "present_queries": len(present),
            "targets": sum(len(q["targets"]) for q in present),
            "missing_outputs": sum(q["query_id"] not in provided for q in selected),
            "absent_queries": len(absent),
            "stages": {},
        }
        for stage in ("candidate", "refined"):
            at_k = {}
            absent_scores = []
            absent_ranked_scores = []
            ranks = []
            margins = []
            for q in selected:
                ranked_list = provided.get(q["query_id"], {}).get(stage, [])
                first = next(
                    (i + 1 for i, p in enumerate(ranked_list) if event_matches([p], q["targets"])),
                    None,
                )
                if q["targets"]:
                    ranks.append(first)
                    if q["task"] == "controlled":
                        same = [
                            p["score"]
                            for p in ranked_list
                            if p["asset_id"] == q["targets"][0]["asset_id"]
                        ]
                        different = [
                            p["score"]
                            for p in ranked_list
                            if p["asset_id"] != q["targets"][0]["asset_id"]
                        ]
                        if same and different:
                            sign = 1 if prediction["score_direction"] == "higher_better" else -1
                            margins.append(
                                max(sign * s for s in same) - max(sign * s for s in different)
                            )
                else:
                    absent_scores.append(ranked_list[0]["score"] if ranked_list else None)
                    absent_ranked_scores.append(
                        [{"rank": i + 1, "score": p["score"]} for i, p in enumerate(ranked_list)]
                    )
            for k in protocol["k"]:
                hits, recovered = 0, 0
                errors = []
                for q in present:
                    prefix = provided.get(q["query_id"], {}).get(stage, [])[:k]
                    matches = event_matches(
                        prefix, q["targets"], protocol["matching"]["minimum_iou"]
                    )
                    hits += bool(matches)
                    recovered += len(matches)
                    for p, t, overlap in matches:
                        a, b = prefix[p], q["targets"][t]
                        rate = assets[b["asset_id"]]["audio"]["sample_rate_hz"]
                        errors.append(
                            {
                                "start_error_seconds": (a["start_frame"] - b["start_frame"]) / rate,
                                "end_error_seconds": (a["end_frame"] - b["end_frame"]) / rate,
                                "iou": overlap,
                            }
                        )
                at_k[str(k)] = {
                    "hit_queries": hits,
                    "query_denominator": len(present),
                    "hit_rate": hits / len(present) if present else None,
                    "recovered_targets": recovered,
                    "target_denominator": group["targets"],
                    "target_coverage": recovered / group["targets"] if group["targets"] else None,
                    "missed_targets": group["targets"] - recovered,
                    "conditional_localisation": errors,
                    "mean_absolute_boundary_error_seconds": float(
                        np.mean(
                            [
                                abs(e[field])
                                for e in errors
                                for field in ("start_error_seconds", "end_error_seconds")
                            ]
                        )
                    )
                    if errors
                    else None,
                }
            group["stages"][stage] = {
                "at_k": at_k,
                "first_target_ranks": ranks,
                "same_source_over_contrast_margins": margins,
                "absent_top_scores": absent_scores,
                "absent_scores_by_rank": absent_ranked_scores,
                "absent_ranks": "forced rankings do not establish presence",
                "false_accepts": None,
                "rejection_rule": "none fitted",
            }
        groups[condition] = group
    return {
        "status": "ok",
        "schema_version": "a04-scores-1",
        "protocol_hash": protocol["record_hash"],
        "run_id": prediction["run_id"],
        "method_id": prediction["method_id"],
        "config_hash": prediction["config_hash"],
        "split": split,
        "evidence_kind": prediction["evidence_kind"],
        "expected_queries": len(queries),
        "provided_queries": len(provided),
        "missing_queries": sorted(set(queries) - set(provided)),
        "conditions": groups,
        "human": {
            "Grey1977": {
                "rho": None,
                "usable_pairs": 0,
                "reason": "download inspection is not permission/alignment; "
                "dataset unavailable for scoring",
            }
        },
        "model_cost": prediction["cost"],
        "scoring_wall_seconds": time.monotonic() - started,
        "model_quality": "not_measured"
        if prediction["evidence_kind"].startswith("harness_")
        else "see separate metrics",
    }


def score_file(budget, prediction, split, choice=None):
    protocol, suite = load_suite(budget)
    assets = {}
    for key in suite["assets"]:
        value = record(budget.root / "manifests/evaluation/assets" / (key + ".json"))
        if value["record_hash"] != suite["asset_record_hashes"][key]:
            raise InputError("score: asset record differs from frozen suite")
        if value["split"] == split:
            _, value = load_asset(budget.root, key, budget)
        assets[key] = value
    return score(prediction, protocol, suite, assets, split, choice)


def known_answers(budget):
    protocol, suite = load_suite(budget)
    assets = {
        k: record(budget.root / "manifests/evaluation/assets" / (k + ".json"))
        for k in suite["assets"]
    }
    # Nontrivial permutations and average-rank ties have independently known answers.
    checks = {
        "perfect": signed_rank([30, 10, 40, 20], [3, 1, 4, 2]),
        "reversed": signed_rank([30, 10, 40, 20], [2, 4, 1, 3]),
        "ties": signed_rank([3, 1, 3, 2], [30, 10, 30, 20]),
        "constant": signed_rank([1, 2, 3], [4, 4, 4]),
    }
    if not (
        abs(checks["perfect"]["rho"] - 1) < 1e-12
        and abs(checks["reversed"]["rho"] + 1) < 1e-12
        and abs(checks["ties"]["rho"] - 1) < 1e-12
        and checks["constant"]["rho"] is None
    ):
        raise InputError("known answers: independent signed/tied rank checks failed")
    mask = np.triu(np.ones((3, 3), dtype=bool), 1)
    pairs = unique_pairs([[0, 0, 2], [0, 0, 3], [0, 0, 0]], mask, "upper_triangle")
    if len(pairs) != 3 or pairs[0][2] != 0:
        raise InputError("known answers: real zero/triangle denominator check failed")
    summaries = {}
    for kind in ("oracle", "wrong", "missing"):
        config = {"constructed_predictions": kind, "matcher": False}
        outputs = []
        for q in suite["queries"]:
            if q["split"] != "development" or kind == "missing":
                continue
            values = [{**t, "score": 1.0} for t in q["targets"]] if kind == "oracle" else []
            if kind == "wrong" or not q["targets"]:
                a = q["candidate_assets"][0]
                values = [{"asset_id": a, "start_frame": 0, "end_frame": 1, "score": -1.0}]
            # Also emit contrasts for controlled tests, at strictly worse oracle scores.
            if kind == "oracle" and q["task"] == "controlled":
                values += [
                    {
                        "asset_id": a,
                        "start_frame": 0,
                        "end_frame": assets[a]["audio"]["sample_count"],
                        "score": 0.0,
                    }
                    for a in q["candidate_assets"]
                    if a != q["targets"][0]["asset_id"]
                ]
            outputs.append({"query_id": q["query_id"], "candidate": values, "refined": values})
        prediction = {
            "schema_version": "a04-predictions-1",
            "protocol_hash": protocol["record_hash"],
            "suite_hash": suite["record_hash"],
            "run_id": "a04-known-" + kind,
            "method_id": "construction-truth-" + kind,
            "configuration": config,
            "config_hash": digest(config),
            "split": "development",
            "coordinate_basis": "decoded_available_file",
            "score_direction": "higher_better",
            "evidence_kind": "harness_" + kind,
            "queries": outputs,
            "cost": {
                "wall_seconds": 0,
                "processed_audio_seconds": 0,
                "storage_bytes": 0,
                "peak_working_bytes_estimate": 0,
            },
            "human_predictions": [],
        }
        path = budget.root / "data/runs/evaluation" / ("predictions-development-" + kind + ".json")
        write_record(path, prediction, budget)
        result = score(prediction, protocol, suite, assets)
        write_record(
            budget.root / "data/runs/evaluation" / ("scores-development-" + kind + ".json"),
            result,
            budget,
        )
        for group in result["conditions"].values():
            for stage in group["stages"].values():
                metrics = stage["at_k"]["10"]
                expected = metrics["target_denominator"] if kind == "oracle" else 0
                if metrics["recovered_targets"] != expected:
                    raise InputError(f"known answers {kind}: target denominator/recovery differs")
        summaries[kind] = {
            "queries": result["expected_queries"],
            "provided": result["provided_queries"],
            "recovered_at_10": sum(
                g["stages"]["candidate"]["at_k"]["10"]["recovered_targets"]
                for g in result["conditions"].values()
            ),
        }
    return {
        "status": "ok",
        "signed_ranks": checks,
        "runs": summaries,
        "evidence": "harness correctness only; no acoustic matcher or held-out model scores",
    }
