"""Deterministic native-frame channel-safe envelope/flux proposals; no truth or scores."""

import numpy as np
from scipy.signal import find_peaks

from ..storage import InputError, digest


def propose(samples, rate, first, last, cfg):
    """Analyse only [first,last). A release is never inferred from the next attack.

    Twenty-ms centred frames and five-ms hops use each channel independently;
    maximum channel RMS and positive spectral flux prevent anti-phase blindness.
    Global-envelope releases are conservative in polyphony: continuous activity,
    overlap, selection edges and the duration cap are explicitly uncertain.
    """
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim != 2 or not np.isfinite(x).all() or not 0 <= first < last <= len(x):
        raise InputError("event proposal: finite frame/channel matrix and in-range region required")
    if (last - first) / rate > cfg["max_region_seconds"]:
        raise InputError("event proposal: selected region exceeds 30 seconds")
    width = max(2, (rate * cfg["frame_milliseconds"] + 999) // 1000)
    hop = max(1, (rate * cfg["hop_milliseconds"] + 500) // 1000)
    native = x[first:last]
    padded = np.pad(native, ((width // 2, width), (0, 0)))
    starts = np.arange(0, len(native), hop, dtype=np.int64)
    energy, flux = [], []
    window = np.hanning(width)
    previous = np.zeros((width // 2 + 1, x.shape[1]))
    # Finite blocks avoid a region x frame x channel materialisation.
    for block in range(0, len(starts), 128):
        indices = starts[block : block + 128, None] + np.arange(width)[None, :]
        frames = padded[indices].astype(np.float64)
        energy.extend(np.sqrt(np.mean(frames * frames, axis=1)).max(axis=1))
        spectra = np.abs(np.fft.rfft(frames * window[None, :, None], axis=1)) / width
        before = np.concatenate([previous[None], spectra[:-1]], axis=0)
        flux.extend(np.maximum(spectra - before, 0).sum(axis=1).max(axis=1))
        previous = spectra[-1]
    energy, flux = np.array(energy), np.array(flux)
    floor = cfg["absolute_rms_floor"]
    if float(energy.max()) <= floor:
        return {
            "state": "empty",
            "reason": "below declared RMS floor",
            "events": [],
            "analysed_frames": len(starts),
            "channel_policy": "max per-channel RMS/flux",
        }
    distance = max(1, round(cfg["minimum_gap_milliseconds"] * rate / 1000 / hop))
    peaks, _ = find_peaks(
        flux,
        distance=distance,
        prominence=max(floor, float(flux.max()) * cfg["novelty_peak_ratio"]),
    )
    threshold = max(floor, float(energy.max()) * cfg["edge_energy_ratio"])
    # Absolute-floor activity also seeds isolated quiet attacks, even when a
    # louder event elsewhere sets the relative novelty threshold.
    active = energy > floor
    rises = np.flatnonzero(active & ~np.r_[False, active[:-1]])
    onsets = sorted(set(peaks.tolist() + rises.tolist()))
    # Keep the earliest onset in each gap. This prevents a noisy attack's later
    # peak replacing its beginning; no retrieval-driven peak selection occurs.
    chosen = []
    for onset in onsets:
        if active[onset] and (not chosen or onset - chosen[-1] >= distance):
            chosen.append(onset)
    omitted = max(0, len(chosen) - cfg["max_events_per_input"])
    chosen = chosen[: cfg["max_events_per_input"]]
    lead = max(1, round(cfg["attack_lead_milliseconds"] * rate / 1000 / hop))
    hold = max(1, round(cfg["release_hold_milliseconds"] * rate / 1000 / hop))
    minimum = max(1, (rate * cfg["minimum_event_milliseconds"] + 999) // 1000)
    maximum = max(1, rate * cfg["maximum_event_milliseconds"] // 1000)
    events = []
    for onset in chosen:
        # Backtrack through at most the declared attack lead. When continuous
        # energy prevents a quiet boundary, retain context and mark uncertainty.
        left = max(0, onset - lead)
        quiet = np.flatnonzero(energy[left : onset + 1] <= threshold)
        start_bin = left + int(quiet[-1]) if len(quiet) else left
        start = max(first, first + int(starts[start_bin]) - width // 2)
        flags = []
        if not len(quiet) and onset > lead:
            flags.append("attack_in_continuous_activity")
        if start == first:
            flags.append("selection_start_censored")
        peak = float(energy[onset : min(len(energy), onset + lead + 1)].max())
        release_threshold = max(floor, peak * cfg["edge_energy_ratio"])
        end_bin, run = None, 0
        for j in range(onset + 1, len(energy)):
            run = run + 1 if energy[j] <= release_threshold else 0
            if run >= hold:
                end_bin = j - hold + 1
                break
        end = last if end_bin is None else min(last, first + int(starts[end_bin]) + width // 2)
        if end_bin is None:
            flags.append("release_not_observed")
        if end == last:
            flags.append("selection_end_censored")
        if end - start > maximum:
            end = start + maximum
            flags.append("duration_cap_censored")
        if end - start < minimum:
            # A detectable short transient remains visible, but is unsupported
            # for this query contract; never extend it to manufacture a note.
            flags.append("below_minimum_query_duration")
        bounds = {
            "start_frame": start,
            "end_frame": end,
            "onset_frame": min(last - 1, first + int(starts[onset])),
        }
        events.append(
            {
                **bounds,
                "event_id": digest([cfg["detector_version"], bounds]),
                "flags": flags,
                "evidence": {
                    "peak_rms": peak,
                    "onset_flux": float(flux[onset]),
                    "release_rms_threshold": release_threshold,
                },
                "complete": not flags,
            }
        )
    for event in events:
        if any(
            other["event_id"] != event["event_id"]
            and max(event["start_frame"], other["start_frame"])
            < min(event["end_frame"], other["end_frame"])
            for other in events
        ):
            event["flags"].append("overlapping_activity_unresolved")
            event["complete"] = False
    return {
        "state": "uncertain" if any(v["flags"] for v in events) else "proposed",
        "events": events,
        "omitted_after_cap": omitted,
        "analysed_frames": len(starts),
        "channel_policy": "max per-channel RMS/flux; no resample/downmix",
        "low_energy_analysis_frames": int(np.count_nonzero(active & (energy <= threshold))),
        "evidence_meaning": "heuristic measured energy/novelty, not probability or layer identity",
    }
