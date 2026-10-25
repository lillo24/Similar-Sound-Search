"""The one authorized allocation, divided into fixed verification and normal shares."""

from similar_sound_search.application.context import CEILINGS as BASE
from similar_sound_search.resources import load_limits

MIB = 1024**2
SHARE = {
    **BASE,
    "feature_windows": 512,
    "metadata_bytes": 256 * MIB,
}
TOTAL = {k: 2 * v for k, v in SHARE.items()}
PROTECTED = 32 * MIB
SEARCH = dict(job_seconds=1200, workers=128, read_audio_seconds=30000)


def limits(root):
    return {
        **load_limits(root / "config/resource_limits.json", "starter"),
        "max_download_bytes": 0,
        "max_model_candidates": 0,
    }


def estimate(kind, examples=2):
    """Conservative whole-request bounds, including protected terminal capacity.

    Search reserves 96 MiB ordinary publication plus a 12 MiB protected margin;
    both arms are computed, only the selected arm's ten cards generate clips.
    Source validation remains charged despite cached candidate features.
    """
    if not 1 <= examples <= 8:
        raise ValueError("D03 requires one to eight original examples")
    if kind in {"search", "validate"}:
        return dict(
            **SEARCH,
            query_jobs=2,
            metadata_bytes=108 * MIB,
            feature_windows=examples,
            processed_window_seconds=examples * 30,
            feature_bytes=examples * 131072,
            preparation_bytes=32 * MIB,
            import_bytes=0,
            clips=20,
            clip_bytes=40 * MIB,
            managed_output_bytes=80 * MIB,
            ordinary_bytes=96 * MIB,
        )
    return dict(
        job_seconds=120,
        workers=2,
        read_audio_seconds=10000 if kind == "native-qa" else 1800,
        query_jobs=1,
        metadata_bytes=4 * MIB,
        feature_windows=0,
        processed_window_seconds=0,
        feature_bytes=0,
        preparation_bytes=4 * MIB,
        import_bytes=128 * MIB if kind == "upload" else 0,
        clips=1 if kind == "preview" else 0,
        clip_bytes=16 * MIB if kind == "preview" else 0,
        managed_output_bytes=144 * MIB if kind == "upload" else 20 * MIB,
        ordinary_bytes=3 * MIB,
    )
