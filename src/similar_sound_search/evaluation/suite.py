"""Construct and audit the frozen controlled suite; never scores an acoustic matcher."""

import time
from collections import Counter

import numpy as np
from scipy.signal import resample_poly

from ..catalogue.ingestion import validate_local_ready
from ..preparation import prepare
from ..records import map_time
from ..storage import InputError, digest
from .artifacts import load_asset, publish, record, write_record
from .protocol import comparison_pair, freeze, validate_splits
from .rendering import FRAMES, MIX_FRAMES, RATE, mix, render_tone


def real_backgrounds(protocol, budget):
    result = {"development": [], "held_out": []}
    for source in protocol["backgrounds"]:
        value = record(
            budget.root / "manifests/catalogue/starter/entries" / (source["entry_id"] + ".json")
        )
        if value["record_hash"] != source["record_hash"]:
            raise InputError("A04 background: frozen catalogue record changed")
        samples, prepared = validate_local_ready(value, budget)
        first, last = 32000, 160000  # explicit 2..10 seconds of the centred A03 excerpt
        if prepared["artifact"]["sample_rate_hz"] != 16000 or len(samples) < last:
            raise InputError("A04 background: expected validated 16 kHz excerpt covering 2..10s")
        mono = samples[first:last].mean(axis=1)
        output = resample_poly(mono, 3, 2, window=("kaiser", 5.0), padtype="constant")
        lineage = {
            "kind": "catalogue_excerpt",
            "entry_id": source["entry_id"],
            "original_sha256": source["original_sha256"],
            "derivative_sha256": value["analysis_derivative"]["sha256"],
            "source_start_seconds": map_time(prepared, 2)["source_seconds"],
            "source_end_seconds": map_time(prepared, 10)["source_seconds"],
            "original_recording_offset_seconds": prepared["timestamp_mapping"][
                "original_recording_offset_seconds"
            ],
            "input_rate": 16000,
            "output_rate": RATE,
            "channels": "mean",
            "resampling": "resample_poly 3/2 Kaiser5 constant zero",
            "sequential_original_validated": True,
        }
        result[source["split"]].append((output, [source["family"]], lineage))
    return result


def build(budget, policy, ledger_directory, pilot=False):
    started = time.monotonic()
    protocol = freeze(budget, policy)
    backgrounds = real_backgrounds(protocol, budget)
    identities = protocol["presets"][:2] if pilot else protocol["presets"]
    assets, renders, queries = {}, {}, []
    reused = 0
    for preset in identities:
        for phrase in range(3):
            for pitch in (0, 2):
                seed = protocol["seed"] + phrase * 10 + pitch
                recipe = {
                    "kind": "tone",
                    "frames": FRAMES,
                    "rate": RATE,
                    "preset": preset,
                    "performance": phrase,
                    "pitch_semitones": pitch,
                    "seed": seed,
                    "transformation": "native procedural rendering; not human equivalence",
                }

                def render(p=preset, ph=phrase, pi=pitch, s=seed):
                    samples, details = render_tone(p, ph, pi, s)
                    return samples, {
                        **details,
                        "families": [p["family"]],
                        "split": p["split"],
                        "source_id": p["preset_id"],
                        "parents": [],
                        "time_mapping": {
                            "basis": "constructed_file",
                            "source_start_seconds": 0,
                            "original_recording_offset_seconds": 0,
                        },
                    }

                value, used = publish(recipe, render, budget, policy, ledger_directory)
                reused += used
                assets[value["asset_id"]] = value
                renders[(preset["preset_id"], phrase, pitch)] = value
    for preset in identities:
        query = renders[(preset["preset_id"], 0, 0)]
        for condition, phrase, pitch in (
            ("exact_waveform", 0, 0),
            ("performance", 1, 0),
            ("pitch", 1, 2),
        ):
            pool = [
                renders[(p["preset_id"], phrase, pitch)]["asset_id"]
                for p in identities
                if p["split"] == preset["split"]
            ]
            positive = renders[(preset["preset_id"], phrase, pitch)]["asset_id"]
            queries.append(
                make_query(query, condition, pool, [[positive, 0, FRAMES]], "controlled")
            )
    if not pilot:
        for index, preset in enumerate(identities):
            query = renders[(preset["preset_id"], 0, 0)]
            contrast = next(
                p
                for p in identities
                if p["split"] == preset["split"] and p["family"] != preset["family"]
            )
            other = renders[(contrast["preset_id"], 2, 0)]
            other_samples, _ = load_asset(budget.root, other["asset_id"], budget)
            generated_bg = np.resize(other_samples[:, 0], MIX_FRAMES)
            procedural = (
                generated_bg,
                other["families"],
                {
                    "kind": "procedural_repeat",
                    "asset_id": other["asset_id"],
                    "repeat_and_crop_frames": MIX_FRAMES,
                    "source_offset_frames": 0,
                },
            )
            for task in ("exact_instance", "source_consistency", "absent"):
                target = (
                    query if task != "source_consistency" else renders[(preset["preset_id"], 1, 2)]
                )
                target_samples, _ = load_asset(budget.root, target["asset_id"], budget)
                for level_index, level in enumerate((-12, 0, 12) if task != "absent" else (0,)):
                    choices = backgrounds[preset["split"]]
                    bg = (
                        choices[(index + level_index) % len(choices)]
                        if choices and level_index != 1
                        else procedural
                    )
                    positions = (
                        [0, MIX_FRAMES - FRAMES]
                        if level_index == 0
                        else [18000]
                        if level_index == 1
                        else [72000]
                    )
                    if task == "absent":
                        positions = []
                    recipe = {
                        "kind": "mixture",
                        "frames": MIX_FRAMES,
                        "rate": RATE,
                        "task": task,
                        "target_asset": target["asset_id"] if positions else None,
                        "query_asset": query["asset_id"],
                        "background": bg[2],
                        "positions": positions,
                        "target_to_background_db": level if positions else None,
                        "families": sorted(set([preset["family"], *bg[1]])),
                        "split": preset["split"],
                        "seed": protocol["seed"],
                    }

                    def render_mixture(r=recipe, b=bg, t=target_samples[:, 0]):
                        samples, details = mix(
                            t, b[0], r["positions"], r["target_to_background_db"]
                        )
                        return samples, {
                            **details,
                            "families": r["families"],
                            "split": r["split"],
                            "source_id": None,
                            "parents": [
                                r["query_asset"],
                                *([r["target_asset"]] if r["target_asset"] else []),
                                *([b[2]["asset_id"]] if "asset_id" in b[2] else []),
                            ],
                            "time_mapping": {
                                "basis": "constructed_file",
                                "source_start_seconds": 0,
                                "original_recording_offset_seconds": 0,
                            },
                        }

                    value, used = publish(recipe, render_mixture, budget, policy, ledger_directory)
                    reused += used
                    assets[value["asset_id"]] = value
                    truth = [[value["asset_id"], p, p + FRAMES] for p in positions]
                    queries.append(
                        make_query(
                            query, task + ":" + str(level), [value["asset_id"]], truth, "mixture"
                        )
                    )
    counts = validate_splits(protocol, list(assets.values()))
    result = {
        "schema_version": "a04-suite-1",
        "protocol_hash": protocol["record_hash"],
        "pilot": pilot,
        "assets": sorted(assets),
        "asset_record_hashes": {k: assets[k]["record_hash"] for k in sorted(assets)},
        "queries": queries,
        "split_counts": counts,
        "condition_counts": dict(Counter(q["condition"] for q in queries)),
    }
    pair = comparison_pair(budget.root)
    if not pilot and pair and digest(result) != pair[1]["record_hash"]:
        raise InputError(
            "construction differs from atomic comparison suite; deliberate revision required"
        )
    name = "pilot.json" if pilot else "suite.json"
    write_record(budget.root / "manifests/evaluation" / name, result, budget)
    return {
        "status": "ok",
        "assets": len(assets),
        "queries": len(queries),
        "reused": reused,
        "split_counts": counts,
        "condition_counts": result["condition_counts"],
        "protocol_hash": protocol["record_hash"],
        "construction_seconds": time.monotonic() - started,
        "audio_seconds": sum(a["audio"]["duration_seconds"] for a in assets.values()),
        "audio_bytes": sum(a["audio"]["file_bytes"] for a in assets.values()),
    }


def make_query(query, condition, pool, truth, task):
    value = {
        "query_asset_id": query["asset_id"],
        "split": query["split"],
        "condition": condition,
        "task": task,
        "candidate_assets": sorted(pool),
        "targets": [{"asset_id": a, "start_frame": s, "end_frame": e} for a, s, e in truth],
        "designated_source": query["source_id"],
        "absent_by_construction": not truth,
    }
    return {"query_id": digest(value), **value}


def load_suite(budget):
    pair = comparison_pair(budget.root)
    if pair:
        return pair
    protocol = record(budget.root / "manifests/evaluation/protocol.json")
    suite = record(budget.root / "manifests/evaluation/suite.json")
    if suite["protocol_hash"] != protocol["record_hash"]:
        raise InputError("A04 suite: stale protocol hash; regenerate with frozen inputs")
    return protocol, suite


def validate(budget, split="development"):
    protocol, suite = load_suite(budget)
    backgrounds = real_backgrounds(protocol, budget)
    selected = []
    values = {}
    # Integrity of either partition may be checked without evaluating held-out model scores.
    for key in suite["assets"]:
        path = budget.root / "manifests/evaluation/assets" / (key + ".json")
        value = record(path)
        if value["record_hash"] != suite["asset_record_hashes"][key]:
            raise InputError(f"A04 asset {key}: frozen suite record changed")
        if split != "all" and value["split"] != split:
            continue
        samples, value = load_asset(budget.root, key, budget)
        recipe = value["identity"]["recipe"]
        if recipe["kind"] == "tone":
            rebuilt, _ = render_tone(
                recipe["preset"], recipe["performance"], recipe["pitch_semitones"], recipe["seed"]
            )
            if not np.array_equal(samples[:, 0], rebuilt.astype(np.float32)):
                raise InputError(f"A04 tone {key}: independent re-render differs")
        else:
            # Bounds are recomputed from recipe, not copied from the emitted truth manifest.
            expected = [[p, p + FRAMES] for p in recipe["positions"]]
            if value["insertions"] != expected or any(
                not 0 <= a < b <= len(samples) for a, b in expected
            ):
                raise InputError(f"A04 mixture {key}: inserted sample intervals differ")
            if (
                expected
                and abs(value["achieved_tbr_db"] - recipe["target_to_background_db"]) > 1e-10
            ):
                raise InputError(f"A04 mixture {key}: TBR measurement differs")
            _audit_mixture(samples[:, 0], value, backgrounds, budget)
        selected.append(value)
        values[key] = value
    counts = validate_splits(protocol, selected)
    duplicate_partitions = {}
    for value in selected:
        for identity in (value["audio"]["sha256"], value["audio"]["canonical_pcm"]["sha256"]):
            previous = duplicate_partitions.setdefault(identity, value["split"])
            if previous != value["split"]:
                raise InputError("A04 split leakage: identical bytes/PCM cross partitions")
        for parent in value.get("parents", []):
            if parent not in values or not set(values[parent]["families"]).issubset(
                value["families"]
            ):
                raise InputError("A04 lineage: missing parent or lost source family")
    for q in suite["queries"]:
        if split != "all" and q["split"] != split:
            continue
        if q["query_asset_id"] not in values or any(a not in values for a in q["candidate_assets"]):
            raise InputError("A04 query: missing or cross-split candidate")
        if q["query_id"] != digest({k: v for k, v in q.items() if k != "query_id"}):
            raise InputError("A04 query: identity differs")
        for target in q["targets"]:
            if target["asset_id"] not in q["candidate_assets"] or not (
                0
                <= target["start_frame"]
                < target["end_frame"]
                <= values[target["asset_id"]]["audio"]["sample_count"]
            ):
                raise InputError("A04 target: invalid sample interval")
    return {"status": "ok", "split": split, **counts, "protocol_hash": protocol["record_hash"]}


def _audit_mixture(actual, value, backgrounds, budget):
    """Reconstruct stems/algebra without using the mixture renderer or emitted intervals."""
    recipe = value["identity"]["recipe"]
    lineage = recipe["background"]
    if lineage["kind"] == "catalogue_excerpt":
        matches = [x for x in backgrounds[value["split"]] if x[2] == lineage]
        if len(matches) != 1:
            raise InputError("A04 audit: missing/stale real background lineage")
        background = matches[0][0].astype(float)
    else:
        source, _ = load_asset(budget.root, lineage["asset_id"], budget)
        background = np.resize(source[:, 0], MIX_FRAMES).astype(float)
    stem = np.zeros(MIX_FRAMES)
    mask = np.zeros(MIX_FRAMES, dtype=bool)
    if recipe["target_asset"]:
        target, _ = load_asset(budget.root, recipe["target_asset"], budget)
        for start in recipe["positions"]:
            stem[start : start + len(target)] += target[:, 0]
            mask[start : start + len(target)] = True
    gain = 0.0
    if mask.any():
        background_energy = np.sum(background[mask] ** 2)
        target_energy = np.sum(stem[mask] ** 2)
        gain = np.sqrt(background_energy / target_energy) * 10 ** (
            recipe["target_to_background_db"] / 20
        )
    unscaled = background + gain * stem
    common = min(1.0, 0.9 / np.max(np.abs(unscaled)))
    expected = (common * unscaled).astype(np.float32)
    if (
        not np.array_equal(actual, expected)
        or abs(value["target_gain"] - gain) > 1e-12
        or abs(value["common_gain"] - common) > 1e-12
    ):
        raise InputError("A04 independent audit: waveform/gain/insertion algebra differs")
    if mask.any():
        residual = actual.astype(float) / common - background
        achieved = 10 * np.log10(np.sum(residual[mask] ** 2) / np.sum(background[mask] ** 2))
        if abs(achieved - recipe["target_to_background_db"]) > 1e-5:
            raise InputError("A04 independent audit: emitted float32 active-interval ratio differs")


def mapping_diagnostics(budget):
    """Exercise A02 composition with known/unknown excerpt offsets on generated audio."""
    _, suite = load_suite(budget)
    key = next(
        k
        for k in suite["assets"]
        if record(budget.root / "manifests/evaluation/assets" / (k + ".json"))["identity"][
            "recipe"
        ]["kind"]
        == "tone"
    )
    audio, value = load_asset(budget.root, key, budget)
    path = budget.root / value["local_path"]
    results = []
    for kind, offset in (("full_track", 0), ("excerpt", 10), ("excerpt", None)):
        context = {
            "schema_version": "a02-input-1",
            "kind": kind,
            "recording": {
                "recording_id": key,
                "version": "A04 procedural fixture",
                "identity_status": "verified",
                "identity_evidence": "Construction recipe",
            },
            "provenance": {"permitted_use": "Project-generated engineering fixture"},
            "original_recording_offset_seconds": offset,
        }
        if offset is not None:
            context["offset_evidence"] = "Engineering coordinate construction; not a music master"
        first = prepare(path, budget, 16000, "mean", ".3", "1.7", context)
        budget.refresh_disk()
        second = prepare(
            budget.root / first["record"]["artifact"]["local_path"],
            budget,
            24000,
            "preserve",
            ".1",
            "1.1",
            parent_record=first["record"],
        )
        budget.refresh_disk()
        mapped = map_time(second["record"], 0.2)
        if (
            abs(mapped["source_seconds"] - 0.6) > 1 / RATE
            or (
                mapped["recording_seconds"] is not None
                and abs(mapped["recording_seconds"] - (offset + 0.6)) > 1 / RATE
            )
            or (offset is None and mapped["recording_seconds"] is not None)
        ):
            raise InputError("A04 mapping diagnostic: double offset or invalid composed crop")
        results.append(
            {
                "kind": kind,
                "offset": offset,
                "mapped": mapped,
                "bundle": second["bundle"],
                "reused": second["reused"],
            }
        )
    return {"status": "ok", "cases": results, "claim": "engineering coordinates only"}
