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
