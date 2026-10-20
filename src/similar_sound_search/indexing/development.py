"""One prospectively fixed development batch; no labels enter feature extraction."""

import time

import numpy as np
from scipy.io.wavfile import write as write_wav

from ..evaluation import rendering
from ..evaluation.artifacts import record
from ..inputs import decode
from ..matchers.acoustic import checked
from ..search.contracts import grid, load_array, save_array
from ..search.ranking import distances
from ..storage import InputError, digest
from . import banks, build


def save_audio(budget, owner, name, samples, rate):
    path = owner.root / "data/audio/indexing/development" / (name + ".wav")
    samples = np.asarray(samples, dtype=np.float32).reshape(-1, 1)
    if path.exists():
        owner.charge(budget, read_audio_seconds=len(samples) / rate)
        actual, _ = decode(path, budget)
        if not np.array_equal(samples, actual):
            raise InputError("C01 generated input conflicts: " + name)
    else:
        owner.charge(budget, preparation_bytes=samples.nbytes + 65536)
        budget.reserve(samples.nbytes + 65536, samples.nbytes * 4)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(path, rate, samples)
    owner.charge(budget, read_audio_seconds=len(samples) / rate)
    _, audio = decode(path, budget)
    return {**audio, "local_path": path.relative_to(owner.root).as_posix()}


def public(audio, name, family):
    return {
        "recording_id": name,
        "record_hash": digest(audio),
        "kind": "engineering",
        "group": "c01-family-" + family,
        "data_role": "engineering",
        "source": audio,
        "title": name,
        "artist": "Procedural development fixture",
        "provider": "generated",
        "provider_recording_id": None,
        "known_family_id": family,
        "source_url": None,
        "source_page": None,
        "rights": {"permitted_use": "Generated C01 engineering fixture"},
        "basis": "file",
        "offset": 0,
        "offset_evidence": "known generated native layout",
    }


def generate(budget, owner, desc):
    path = owner.directory / "development/fixtures.json"
    if path.exists():
        return {"status": "ok", "fixtures": path.relative_to(owner.root).as_posix(), "reused": True}
    cfg = owner.protocol["development"]
    presets = [
        p for p in rendering.presets(cfg["family_selection_seed"]) if p["split"] == "development"
    ]
    rate, seed = cfg["rate"], cfg["seed"]
    rng = np.random.default_rng(seed)
    sources, tones, queries = [], {}, []
    for f, family in enumerate(cfg["families"]):
        for variant in range(2):
            preset = next(
                p for p in presets if p["mechanism"] == family and p["variant"] == variant
            )
            tone, _ = rendering.render_tone(preset, variant, variant * 2, seed + f * 10 + variant)
            tones[(family, variant)] = tone
            first = round(cfg["insertions_seconds"][f][variant] * rate)
            background = 0.012 * np.sqrt(2) * np.sin(2 * np.pi * 83 * np.arange(8 * rate) / rate)
            background += 0.003 * rng.standard_normal(8 * rate)
            target = np.zeros(8 * rate)
            target[first : first + len(tone)] = tone
            name = family + "-" + str(variant)
            audio = save_audio(budget, owner, name, target + background, rate)
            stem = save_audio(budget, owner, name + "-target", target, rate)
            bg = save_audio(budget, owner, name + "-background", background, rate)
            isolated = save_audio(budget, owner, name + "-isolated", tone, rate)
            sources.append(
                {
                    "source": public(audio, name, family),
                    "family": family,
                    "truth": [first, first + len(tone)],
                    "target": stem,
                    "background": bg,
                    "isolated": isolated,
                }
            )
    short = tones[("pluck", 0)][: round(0.3 * rate)]
    audio = save_audio(budget, owner, "pluck-short-file", short, rate)
    sources.append(
        {
            "source": public(audio, "pluck-short-file", "pluck"),
            "family": "pluck",
            "truth": [0, len(short)],
            "target": audio,
            "background": None,
            "isolated": audio,
        }
    )
    for case in cfg["queries"]:
        family = case["family"]
        if case["stratum"] == "alternate":
            preset = next(p for p in presets if p["mechanism"] == family and p["variant"] == 1)
            samples, _ = rendering.render_tone(preset, case["phrase"], case["pitch"], seed + 300)
        elif case["id"] == "exact-fm":
            samples = tones[("fm", 0)]
        elif case["id"] == "exact-short-file":
            samples = short
        elif case["id"] == "silence":
            samples = np.zeros(rendering.FRAMES)
        else:
            samples = 0.08 * np.sin(2 * np.pi * 10000 * np.arange(rendering.FRAMES) / rate)
        if case["support"] == "attack":
            samples = samples[: round(0.3 * rate)]
        audio = save_audio(budget, owner, "query-" + case["id"], samples, rate)
        queries.append({**case, "audio": audio})
    signals = {s["source"]["recording_id"]: banks.original_signal(s["source"]) for s in sources}
    plans = []
    for duration, hop in cfg["grids_milliseconds"]:
        p, _ = banks.create_plan(
            budget,
            owner,
            "development-" + str(duration),
            "original",
            desc,
            {"window_milliseconds": duration, "hop_milliseconds": hop},
            signals,
            "engineering",
            pilot=True,
        )
        plans.append(p.relative_to(owner.root).as_posix())
    value = {
        "schema_version": "c01-fixtures-1",
        "protocol_hash": digest(owner.protocol),
        "sources": sources,
        "queries": queries,
        "plans": plans,
        "family_presets": presets,
        "truth_kind": "generated source consistency; no human relevance",
    }
    owner.publish(budget, path, value, immutable=True)
    return {"status": "ok", "fixtures": path.relative_to(owner.root).as_posix(), "plans": plans}


def query_feature(budget, owner, case, desc):
    audio = case["audio"]
    owner.charge(budget, read_audio_seconds=audio["duration_seconds"])
    samples, meta = decode(owner.root / audio["local_path"], budget)
    if meta != {k: v for k, v in audio.items() if k != "local_path"}:
        raise InputError("C01 development query bytes/decoder changed")
    if np.max(np.abs(samples)) <= 1e-12:
        raise InputError("C01 development query: silence, no valid vector")
    identity = {
        "version": "c01-development-query-1",
        "pcm": audio["canonical_pcm"],
        "representation": desc,
        "dimension": desc["dimension"],
    }
    path = owner.features / "development-queries" / digest(identity)
    if path.exists():
        return load_array(path, identity, budget)[0]
    owner.charge(
        budget,
        query_jobs=1,
        feature_windows=1,
        pilot_windows=1,
        processed_window_seconds=audio["duration_seconds"],
        feature_bytes=65536 + 4 * desc["dimension"],
    )
    samples = checked(
        owner.model(budget, desc).encode(samples, audio["sample_rate_hz"]), desc["dimension"]
    )[None]
    save_array(path.parent, identity, samples, budget)
    return samples


def compare(budget, owner, fixtures, desc):
    geometry = record(owner.directory / "development/geometry.json")
    if geometry["fixtures_hash"] != fixtures["record_hash"] or not geometry["passed"]:
        raise InputError("C01 comparison requires independent saved-waveform geometry checks")
    output = owner.directory / "development/comparison.json"
    if output.exists():
        raise InputError("C01 fixed comparison already complete; no replacement batch")
    pending = owner.directory / "development/comparison-pending.json"
    if not pending.exists():
        owner.charge(
            budget,
            comparison_batches=1,
            query_jobs=1,
            case_bank_queries=len(fixtures["queries"]) * len(fixtures["plans"]),
        )
        owner.publish(
            budget,
            pending,
            {"state": "pending", "fixtures_hash": fixtures["record_hash"]},
            immutable=True,
        )
    elif record(pending)["fixtures_hash"] != fixtures["record_hash"]:
        raise InputError("C01 comparison pending inputs conflict")
    arrays = []
    for relative in fixtures["plans"]:
        plan = banks.validate_plan(owner, owner.root / relative)
        state = build.progress(owner, plan)
        if len(state["committed"]) != len(banks.units(plan)):
            raise InputError("C01 comparison candidate bank is incomplete")
        for signal in plan["signals"].values():
            build.load_signal(budget, owner, signal)
        rows, features = [], []
        for unit in banks.units(plan):
            a, _ = load_array(build.array_path(owner, unit), unit["identity"], budget)
            features.extend(a)
            rows.extend(
                {
                    **banks.passage(plan, unit, i),
                    "source": plan["signals"][unit["signal_id"]]["original"],
                }
                for i in range(len(a))
            )
        arrays.append((plan, rows, np.asarray(features)))
    results = []
    for case in fixtures["queries"]:
        started = time.perf_counter()
        try:
            q = query_feature(budget, owner, case, desc)
        except InputError as exc:
            if (
                case["stratum"] != "silence"
                or str(exc) != "C01 development query: silence, no valid vector"
            ):
                raise
            results.append(
                {
                    "case_id": case["id"],
                    "stratum": case["stratum"],
                    "state": "failed-silence",
                    "banks": [],
                    "expected_failure": True,
                }
            )
            continue
        arms = []
        for plan, rows, features in arrays:
            _, scores = distances(q, features, desc["distance"])
            best = {}
            for row, score in zip(rows, scores, strict=True):
                key = (float(score), row["source"]["recording_id"], *row["signal_bounds"])
                family = row["source"]["known_family_id"]
                if family not in best or key < best[family][0]:
                    best[family] = (key, row)
            ordered = sorted(best.values(), key=lambda v: v[0])
            ranking = [
                {
                    "family": row["source"]["known_family_id"],
                    "score": key[0],
                    "recording_id": row["source"]["recording_id"],
                    "bounds": row["signal_bounds"],
                    "row_id": row["row_id"],
                }
                for key, row in ordered
            ]
            truth = [s for s in fixtures["sources"] if s["family"] == case["family"]]
            opportunities, supported = 0, 0
            for source in truth:
                lo, hi = source["truth"]
                if case["support"] == "attack":
                    hi = min(hi, lo + round(0.3 * source["source"]["source"]["sample_rate_hz"]))
                these = [
                    r
                    for r in rows
                    if r["source"]["recording_id"] == source["source"]["recording_id"]
                ]
                opportunities += 1
                supported += any(
                    r["signal_bounds"][0] <= lo and hi <= r["signal_bounds"][1] for r in these
                )
            target = next((v for v in ranking if v["family"] == case["family"]), None)
            localization = None
            if target:
                source = next(
                    s for s in truth if s["source"]["recording_id"] == target["recording_id"]
                )
                lo, hi = source["truth"]
                if case["support"] == "attack":
                    hi = min(hi, lo + round(0.3 * source["source"]["source"]["sample_rate_hz"]))
                a, b = target["bounds"]
                overlap = max(0, min(b, hi) - max(a, lo))
                localization = {
                    "overlap_frames": overlap,
                    "IoU": overlap / (max(b, hi) - min(a, lo)),
                    "boundary_error_seconds": (abs(a - lo) + abs(b - hi)) / 24000,
                    "contains_full_event": a <= lo and hi <= b,
                }
            arms.append(
                {
                    "duration_ms": plan["bank"]["identity"]["grid"]["window_milliseconds"],
                    "hop_ms": 500,
                    "state": "ready",
                    "ranking": ranking,
                    "hit1": ranking[0]["family"] == case["family"] if truth else None,
                    "hit3": any(v["family"] == case["family"] for v in ranking[:3])
                    if truth
                    else None,
                    "containment_opportunities": [supported, opportunities],
                    "target_localization": localization,
                }
            )
        results.append(
            {
                "case_id": case["id"],
                "stratum": case["stratum"],
                "state": "ready",
                "banks": arms,
                "seconds": time.perf_counter() - started,
            }
        )
    summary = {}
    for duration in (1200, 2400, 4800):
        cases = [
            next(a for a in c["banks"] if a["duration_ms"] == duration)
            for c in results
            if c["stratum"] == "alternate"
        ]
        baseline = [
            next(a for a in c["banks"] if a["duration_ms"] == 2400)
            for c in results
            if c["stratum"] == "alternate"
        ]
        # Only complete 2.4s native truths enter this denominator. The short-file
        # control stays in rankings/cases, but cannot supply a full 2.4s event.
        support = []
        for case in fixtures["queries"]:
            if case["stratum"] != "alternate" or case["support"] != "full":
                continue
            for source in fixtures["sources"]:
                audio = source["source"]["source"]
                lo, hi = source["truth"]
                if (
                    source["family"] != case["family"]
                    or (hi - lo) * 1000 != 2400 * audio["sample_rate_hz"]
                ):
                    continue
                windows = grid(
                    audio["sample_count"],
                    audio["sample_rate_hz"],
                    {"window_milliseconds": duration, "hop_milliseconds": 500},
                )
                support.append(any(a <= lo and hi <= b for a, b in windows))
        summary[str(duration)] = {
            "alternate_cases": len(cases),
            "hit1": sum(v["hit1"] for v in cases),
            "hit3": sum(v["hit3"] for v in cases),
            "paired_gains": sum(
                a["hit1"] and not b["hit1"] for a, b in zip(cases, baseline, strict=True)
            ),
            "paired_losses": sum(
                b["hit1"] and not a["hit1"] for a, b in zip(cases, baseline, strict=True)
            ),
            "full_event_support": [sum(support), len(support)],
        }
    value = {
        "schema_version": "c01-comparison-1",
        "fixtures_hash": fixtures["record_hash"],
        "protocol_hash": digest(owner.protocol),
        "cases": results,
        "summary": summary,
        "complete": True,
        "pitch_weight": 0,
        "scope": "development only; exact and absent diagnostics separate",
    }
    owner.publish(budget, output, value, immutable=True)
    return {
        "status": "ok",
        "comparison": output.relative_to(owner.root).as_posix(),
        "summary": summary,
    }
