"""Independent native delivery checks, under the same finite D01 owner."""

import numpy as np

from ..inputs import decode
from ..search import sources
from ..storage import InputError
from . import api, media


def native(budget, owner, spec):
    result = api.result(owner.root, spec["job_id"])
    population = {s["recording_id"]: s for s in result["population"]}
    checks = []
    for card in result["cards"][spec["start"] : spec["start"] + 2]:
        passage = card["passages"][0]
        source = population[passage["row"]["recording_id"]]
        original = sources.load(budget, source, context=owner)
        for key in ("scored", "context"):
            path, saved = media.validate(owner, passage[key]["record_hash"])
            owner.charge(budget, read_audio_seconds=saved["clip"]["duration_seconds"])
            actual, meta = decode(path, budget)
            a, b = saved["bounds"]
            crop = original[a:b].astype(np.float64)
            peak = float(np.max(np.abs(crop)))
            gain = min(1.0, (32767 / 32768) / peak) if peak else 1.0
            expected = np.rint(crop * gain * 32768).astype(np.int16).astype(np.float32) / 32768
            if (
                not np.array_equal(expected, actual)
                or gain != saved["clip"]["gain"]
                or meta["sample_count"] != b - a
                or meta["sample_rate_hz"] != source["source"]["sample_rate_hz"]
                or meta["channels"] != source["source"]["channels"]
            ):
                raise InputError(
                    "D01 independent native crop/channel/gain/frame verification failed"
                )
            checks.append(
                dict(
                    group=card["group"],
                    kind=key,
                    media=passage[key]["record_hash"],
                    bounds=[a, b],
                    frames=b - a,
                    rate=meta["sample_rate_hz"],
                    channels=meta["channels"],
                    samples_exact=True,
                    gain=gain,
                )
            )
    return dict(passed=True, job_id=spec["job_id"], checks=checks)


def finalization(budget, owner, key):
    """Resume metadata/media finalization after scores/aggregation already committed.

    Source bytes are freshly hashed and charged at full-source duration. Exact bytes,
    unchanged decoder/representation and the prior full PCM audits establish the same
    PCM without re-decoding unrelated songs. Every candidate array is reopened and
    hash/native-validated. This is distinct from a warm search's full sequential reads.
    """
    from ..processing import cache
    from ..processing import job as historical_job
    from ..storage import contained, sha256
    from . import history, job

    old, plan, state = history.inputs(owner)
    proofs = []
    for source in plan["input"]["sources"]:
        rid = source["recording_id"]
        previous = job.committed(owner, key, "source:" + rid)
        adoption = owner.get(previous["proof"], "adoptions")
        if adoption["source"] != source or not adoption["source_pcm_verified"]:
            raise InputError("D01 recovery lacks prior full source/PCM audit")
        owner.charge(budget, read_audio_seconds=source["source"]["duration_seconds"])
        path = contained(owner.root / source["source"]["local_path"], owner.root)
        if sha256(path, budget) != source["source"]["sha256"]:
            raise InputError(
                "D01 finalization source bytes changed; existing scores cannot be published"
            )
        unit = next(u for u in plan["units"] if u["kind"] == "features" and u["subject"] == rid)
        features = historical_job.output(old, state, unit)
        cache.vectors(budget, old, features["rows"])
        proofs.append(
            dict(
                source=rid,
                prior=previous["proof"],
                rows=len(features["rows"]),
                source_bytes_verified=True,
            )
        )
    return owner.put(
        budget,
        "finalization-audits",
        dict(
            job_id=key,
            consumer=history.consumer(owner),
            sources=proofs,
            source_pcm="prior full sequential audit, unchanged exact bytes/decoder",
            arrays_reopened=True,
            new_encodes=0,
            scope="committed aggregation to final media/publication only",
        ),
    )
