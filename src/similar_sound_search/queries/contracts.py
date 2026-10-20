"""Strict B03 identifiers, finite configuration and canonical recipe syntax."""

import re

from ..storage import InputError, digest, read_json

CAPS = {
    "job_seconds": 3600,
    "workers": 256,
    "http_attempts": 0,
    "download_bytes": 0,
    "read_audio_seconds": 90000,
    "feature_windows": 1024,
    "processed_window_seconds": 6000,
    "query_jobs": 16,
    "clips": 64,
    "clip_bytes": 64 * 1024**2,
    "managed_output_bytes": 256 * 1024**2,
    "processing_inputs": 32,
    "separator_input_seconds": 240,
    "pitch_audio_seconds": 3600,
    "query_preparation_bytes": 64 * 1024**2,
    "feature_bytes": 32 * 1024**2,
    "preparation_bytes": 96 * 1024**2,
    "metadata_bytes": 16 * 1024**2,
    "comparisons": 1,
    "comparison_cases": 16,
    "comparison_queries": 48,
}


def identifier(value, label="identifier"):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise InputError("B03 " + label + ": expected lowercase SHA256 identifier")
    return value


def fields(value, expected, label, optional=()):
    if (
        not isinstance(value, dict)
        or set(value) - set(expected) - set(optional)
        or set(expected) - set(value)
    ):
        raise InputError("B03 " + label + ": invalid/missing fields")
    return value


def configuration(root):
    cfg = read_json(root / "config/queries.json")
    fields(cfg, {"schema_version", "pitch", "policy"}, "configuration")
    if cfg["schema_version"] != "b03-queries-1":
        raise InputError("B03 configuration: unknown version")
    fields(cfg["policy"], {"max_" + k for k in CAPS}, "finite policy")
    for key, cap in CAPS.items():
        v = cfg["policy"]["max_" + key]
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= cap:
            raise InputError("B03 outer ceiling invalid: " + key)
    if cfg["pitch"] != {"version": "b03-pitch-1", "weight": 0.03, "scale_semitones": 12}:
        raise InputError("B03 fixed primary pitch policy changed; declare a new experiment")
    return cfg


def preference(value):
    fields(value, {"version", "weight", "scale_semitones"}, "pitch preference")
    if (
        value["version"] != "b03-pitch-1"
        or value["scale_semitones"] != 12
        or isinstance(value["weight"], bool)
        or value["weight"] not in (0, 0.03)
    ):
        raise InputError("B03 preference: use off or the predeclared .03 / 12-semitone policy")
    return value


def selection(value):
    fields(value, {"origin", "version", "complete", "uncertainty"}, "selection")
    if (
        not all(
            isinstance(value[k], str) and 0 < len(value[k]) <= 200 for k in ("origin", "version")
        )
        or not isinstance(value["complete"], bool)
        or not isinstance(value["uncertainty"], list)
        or len(value["uncertainty"]) > 16
        or any(not isinstance(v, str) or not 0 < len(v) <= 300 for v in value["uncertainty"])
    ):
        raise InputError("B03 selection: explicit origin/version/completeness/uncertainty required")
    return value


def canonical_examples(examples):
    if not isinstance(examples, list) or not 1 <= len(examples) <= 8:
        raise InputError("B03 recipe: one to eight explicit examples required")
    return [v for _, v in sorted({digest(v): v for v in examples}.items())]
