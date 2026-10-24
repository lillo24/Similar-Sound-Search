"""Read saved predictions, validate native contracts, then open isolated ground truth."""

import math
from collections import defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.evaluation.scoring import event_matches, iou
from similar_sound_search.processing.engine import load_scores
from similar_sound_search.search.contracts import grid
from similar_sound_search.storage import InputError, digest

from . import contracts, pipeline

CUTS = (1, 5, 10, 20)
ARMS = ("legacy-mean", "event-multi")


def interval(source, bounds):
    if (
        not isinstance(bounds, list)
        or len(bounds) != 2
        or any(isinstance(x, bool) or not isinstance(x, int) for x in bounds)
        or not 0 <= bounds[0] < bounds[1] <= source["source"]["sample_count"]
    ):
        raise InputError("D02 prediction: malformed/reversed/out-of-bounds native interval")
    return dict(asset_id=source["recording_id"], start_frame=bounds[0], end_frame=bounds[1])


def validate_prediction(owner, prediction):
    pop = contracts.population(owner)
    if (
        prediction["state"] != "complete"
        or prediction["population"] != pop["record_hash"]
        or prediction["protocol"] != owner.protocol["record_hash"]
        or prediction["split"] != owner.split
        or set(prediction["arms"]) != set(ARMS)
    ):
        raise InputError("D02 prediction incomplete or wrong paired population/protocol")
    sources = {s["recording_id"]: s for s in pop["sources"]}
    eligible = {s["group"] for s in sources.values()} - set(prediction["excluded_groups"])
    if len(eligible) < 24:
        raise InputError("D02 fewer than 24 distinct groups after ancestry exclusions")
    q = owner.get(prediction["query"], "queries")
    if q["query"]["record_hash"] != prediction["query_hash"]:
        raise InputError("D02 prediction/query binding differs")
    output = {}
    for arm in ARMS:
        published = prediction["arms"][arm]
        refs = published["complete_groups"]
        if (
            published["eligible_groups"] != len(eligible)
            or len(refs) != len(eligible)
            or published["shortlist"] != refs[:20]
            or published["display"] != refs[:10]
        ):
            raise InputError("D02 missing/partial complete ranking or shortlist binding")
        groups, seen, previous = [], set(), None
        for rank, ref in enumerate(refs, 1):
            g = owner.get(ref, "group-results")
            if g["group"] not in eligible or g["group"] in seen or g["rank"] != rank:
                raise InputError("D02 duplicate/unknown group or reversed/missing rank")
            seen.add(g["group"])
            score = g["score"]
            if (
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(score)
            ):
                raise InputError("D02 nonfinite prediction score")
            directed = score if arm == "legacy-mean" else -score
            if previous is not None and directed < previous:
                raise InputError("D02 score direction disagrees with rank")
            previous = directed
            passages, coordinates = [], set()
            if not g["passages"]:
                raise InputError("D02 group lacks a scored representative")
            for p in g["passages"]:
                row = p["representative"]
                if row["recording_id"] not in sources:
                    raise InputError("D02 representative source outside population")
                source = sources[row["recording_id"]]
                if source["group"] != g["group"] or p["scored_bounds"] != row["original_bounds"]:
                    raise InputError("D02 scored bounds differ from selected native row")
                actual = interval(source, p["scored_bounds"])
                interval(source, row["original_context"])
                key = (actual["asset_id"], actual["start_frame"], actual["end_frame"])
                if key in coordinates:
                    raise InputError("D02 duplicate scored representative")
                coordinates.add(key)
                passages.append(actual)
            groups.append(
                dict(
                    group=g["group"],
                    score=score,
                    passages=passages,
                    rank=rank,
                    grouping=g["grouping"],
                    support_truncated=g["support_truncated"],
                )
            )
        if seen != eligible:
            raise InputError("D02 eligible paired population differs")
        output[arm] = groups
    return output


def coverage_matches(predictions, targets, minimum=0.5):
    if not predictions or not targets:
        return []
    overlap = np.array(
        [
            [
                max(
                    0, min(p["end_frame"], t["end_frame"]) - max(p["start_frame"], t["start_frame"])
                )
                / (t["end_frame"] - t["start_frame"])
                if p["asset_id"] == t["asset_id"]
                else 0
                for t in targets
            ]
            for p in predictions
        ]
    )
    valid = overlap >= minimum
    weights = valid + np.where(valid, overlap, 0) / (min(overlap.shape) + 1)
    a, b = linear_sum_assignment(-weights)
    return [
        (int(x), int(y), float(overlap[x, y])) for x, y in zip(a, b, strict=True) if valid[x, y]
    ]


def case_metrics(groups, truth):
    targets = [
        dict(asset_id=e["recording_id"], start_frame=e["bounds"][0], end_frame=e["bounds"][1])
        for e in truth["events"]
    ]
    positives = set(truth["positive_groups"])
    rates = {e["recording_id"]: e["rate"] for e in truth["events"]}
    output = {}
    for k in CUTS:
        recovered = positives & {g["group"] for g in groups[:k]}
        predictions = [p for g in groups[:k] for p in g["passages"]]
        matches = event_matches(predictions, targets, 0.5)
        coverage = coverage_matches(predictions, targets)
        matched = {m[1] for m in matches}
        errors = []
        for a, b, value in matches:
            p, t = predictions[a], targets[b]
            intersection = max(
                0, min(p["end_frame"], t["end_frame"]) - max(p["start_frame"], t["start_frame"])
            )
            errors.append(
                dict(
                    prediction=p,
                    target_index=b,
                    iou=value,
                    truth_coverage=intersection / (t["end_frame"] - t["start_frame"]),
                    prediction_containment=intersection / (p["end_frame"] - p["start_frame"]),
                    start_error_seconds=(p["start_frame"] - t["start_frame"])
                    / rates[t["asset_id"]],
                    end_error_seconds=(p["end_frame"] - t["end_frame"]) / rates[t["asset_id"]],
                )
            )
        output[str(k)] = dict(
            query_hit=bool(recovered),
            recovered_positive_groups=sorted(recovered),
            positive_groups=len(positives),
            all_positive_group_recall=len(recovered) / len(positives) if positives else None,
            targets=len(targets),
            matched_events=len(matches),
            event_recall=len(matches) / len(targets) if targets else None,
            truth_coverage_recall=len(coverage) / len(targets) if targets else None,
            misses=[i for i in range(len(targets)) if i not in matched],
            matched=errors,
        )
    return output


def attribution(owner, prediction, groups, truth):
    """For every @20 IoU miss: group rank, grid reachability, retained supports, scorer."""
    sources = {s["recording_id"]: s for s in contracts.population(owner)["sources"]}
    retained = {}
    for rid, ref in prediction["scores"].items():
        raw = load_scores(owner, ref)
        retained[rid] = [r["bounds"] for b in raw["banks"] for row in b["supports"] for r in row]
    predictions = [p for g in groups[:20] for p in g["passages"]]
    targets = [
        dict(asset_id=e["recording_id"], start_frame=e["bounds"][0], end_frame=e["bounds"][1])
        for e in truth["events"]
    ]
    matched = {v[1] for v in event_matches(predictions, targets)}
    ranks = {g["group"]: g["rank"] for g in groups}
    losses = []
    for i, e in enumerate(truth["events"]):
        if i in matched:
            continue
        s = sources[e["recording_id"]]
        all_bounds = {
            tuple(b)
            for bank in owner.protocol["banks"]
            for b in grid(s["source"]["sample_count"], e["rate"], bank)
        }
        reachable = any(iou(interval(s, list(b)), targets[i]) >= 0.5 for b in all_bounds)
        retained_hit = any(
            iou(interval(s, b), targets[i]) >= 0.5 for b in retained[s["recording_id"]]
        )
        rank = ranks.get(e["group"])
        reason = (
            "eligible-positive-group-missing"
            if rank is None
            else "group-rank-cut"
            if rank > 20
            else "native-grid-unreachable"
            if not reachable
            else "retained-support-cap-or-window-scoring"
            if not retained_hit
            else "representative-selection-or-passage-cap"
        )
        losses.append(
            dict(
                target_index=i,
                group=e["group"],
                rank=rank,
                grid_reachable=reachable,
                retained_iou_support=retained_hit,
                reason=reason,
            )
        )
    return losses


def ordering_controls(groups, truth, case_id):
    stable = sorted(groups, key=lambda g: g["group"])
    rng = np.random.default_rng(int(digest([882711, case_id])[:16], 16))
    random = [stable[i] for i in rng.permutation(len(stable))]
    return {
        name: {
            str(k): dict(
                query_hit=bool(set(truth["positive_groups"]) & {g["group"] for g in items[:k]}),
                all_positive_group_recall=len(
                    set(truth["positive_groups"]) & {g["group"] for g in items[:k]}
                )
                / len(truth["positive_groups"])
                if truth["positive_groups"]
                else None,
            )
            for k in CUTS
        }
        for name, items in (("constant-tie-group-id", stable), ("seeded-random-order", random))
    }


def macro(cases, arm, k, field):
    """Equal weight per present (known-positive family, query-condition) cell.

    A distinct-event query contributes to both declared character cells. Within a
    cell, whole-query metrics are averaged; no family re-labelling after scoring.
    """
    cells = defaultdict(list)
    for c in cases:
        if not c["primary"]:
            continue
        for family in c["families"]:
            cells[(family, str(c["condition"]))].append(float(c["arms"][arm][str(k)][field]))
    return sum(sum(v) / len(v) for v in cells.values()) / len(cells) if cells else None


def gate(cases, valid=True):
    loss = []
    for c in cases:
        if c["primary"]:
            before = set(c["arms"][ARMS[0]]["20"]["recovered_positive_groups"])
            after = set(c["arms"][ARMS[1]]["20"]["recovered_positive_groups"])
            if before - after:
                loss.append(dict(case_id=c["case_id"], newly_lost_groups=sorted(before - after)))
    b = [macro(cases, ARMS[0], 1, "query_hit"), macro(cases, ARMS[0], 10, "event_recall")]
    a = [macro(cases, ARMS[1], 1, "query_hit"), macro(cases, ARMS[1], 10, "event_recall")]
    passes = (
        valid
        and all(x is not None and y is not None and x >= y for x, y in zip(a, b, strict=True))
        and any(x > y for x, y in zip(a, b, strict=True))
        and not loss
    )
    return dict(
        passed=passes,
        valid=valid,
        baseline=dict(macro_group_hit_1=b[0], macro_iou_event_recall_10=b[1]),
        candidate=dict(macro_group_hit_1=a[0], macro_iou_event_recall_10=a[1]),
        coverage_regressions=loss,
        decision="qualifies on this split" if passes else "retain baseline; paired gate not met",
    )


def score(budget, owner):
    # Validate all declared saved predictions before opening any private truth.
    declared = contracts.inputs(owner)["queries"]
    predictions = {c["case_id"]: pipeline.saved_prediction(owner, c["case_id"]) for c in declared}
    rankings = {key: validate_prediction(owner, v) for key, v in predictions.items()}
    truth = record(owner.directory / "truth" / (owner.split + ".json"))
    if {c["case_id"] for c in truth["cases"]} != set(predictions):
        raise InputError("D02 truth/prediction matrix differs; no denominator may disappear")
    output = []
    for t in truth["cases"]:
        key = t["case_id"]
        pop = contracts.population(owner)
        expected = set(t.get("excluded_candidate_groups", []))
        actual = set(predictions[key]["excluded_groups"]) & {s["group"] for s in pop["sources"]}
        if actual != expected:
            raise InputError(
                "D02 exact-instance/PCM ancestry exclusion differs from independent truth"
            )
        g = rankings[key]
        output.append(
            dict(
                **t,
                arms={arm: case_metrics(g[arm], t) for arm in ARMS},
                attribution={arm: attribution(owner, predictions[key], g[arm], t) for arm in ARMS},
                controls=ordering_controls(g[ARMS[0]], t, key),
                forced_rank_scores={arm: [v["score"] for v in g[arm]] for arm in ARMS},
                prediction_hash=predictions[key]["record_hash"],
                eligible_groups=len(g[ARMS[0]]),
            )
        )
    resources = owner.pool()
    valid = all(resources["counts"][k] <= cap for k, cap in resources["ceilings"].items())
    summary = {
        arm: {
            str(k): dict(
                query_hit=macro(output, arm, k, "query_hit"),
                all_positive_group_recall=macro(output, arm, k, "all_positive_group_recall"),
                iou_event_recall=macro(output, arm, k, "event_recall"),
                truth_coverage_recall=macro(output, arm, k, "truth_coverage_recall"),
            )
            for k in CUTS
        }
        for arm in ARMS
    }
    value = dict(
        schema_version="d02-scores-1",
        split=owner.split,
        state="complete",
        protocol=owner.protocol["record_hash"],
        consumer=contracts.consumer(owner),
        truth=truth["record_hash"],
        cases=output,
        summary=summary,
        gate=gate(output, valid),
        primary_queries=sum(t["primary"] for t in output),
        declared_queries=len(declared),
        interpretation=(
            "Prospective confirmation within familiar A04 mechanisms; no unseen-m"
            "usic/human timbre inference"
        ),
        absent_target="Forced-rank score observations only; no rejection threshold or calibration",
        uncertainty=(
            "Descriptive paired construction families; no independence CI or human validation"
        ),
    )
    ref = owner.put(budget, "assessments", value)
    owner.publish(
        budget,
        owner.directory / "scores" / (owner.split + "-summary.json"),
        dict(assessment=ref),
        immutable=True,
    )
    return dict(assessment=ref, summary=summary, gate=value["gate"])
