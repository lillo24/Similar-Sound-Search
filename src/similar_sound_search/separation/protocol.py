"""Construct and independently preflight a distinct, inspected-development B02 plan."""

import time

import numpy as np
from scipy.io.wavfile import write as write_wav

from ..evaluation.artifacts import load_asset, record, write_record
from ..evaluation.protocol import comparison_pair
from ..evaluation.rendering import render_tone
from ..inputs import decode
from ..storage import InputError, bounded_json, digest


def load(budget, context, key):
    value = record(budget.root / "manifests/evaluation/assets" / (key + ".json"))
    if value["split"] != "development":
        raise InputError("B02 preflight: only inspected development assets allowed")
    context.charge(budget, read_audio_seconds=value["audio"]["duration_seconds"])
    return load_asset(budget.root, key, budget)


def save_signal(budget, context, name, samples, rate):
    x = np.asarray(samples, dtype=np.float32).reshape(-1, 1)
    path = context.directory / "development-audio" / (name + ".wav")
    if not path.exists():
        context.charge(budget, preparation_bytes=x.nbytes + 4096)
        budget.reserve(x.nbytes + 4096, x.nbytes * 8 + 16 * 1024**2)
        path.parent.mkdir(parents=True, exist_ok=True)
        budget.track_file(path)
        temp = path.with_suffix(".partial.wav")
        write_wav(temp, rate, x)
        temp.replace(path)
        budget.account_file(path, path.stat().st_size)
    context.charge(budget, read_audio_seconds=len(x) / rate)
    actual, meta = decode(path, budget)
    if not np.array_equal(actual, x):
        raise InputError("B02 preflight signal changed: " + name)
    return {"path": path.relative_to(budget.root).as_posix(), "sha256": meta["sha256"]}, meta


def preflight(budget, context):
    started = time.perf_counter()
    plan_path = context.directory / "preflight.json"
    if plan_path.exists():
        # Explicit reuse checks every referenced waveform, never silently replaces a plan.
        value = record(plan_path)
        for signal in value["signals"]:
            context.charge(budget, read_audio_seconds=signal["audio"]["duration_seconds"])
            _, meta = decode(budget.root / signal["spec"]["path"], budget)
            if meta != signal["audio"]:
                raise InputError("B02 preflight reuse: input changed")
        return {
            "status": "ok",
            "preflight": plan_path.relative_to(budget.root).as_posix(),
            "reused": True,
        }
    _, suite = comparison_pair(budget.root)
    legacy = record(budget.root / "manifests/events/development.json")
    references = [load(budget, context, c["reference_asset"]) for c in legacy["cases"][:4]]
    # Full predefined pools; same-pitch contrasting presets plus nearby-pitch controls.
    pool = set()
    for q in suite["queries"]:
        if (
            q["split"] == "development"
            and q["condition"] in {"performance", "pitch"}
            and q["task"] == "controlled"
        ):
            pool.update(q["candidate_assets"])
    candidates = []
    for key in sorted(pool):
        _, value = load(budget, context, key)
        if value["audio"]["sample_count"] != 57600 or value["audio"]["sample_rate_hz"] != 24000:
            raise InputError("B02 candidate geometry: expected complete native 2.4-second render")
        candidates.append(
            {
                "asset_id": key,
                "record_hash": value["record_hash"],
                "source_id": value["source_id"],
                "frames": [0, 57600],
                "rate": 24000,
                "pitch": value["identity"]["recipe"]["pitch_semitones"],
            }
        )
    if len(candidates) > 64:
        raise InputError("B02 bounded candidate pool exceeds 64 original passages")
    cases, signals = [], []
    directory = context.directory / "inputs"
    for i, (target, asset) in enumerate(references):
        background = references[(i + 1) % 4][0][:, 0]
        recipe = asset["identity"]["recipe"]
        cue, _ = render_tone(recipe["preset"], 2, 0, 62100 + i)
        clean_cue, cm = save_signal(budget, context, f"cue-{i}-different-performance", cue, 24000)
        contaminated_cue, ccm = save_signal(
            budget, context, f"cue-{i}-contaminated", cue + np.roll(background, 6000), 24000
        )
        signals.extend([{"spec": clean_cue, "audio": cm}, {"spec": contaminated_cue, "audio": ccm}])
        conditions = [
            ("positive-clean-cue", 0, clean_cue),
            ("positive-contaminated-cue", 0, contaminated_cue),
            ("positive-quiet-target", -6, clean_cue),
        ]
        if i == 0:
            conditions += [
                ("absent", 0, clean_cue),
                ("censored", 0, clean_cue),
                ("silence", 0, clean_cue),
                ("exact-waveform-control", 0, clean_cue),
            ]
        for stratum, ratio, cue_spec in conditions:
            name = f"{i}-{stratum}"
            bg = np.tile(background, 4)[:192000].astype(np.float64)
            stem = np.zeros(192000)
            insertion = [36000, 93600]
            target_gain = float(10 ** (ratio / 20))
            stem[36000:93600] = target[:, 0] * target_gain
            event, region = [36000, 93600], [24000, 108000]
            if stratum in {"absent", "silence"}:
                stem[:] = 0
                insertion = None
            if stratum == "silence":
                bg[:] = 0
            if stratum == "censored":
                event, region = [36000, 84000], [24000, 84000]
            if stratum == "exact-waveform-control":
                bg[:] = 0
            mix = stem + bg
            common = min(1.0, 0.9 / max(float(np.max(np.abs(mix))), 1e-30))
            mix, stem, bg = mix * common, stem * common, bg * common
            source, sm = save_signal(budget, context, name, mix, 24000)
            evaluator, tm = save_signal(budget, context, name + "-evaluator-target", stem, 24000)
            signals.extend([{"spec": source, "audio": sm}, {"spec": evaluator, "audio": tm}])
            selected = slice(*event)
            target_power = float(np.mean(stem[selected] ** 2))
            bg_power = float(np.mean(bg[selected] ** 2))
            full = insertion is not None and event[0] <= insertion[0] and event[1] >= insertion[1]
            if stratum.startswith("positive") and (not full or target_power <= 0):
                raise InputError("B02 positive preflight: target absent/truncated: " + name)
            truth = [c["asset_id"] for c in candidates if c["source_id"] == asset["source_id"]]
            if stratum == "exact-waveform-control":
                truth = [asset["asset_id"]]
            if not truth or not all(c["frames"] == [0, 57600] for c in candidates):
                raise InputError("B02 preflight: target/candidate geometry missing")
            spec = {
                "schema_version": "b02-process-input-1",
                "source": source,
                "region": region,
                "event": event,
                "cue": {**cue_spec, "bounds": [0, 57600]},
                "label": name,
            }
            specpath = directory / (name + ".json")
            bounded_json(specpath, spec, budget)
            case_pool = [c["asset_id"] for c in candidates]
            if stratum == "exact-waveform-control":
                case_pool = sorted(set(case_pool + [asset["asset_id"]]))
            cases.append(
                {
                    "case_id": name,
                    "stratum": stratum,
                    "input": specpath.relative_to(budget.root).as_posix(),
                    "source_sha256": sm["sha256"],
                    "source_frames": 192000,
                    "rate": 24000,
                    "insertion": insertion,
                    "region": region,
                    "event": event,
                    "complete_target_support": full,
                    "target_present": bool(target_power),
                    "cue": cue_spec,
                    "cue_performance": 2,
                    "evaluator_target": evaluator,
                    "target_asset": asset["asset_id"],
                    "target_source": asset["source_id"],
                    "target_gain": target_gain,
                    "common_gain": common,
                    "region_tbr_db": float(10 * np.log10(target_power / bg_power))
                    if target_power and bg_power
                    else None,
                    "tbr_state": "finite"
                    if target_power and bg_power
                    else "no-background"
                    if target_power
                    else "target-absent",
                    "candidate_assets": case_pool,
                    "truth_assets": truth if target_power else [],
                    "native_mapping": {
                        "selected_first": event[0],
                        "selected_last": event[1],
                        "region_first": region[0],
                        "selected_in_region": [event[0] - region[0], event[1] - region[0]],
                        "master_offset": None,
                    },
                }
            )
    # The real substitute and its cue are fixed before any B02 catalogue score.
    entry = record(
        budget.root
        / "manifests/catalogue/starter/entries"
        / (legacy["demo_alternatives"][0]["entry_id"] + ".json")
    )
    source = entry["source_asset"]
    real = {
        "schema_version": "b02-process-input-1",
        "source": {"path": source["local_path"], "sha256": source["sha256"]},
        "region": [441000, 970200],
        "event": [441000, 546840],
        "cue": {
            "path": source["local_path"],
            "sha256": source["sha256"],
            "bounds": [546840, 652680],
        },
        "label": "Donnie Ozone — Christmas Shopping at the Dollar Store; "
        "mixed cue, intended layer unverified",
    }
    # Independently check the actual file geometry; no assumed insertion or master offset.
    context.charge(budget, read_audio_seconds=source["duration_seconds"])
    _, realmeta = decode(budget.root / source["local_path"], budget)
    if (
        realmeta["sha256"] != source["sha256"]
        or realmeta["sample_rate_hz"] != 44100
        or realmeta["sample_count"] < 970200
    ):
        raise InputError("B02 real preflight: predetermined source/geometry unavailable")
    bounded_json(directory / "real.json", real, budget)
    value = {
        "schema_version": "b02-preflight-1",
        "development_reuse": "A04/B01 inspected material; distinct new mixtures, no fresh holdout",
        "cases": cases,
        "candidates": candidates,
        "signals": signals,
        "suite_hash": suite["record_hash"],
        "real_input": (directory / "real.json").relative_to(budget.root).as_posix(),
        "real_record_hash": entry["record_hash"],
        "real_cue_uncertainty": "contaminated adjacent mixed audio; "
        "neither intended layer nor complete real note verified",
        "preflight_seconds": time.perf_counter() - started,
        "configuration_hash": digest(context.cfg),
    }
    context.charge(budget, managed_output_bytes=262144)
    write_record(plan_path, value, budget)
    return {
        "status": "ok",
        "preflight": plan_path.relative_to(budget.root).as_posix(),
        "cases": len(cases),
        "candidates": len(candidates),
        "reused": False,
    }
