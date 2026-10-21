"""Pure deterministic rank fusion and representative-anchored support consolidation."""

import math

from ..storage import InputError, digest


def row_key(row):
    return (row["distance"], row["recording_id"], *row["original_bounds"], row["row_id"])


def retain(rows, cap):
    unique = {}
    for row in rows:
        if not math.isfinite(row["distance"]):
            raise InputError("C02 support distance is nonfinite")
        key = row["row_id"]
        if key in unique and unique[key] != row:
            raise InputError("C02 conflicting same-row evidence")
        unique[key] = row
    return sorted(unique.values(), key=row_key)[:cap]


def events(examples, association=None):
    """Unique PCM examples are events; only a validated witness may group variants."""
    ids = sorted(set(examples))
    if not ids or len(ids) > 8:
        raise InputError("C02 requires one to eight unique examples")
    if association is None:
        return {v: [v] for v in ids}
    if set(association) != set(ids):
        raise InputError("C02 association must cover exactly every unique example")
    grouped = {}
    for key in ids:
        witness = association[key]
        if not isinstance(witness, dict) or set(witness) != {"source_pcm", "native_bounds", "rate"}:
            raise InputError("C02 same-event association requires native parent witness")
        a, b = witness["native_bounds"]
        if (
            any(isinstance(v, bool) or not isinstance(v, int) for v in (a, b, witness["rate"]))
            or not 0 <= a < b
            or witness["rate"] <= 0
        ):
            raise InputError("C02 association has invalid native support")
        grouped.setdefault(digest(witness), []).append(key)
    return dict(sorted(grouped.items()))


def intersects(a, b):
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def consolidate(rows, cfg):
    # A row may support several events; retain each contribution, but use one anchor.
    def order(r):
        return -r["credit"], r["bank_hash"], *row_key(r), r["variant_id"]

    ordered = sorted({digest(r): r for r in rows}.values(), key=order)
    clusters = []
    for row in ordered:
        a = row["original_bounds"]
        match = None
        for cluster in clusters:
            anchor = cluster["representative"]
            b = anchor["original_bounds"]
            envelope = [
                min(a[0], cluster["display_envelope"][0]),
                max(a[1], cluster["display_envelope"][1]),
            ]
            if (
                row["recording_id"] == anchor["recording_id"]
                and row["rate"] == anchor["rate"]
                and intersects(a, b) > 0
                and intersects(a, b) / min(a[1] - a[0], b[1] - b[0]) >= cfg["overlap_fraction"]
                and envelope[1] - envelope[0] <= cfg["max_span_seconds"] * row["rate"]
            ):
                match = cluster
                break
        if match is None:
            clusters.append(
                {
                    "representative": row,
                    "scored_bounds": a,
                    "display_envelope": list(a),
                    "supports": [row],
                    "envelope_is_scored": False,
                }
            )
        else:
            match["supports"].append(row)
            match["display_envelope"] = [
                min(match["display_envelope"][0], a[0]),
                max(match["display_envelope"][1], a[1]),
            ]
    selected = []
    for c in clusters:
        r = c["representative"]
        if any(
            r["recording_id"] == v["representative"]["recording_id"]
            and intersects(r["original_bounds"], v["scored_bounds"]) > 0
            for v in selected
        ):
            continue
        selected.append(c)
        if len(selected) == cfg["passages_per_track"]:
            break
    return selected, {
        "raw_retained": len(ordered),
        "clusters": len(clusters),
        "display_passages": len(selected),
        "discarded_clusters": len(clusters) - len(selected),
    }


def results(groups, event_map, bank_hashes, cfg, arm):
    bank_hashes = sorted(set(bank_hashes))
    if arm not in {"legacy-mean", "event-legacy", "event-multi"}:
        raise InputError("C02 unknown retrieval arm")
    if not groups:
        return []
    legacy = next(iter(groups.values()))["baseline_row"]["bank_hash"]
    if legacy not in bank_hashes:
        raise InputError("C02 baseline bank is absent")
    chosen = bank_hashes if arm == "event-multi" else [legacy]
    ranks = {}
    for bank in chosen:
        for variant in sorted({v for values in event_map.values() for v in values}):
            key = bank + ":" + variant
            eligible = [
                (g, v["objectives"][key]["rows"][0])
                for g, v in groups.items()
                if key in v["objectives"]
            ]
            if len(eligible) != len(groups):
                raise InputError("C02 primary fusion has missing per-group bank/variant support")
            for rank, (g, _) in enumerate(
                sorted(eligible, key=lambda p: (*row_key(p[1]), p[0])), 1
            ):
                ranks[(key, g)] = rank
    output = []
    for group, value in sorted(groups.items()):
        contributions = []
        supported = []
        for event, variants in sorted(event_map.items()):
            credits = []
            for bank in chosen:
                alternatives = []
                for variant in sorted(set(variants)):
                    key = bank + ":" + variant
                    rank = ranks[(key, group)]
                    credit = (cfg["rrf_constant"] + 1) / (cfg["rrf_constant"] + rank)
                    objective = value["objectives"][key]
                    alternatives.append((credit, variant, rank, objective))
                    supported.extend(
                        {**r, "credit": credit, "event_id": event, "variant_id": variant}
                        for r in objective["rows"]
                    )
                best = sorted(alternatives, key=lambda x: (-x[0], x[1]))[0]
                credits.append(best[0])
                contributions.append(
                    {
                        "event_id": event,
                        "bank_hash": bank,
                        "variant_id": best[1],
                        "rank": best[2],
                        "eligible_groups": len(groups),
                        "credit": best[0],
                        "best_row": best[3]["rows"][0]["row_id"],
                    }
                )
            contributions.append({"event_id": event, "event_credit": sum(credits) / len(credits)})
        event_scores = [v["event_credit"] for v in contributions if "event_credit" in v]
        score = (max(event_scores) + sum(event_scores) / len(event_scores)) / 2
        if arm == "legacy-mean":
            score = value["baseline"]["timbre_distance"]
            row = value["baseline_row"]
            passages = [
                {
                    "representative": row,
                    "scored_bounds": row["original_bounds"],
                    "display_envelope": row["original_bounds"],
                    "supports": [row],
                    "envelope_is_scored": False,
                }
            ]
            grouping = {
                "raw_retained": 1,
                "clusters": 1,
                "display_passages": 1,
                "discarded_clusters": 0,
            }
            contributions = []
        else:
            passages, grouping = consolidate(supported, cfg)
        output.append(
            {
                "group": group,
                "score": score,
                "contributions": contributions,
                "passages": passages,
                "grouping": grouping,
                "support_cap": cfg["raw_support_cap"],
                "support_truncated": any(
                    v["count"] > len(v["rows"])
                    for k, v in value["objectives"].items()
                    if k.split(":")[0] in chosen
                ),
                "opportunities": value["opportunities"],
            }
        )
    if arm == "legacy-mean":
        return sorted(
            output,
            key=lambda v: (
                v["score"],
                groups[v["group"]]["baseline"]["recording_id"],
                groups[v["group"]]["baseline"]["start_frame"],
                groups[v["group"]]["baseline"]["end_frame"],
            ),
        )
    return sorted(output, key=lambda v: (-v["score"], v["group"]))
