"""Evaluation-only aligned signal diagnostics; never supplied to processing or routing."""

import numpy as np

from ..storage import InputError


def preservation(output, target, mixture, rate):
    y, t, m = (np.asarray(v, dtype=float).reshape(-1) for v in (output, target, mixture))
    if y.shape != t.shape or t.shape != m.shape or not np.isfinite(y).all():
        raise InputError("B02 preservation: aligned finite equal-support signals required")
    energy = float(t @ t)
    if energy <= 1e-20:
        return {
            "state": "target-absent",
            "output_rms": float(np.sqrt(np.mean(y * y))),
            "presence_detection": False,
        }

    def sdr(v):
        error = float((v - t) @ (v - t))
        return float(10 * np.log10(energy / max(error, 1e-30)))

    def projected_retention(v, truth):
        power = float(truth @ truth)
        return float(v @ truth / power) if power > 1e-20 else None

    background = m - t
    design = np.column_stack((t, background))
    coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
    alpha = float(y @ t / energy)
    projected = alpha * t
    si_sdr = float(
        10
        * np.log10(
            max(float(projected @ projected), 1e-30)
            / max(float((y - projected) @ (y - projected)), 1e-30)
        )
    )
    attack = min(len(y), int(0.025 * rate))
    tail = min(len(y), int(0.2 * rate))
    return {
        "state": "aligned-exact-component-evaluation",
        "sdr_db": sdr(y),
        "sdr_improvement_db": sdr(y) - sdr(m),
        "si_sdr_db": si_sdr,
        "target_gain_projection": float(coefficients[0]),
        "background_leakage_projection": float(coefficients[1]),
        "attack_projection": projected_retention(y[:attack], t[:attack]),
        "tail_projection": projected_retention(y[-tail:], t[-tail:]),
        "overload_samples": int(np.count_nonzero(np.abs(y) > 1)),
        "delay_frames": 0,
        "fit_note": "projection diagnostics only; raw samples/gain/timing unchanged; "
        "no fitted shift",
    }


def outcome(hits, truth):
    return {
        "abstained": not hits,
        "hit_at": {
            str(k): bool(set(h["asset_id"] for h in hits[:k]) & set(truth)) for k in (1, 5, 10)
        },
        "recovery_at": {
            str(k): sum(v in {h["asset_id"] for h in hits[:k]} for v in truth) for k in (1, 5, 10)
        },
        "truth_events": len(truth),
        "forced_ranking_is_presence_detection": False,
    }
