"""Truth-independent sample grids and opaque waveform routing."""

from ..evaluation.protocol import INTERVAL_POLICY
from ..storage import InputError, digest

POLICY = INTERVAL_POLICY


def intervals(frames, query_frames, rate, controlled=False):
    if any(
        isinstance(v, bool) or not isinstance(v, int) or v <= 0
        for v in (frames, query_frames, rate)
    ):
        raise InputError("window grid: positive integer frame counts/rate required")
    if controlled:
        return [(0, frames)]
    if frames < query_frames or rate % 4:
        raise InputError(
            "window grid: candidate shorter than query or non-integral quarter-second hop"
        )
    starts = list(range(0, frames - query_frames + 1, rate // 4))
    if starts[-1] != frames - query_frames:
        starts.append(frames - query_frames)
    return [(s, s + query_frames) for s in starts]


def routes(suite, assets, split="development"):
    """Return only routing identity, sample metadata and bounds; never construction labels."""
    if split not in {"development", "held_out"}:
        raise InputError("routing: explicit development/held_out split required")
    result, queries = {}, []
    for q in suite["queries"]:
        if q["split"] != split:
            continue
        query = assets[q["query_asset_id"]]
        meta = query["audio"]
        query_key = add_route(result, query, 0, meta["sample_count"])
        pool = []
        for key in q["candidate_assets"]:
            a = assets[key]
            if a["split"] != split or a["audio"]["sample_rate_hz"] != meta["sample_rate_hz"]:
                raise InputError("routing: same-split assets with equal source rate required")
            # Whole-file mode follows candidate duration, not target truth or task labels.
            for start, end in intervals(
                a["audio"]["sample_count"],
                meta["sample_count"],
                meta["sample_rate_hz"],
                a["audio"]["sample_count"] == meta["sample_count"],
            ):
                route = add_route(result, a, start, end)
                pool.append(
                    {"route": route, "asset_id": key, "start_frame": start, "end_frame": end}
                )
        if len(pool) > 128:
            raise InputError("routing: prediction stage exceeds 128 intervals")
        queries.append({"query_id": q["query_id"], "query_route": query_key, "pool": pool})
    return result, queries


def add_route(result, asset, start, end):
    value = {
        "asset_id": asset["asset_id"],
        "sha256": asset["audio"]["sha256"],
        "pcm": asset["audio"]["canonical_pcm"],
        "sample_rate_hz": asset["audio"]["sample_rate_hz"],
        "start_frame": start,
        "end_frame": end,
    }
    key = digest(value)
    result[key] = value
    return key
