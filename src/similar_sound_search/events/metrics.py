"""Note-boundary evaluation, separate from unchanged A04 full-render retrieval truth."""

import numpy as np
from scipy.optimize import linear_sum_assignment

from ..storage import InputError


def reference_notes(reference, tone, first, last):
    """Compose actual insertion offsets; keep full releases beyond a selected edge.

    Only notes overlapping the authorized region are evaluation targets. A mixture
    with a later insertion can contain no designated target in the selected region.
    These bounds are evaluation-only and never passed to the proposer/selector.
    """
    meta = reference["audio"]
    if not 0 <= first < last <= meta["sample_count"]:
        raise InputError("event truth: selected region outside reference " + reference["asset_id"])
    if tone is None:
        return []
    if tone["audio"]["sample_rate_hz"] != meta["sample_rate_hz"]:
        raise InputError("event truth: native rates differ for " + reference["asset_id"])
    length = tone["audio"]["sample_count"]
    if reference["asset_id"] == tone["asset_id"]:
        insertions = [[0, length]]
    else:
        if reference["identity"]["recipe"].get("target_asset") != tone["asset_id"]:
            raise InputError(
                "event truth: reference target identity differs: " + reference["asset_id"]
            )
        insertions = reference["insertions"]
    result = []
    for insertion, (a, b) in enumerate(insertions):
        if b - a != length or not 0 <= a < b <= meta["sample_count"]:
            raise InputError(
                "event truth: insertion length/bounds differ: " + reference["asset_id"]
            )
        for i, note in enumerate(tone["events"]):
            start, end = a + note["start_frame"], a + note["end_frame"]
            if not a <= start < end <= b:
                raise InputError("event truth: note outside complete inserted render")
            if start < last and end > first:
                result.append(
                    {
                        "start_frame": start,
                        "end_frame": end,
                        "insertion_index": insertion,
                        "note_index": i,
                        "selection_start_censored": start < first,
                        "selection_end_censored": end > last,
                    }
                )
    return result


def boundaries(proposals, truth, rate, settings):
    pairs = []
    if proposals and truth:
        errors = np.array(
            [
                [
                    [
                        abs(p["start_frame"] - t["start_frame"]) / rate,
                        abs(p["end_frame"] - t["end_frame"]) / rate,
                    ]
                    for t in truth
                ]
                for p in proposals
            ]
        )
        valid = (errors[:, :, 0] <= settings["onset_tolerance_seconds"]) & (
            errors[:, :, 1] <= settings["offset_tolerance_seconds"]
        )
        # Maximum valid cardinality dominates the boundary-error tie-break.
        costs = np.where(valid, errors.sum(axis=2), 1e6)
        rows, columns = linear_sum_assignment(costs)
        for i, j in zip(rows, columns, strict=True):
            if not valid[i, j]:
                continue
            p, t = proposals[i], truth[j]
            attack_end = min(t["end_frame"], t["start_frame"] + round(0.025 * rate))
            tail_start = max(t["start_frame"], t["end_frame"] - round(0.2 * rate))

            def coverage(first, last):
                return max(0, min(last, p["end_frame"]) - max(first, p["start_frame"])) / (
                    last - first
                )

            pairs.append(
                {
                    "proposal": int(i),
                    "truth": int(j),
                    "onset_error_seconds": (p["start_frame"] - t["start_frame"]) / rate,
                    "release_error_seconds": (p["end_frame"] - t["end_frame"]) / rate,
                    "attack_coverage": coverage(t["start_frame"], attack_end),
                    "tail_coverage": coverage(tail_start, t["end_frame"]),
                }
            )
    matched = {v["proposal"] for v in pairs}
    # These are explicit structural diagnostics, not extra true-positive credits.
    splits = sum(
        i not in matched
        and any(t["start_frame"] < p["onset_frame"] < t["end_frame"] for t in truth)
        for i, p in enumerate(proposals)
    )
    merges = sum(
        sum(
            p["start_frame"] <= t["start_frame"] and p["end_frame"] >= t["end_frame"] for t in truth
        )
        >= 2
        for p in proposals
    )
    return {
        "proposals": len(proposals),
        "truth_events": len(truth),
        "matched": len(pairs),
        "precision": len(pairs) / len(proposals) if proposals else None,
        "recall": len(pairs) / len(truth) if truth else None,
        "missed_events": len(truth) - len(pairs),
        "false_or_unresolved_proposals": len(proposals) - len(pairs),
        "split_candidates": splits,
        "merged_spans": merges,
        "boundary_truncated": sum(any("censored" in f for f in p["flags"]) for p in proposals),
        "pairs": pairs,
    }


def aggregate(values):
    total = {
        k: sum(v[k] for v in values)
        for k in (
            "proposals",
            "truth_events",
            "matched",
            "missed_events",
            "false_or_unresolved_proposals",
            "split_candidates",
            "merged_spans",
            "boundary_truncated",
        )
    }
    total["precision"] = total["matched"] / total["proposals"] if total["proposals"] else None
    total["recall"] = total["matched"] / total["truth_events"] if total["truth_events"] else None
    pairs = [p for v in values for p in v["pairs"]]
    for key in ("onset_error_seconds", "release_error_seconds"):
        total["mean_absolute_" + key] = (
            float(np.mean([abs(p[key]) for p in pairs])) if pairs else None
        )
    for key in ("attack_coverage", "tail_coverage"):
        total["minimum_matched_" + key] = min((p[key] for p in pairs), default=None)
    total["empty_inputs"] = sum(v["proposals"] == 0 for v in values)
    return total
