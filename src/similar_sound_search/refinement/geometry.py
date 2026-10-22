"""Finite native-frame local search, fixed objectives, ties and explicit lineage roles."""

import math

import numpy as np

from ..retrieval.fusion import intersects
from ..search.ranking import distances
from ..storage import InputError, digest


def positions(bounds, frames, rate, offsets):
    if (
        len(bounds) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) for v in (*bounds, frames, rate))
        or not 0 <= bounds[0] < bounds[1] <= frames
        or rate <= 0
        or len(offsets) > 9
        or 0 not in offsets
        or any(isinstance(v, bool) or not isinstance(v, int) or abs(v) > 500 for v in offsets)
    ):
        raise InputError("C03 local grid requires valid native support and at most nine offsets")
    width = bounds[1] - bounds[0]
    starts = set()
    for ms in offsets:
        shift = (abs(ms) * rate + 500) // 1000
        shift = -shift if ms < 0 else shift
        starts.add(max(0, min(frames - width, bounds[0] + shift)))
    return [[s, s + width] for s in sorted(starts)]


def objective(row, variants, events):
    if "variant_id" not in row:
        return {"kind": "mean", "variants": list(variants), "event": None}
    variant, event = row["variant_id"], row["event_id"]
    if variant not in variants or event not in events or variant not in events[event]:
        raise InputError("C03 anchor event/variant association differs")
    return {"kind": "variant", "variant": variant, "event": event}


def scores(features, array, obj, variants):
    per, means = distances(features, array, "cosine")
    if obj["kind"] == "mean":
        return per, means
    if obj["kind"] != "variant" or obj["variant"] not in variants:
        raise InputError("C03 objective incompatible with query examples")
    return per, per[variants.index(obj["variant"])]


def choose(bounds, values, original):
    if (
        len(bounds) != len(values)
        or original not in bounds
        or any(not math.isfinite(float(v)) for v in values)
    ):
        raise InputError("C03 finite scores and exact original control required")
    return min(
        range(len(bounds)),
        key=lambda i: (
            float(values[i]),
            bounds[i] != original,
            abs(bounds[i][0] - original[0]),
            bounds[i][0],
        ),
    )


def semantic(source, bounds, representation):
    return {
        "version": "c03-original-native-feature-1",
        "source_pcm": source["source"]["canonical_pcm"],
        "source_sha256": source["source"]["sha256"],
        "rate": source["source"]["sample_rate_hz"],
        "channels": source["source"]["channels"],
        "bounds": bounds,
        "representation": representation,
        "dimension": representation["dimension"],
    }


def lineage(candidate, query, cue=None):
    """Conditioning is a role, not candidate ancestry; candidate self-matches still fail."""
    from ..search.ranking import excluded_source

    if excluded_source(candidate, query):
        raise InputError("C03 candidate source is query ancestry or excluded duplicate group")
    if cue and candidate["source"]["canonical_pcm"] == cue["canonical_pcm"]:
        raise InputError("C03 cue audio cannot masquerade as candidate source")
    return {
        "candidate_source": digest(candidate),
        "conditioning_query": query["record_hash"],
        "conditioning_cue": None if cue is None else digest(cue),
        "method": "original-mixture",
        "processed_evidence": None,
    }


def overlaps(a, b):
    n = intersects(a, b)
    return {
        "overlap_frames": n,
        "iou": n / (max(a[1], b[1]) - min(a[0], b[0])),
        "contains": a[0] <= b[0] and a[1] >= b[1],
        "half_truth": n >= (b[1] - b[0]) / 2,
        "boundary_error_frames": [abs(a[0] - b[0]), abs(a[1] - b[1])],
    }


def deduplicate(anchors):
    """Anchored overlap: preserve every anchor result, label duplicate presentations only."""
    displayed = []
    for a in anchors:
        r = a["selected"]
        duplicate = next(
            (
                i
                for i, b in enumerate(displayed)
                if r["recording_id"] == b["recording_id"]
                and intersects(r["original_bounds"], b["original_bounds"])
                >= min(np.diff(r["original_bounds"])[0], np.diff(b["original_bounds"])[0]) * 0.5
            ),
            None,
        )
        a["presentation_duplicate_of"] = duplicate
        if duplicate is None:
            displayed.append(r)
    return anchors
