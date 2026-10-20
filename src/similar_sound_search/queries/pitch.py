"""B03 estimate provenance/cache and bounded, separately inspectable pitch preference."""

import numpy as np

from ..evaluation.artifacts import record
from ..inputs import pcm_identity
from ..search.contracts import code_identity
from ..search.pitch import estimate, penalty
from ..storage import InputError, digest
from .contracts import preference


def estimate_identity(samples, rate):
    return {
        "version": "b03-pitch-estimate-1",
        "pcm": pcm_identity(samples, rate),
        "estimator_code": code_identity()["search/pitch.py"],
        "preprocessing": "unchanged waveform: arithmetic channel mean, resample_poly to 8000 Hz; "
        "whole selected support",
        "support_frames": len(samples),
        "native_rate": rate,
    }


def checked(value):
    hz = value.get("hz")
    if hz is not None and (
        isinstance(hz, bool) or not isinstance(hz, (int, float)) or not np.isfinite(hz) or hz <= 0
    ):
        raise InputError("B03 pitch: invalid nonfinite/nonpositive estimate")
    if not isinstance(value.get("reason"), str) or not isinstance(
        value.get("reliable_blocks"), int
    ):
        raise InputError("B03 pitch: missing abstention/estimator evidence")
    return value


def cached_estimate(budget, owner, samples, rate):
    identity = estimate_identity(samples, rate)
    path = owner.directory / "pitch" / (digest(identity) + ".json")
    if path.exists():
        value = record(path)
        if value["identity"] != identity:
            raise InputError("B03 pitch cache: changed PCM/support/estimator")
        return {**checked(value["estimate"]), "provenance": identity}
    owner.charge(budget, pitch_audio_seconds=len(samples) / rate)
    value = checked(estimate(samples, rate))
    owner.publish(budget, path, {"identity": identity, "estimate": value}, immutable=True)
    return {**value, "provenance": identity}


def contribution(queries, candidate, policy):
    policy = preference(policy)
    for value in [*queries, candidate]:
        checked(value)
    if not queries:
        raise InputError("B03 pitch: at least one query estimate required")
    missing_query = any(q["hz"] is None for q in queries)
    if policy["weight"] == 0:
        reason = "pitch preference off"
    elif missing_query:
        reason = "one or more required query estimates abstain; zero penalty for uncertainty"
    elif candidate["hz"] is None:
        reason = "candidate estimate abstains; zero penalty for uncertainty"
    else:
        reason = "mean clipped absolute semitone/register mismatch over unique PCM examples; "
        reason += "octaves not folded"
    differences = [
        None
        if q["hz"] is None or candidate["hz"] is None
        else float(abs(12 * np.log2(q["hz"] / candidate["hz"])))
        for q in queries
    ]
    # The one predeclared 12-semitone scale matches the unchanged legacy penalty.
    amount = penalty(queries, candidate, policy["weight"])
    if not 0 <= amount <= policy["weight"]:
        raise InputError("B03 pitch: contribution escaped its declared bound")
    return {
        "policy": policy,
        "value": amount,
        "reason": reason,
        "per_example_absolute_semitones": differences,
        "all_query_estimates_reliable": not missing_query,
        "different_query_notes": len(
            {round(12 * np.log2(q["hz"] / 440), 1) for q in queries if q["hz"] is not None}
        )
        > 1,
    }
