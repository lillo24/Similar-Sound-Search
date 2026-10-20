"""One prospective B03 fixture batch: recipe invariance and a fixed pitch trade-off."""

import math

import numpy as np
from scipy.io.wavfile import write as write_wav

from ..evaluation.artifacts import record
from ..inputs import decode, pcm_identity
from ..search.contracts import code_identity, frozen
from ..search.ranking import distances
from ..storage import InputError, digest
from . import assets, library, materialization, pitch
from .context import TransformContext
from .features import Features

RATE = 24000
FRAMES = 57600
SELECTION = {
    "origin": "explicit generated native interval",
    "version": "b03-development-1",
    "complete": True,
    "uncertainty": ["source-family identity is a procedural timbre proxy, not human similarity"],
}


def tone(family, hz, performance):
    t = np.arange(FRAMES, dtype=np.float64) / RATE
    phase = 2 * np.pi * hz * t + 0.23 * performance
    harmonics = [(1, 0.12, 0, 0), (1, 0.38, 0.10, 0), (1, 0, 0.12, 0), (1, 0.25, 0.15, 0.08)][
        family
    ]
    x = sum(gain * np.sin((i + 1) * phase) for i, gain in enumerate(harmonics))
    if family == 2:
        x *= 1 + 0.3 * np.sin(2 * np.pi * 7 * t)
    envelope = np.minimum(t / (0.025 + performance * 0.004), 1) * np.minimum(
        (FRAMES / RATE - t) / 0.12, 1
    )
    return (0.16 * x * envelope)[:, None].astype(np.float32)


def save_signal(budget, owner, name, selected, start):
    x = np.zeros((start + FRAMES + 9600, 1), np.float32)
    x[start : start + FRAMES] = selected
    # Identical generated source arrays share one explicit binding; logical case
    # labels remain separate. Registration never silently rebinds a second name.
    path = owner.root / "data/audio/queries/development" / (digest(pcm_identity(x, RATE)) + ".wav")
    if not path.exists():
        owner.charge(budget, preparation_bytes=x.nbytes + 4096)
        budget.reserve(x.nbytes + 4096, x.nbytes * 8 + 32 * 1024**2)
        path.parent.mkdir(parents=True, exist_ok=True)
        budget.track_file(path)
        partial = path.with_suffix(".partial.wav")
        write_wav(partial, RATE, x)
        partial.replace(path)
        budget.account_file(path, path.stat().st_size)
    owner.charge(budget, read_audio_seconds=len(x) / RATE)
    actual, audio = decode(path, budget)
    if (
        not np.array_equal(actual, x)
        or len(actual[start : start + FRAMES]) != FRAMES
        or np.any(actual[:start])
        or np.any(actual[start + FRAMES :])
    ):
        raise InputError("B03 independent geometry: changed saved insertion/support: " + name)
    registered = assets.register(budget, owner, path)
    return {
        "label": name,
        "path": path.relative_to(owner.root).as_posix(),
        "sha256": audio["sha256"],
        "asset_id": registered["asset_id"],
        "event": [start, start + FRAMES],
        "context": [max(0, start - 4800), start + FRAMES + 4800],
        "audio": audio,
        "geometry": {
            "independent_saved_sample_equality": True,
            "nonzero_insertion_frame": start,
            "selected_frames": FRAMES,
            "full_generated_attack_release": bool(np.any(selected)),
        },
    }


def preflight(budget, owner):
    path = owner.directory / "development.json"
    if path.exists():
        value = record(path)
        for item in [*value["candidates"], *value["signals"]]:
            assets.read_asset(budget, owner, item["asset_id"])
        return {
            "status": "ok",
            "plan": path.relative_to(owner.root).as_posix(),
            "plan_hash": value["record_hash"],
            "reused": True,
        }
    candidates = []
    for family in range(4):
        for hz in (110, 220, 261.6255653005986, 440):
            item = save_signal(budget, owner, f"candidate-{family}-{hz}", tone(family, hz, 2), 7200)
            candidates.append(
                {
                    **item,
                    "family": family,
                    "frequency_truth_hz": hz,
                    "recording_id": digest([family, hz]),
                    "group": digest([family, hz]),
                }
            )
    cases, signals = [], []
    descriptions = [
        ("single-220", 0, [220], "primary"),
        ("octave-440", 0, [440], "primary"),
        ("single-261", 1, [261.6255653005986], "primary"),
        ("low-130", 1, [130.8127826502993], "primary"),
        ("multiple-registers", 0, [220, 440], "primary"),
        ("processed-mixture", 2, [220], "primary"),
        ("noisy-chord", 3, [220], "ambiguous_diagnostic"),
        ("silence", None, [220], "absent_diagnostic"),
    ]
    for name, family, frequencies, stratum in descriptions:
        examples = []
        for n, hz in enumerate(frequencies):
            x = np.zeros((FRAMES, 1), np.float32) if family is None else tone(family, hz, 1)
            if name == "processed-mixture":
                t = np.arange(FRAMES) / RATE
                x = x + (0.055 * np.sin(2 * np.pi * 1800 * t))[:, None].astype(np.float32)
                x[::1200] += 0.1
            if name == "noisy-chord":
                x = (
                    x
                    + tone(family, 330, 1)
                    + np.random.default_rng(303).normal(0, 0.03, x.shape).astype(np.float32)
                )
            signal = save_signal(budget, owner, name + "-" + str(n), x, 9600)
            signals.append(signal)
            examples.append(
                {
                    "asset_id": signal["asset_id"],
                    "event": signal["event"],
                    "context": signal["context"],
                    "selection": SELECTION
                    if family is not None
                    else {
                        **SELECTION,
                        "complete": False,
                        "uncertainty": [
                            "intentionally target-absent silence control; "
                            "no event/attack/release claimed"
                        ],
                    },
                }
            )
        item = {
            "case_id": name,
            "stratum": stratum,
            "family_truth": family,
            "frequency_truth_hz": frequencies,
            "input": {"schema_version": "b03-query-input-1", "examples": examples},
            "signal": signals[-1],
        }
        if name == "processed-mixture":
            s = item["signal"]
            item["processing"] = {
                "schema_version": "b02-process-input-1",
                "source": {"path": s["path"], "sha256": s["sha256"]},
                "region": s["context"],
                "event": s["event"],
            }
        cases.append(item)
    value = {
        "schema_version": "b03-development-1",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "signals": signals,
        "cases": cases,
        "arms": {"off": library.OFF, "primary": owner.cfg["pitch"]},
        "ks": [1, 5, 10],
        "primary_cases": 6,
        "diagnostic_cases": 2,
        "aggregation": "same mean unique-PCM timbre distances; same complete candidate "
        "support/groups/exclusions and stable ties",
        "criteria": "exact direct/saved/reopened off equality and fixed winner intervals; "
        "independent 0..0.03 contribution bound; report all paired gains/losses "
        "without changing defaults",
        "stop_rule": "one eight-case/sixteen-arm batch; all failures retained; "
        "no replacement or sensitivity setting",
        "exposure": "new deterministic B03 fixtures using familiar procedural harmonic/envelope "
        "ideas; inspected development, no fresh holdout or human similarity",
        "geometry": "all saved native arrays independently compared to generated full-support "
        "insertion at 7200/9600 frames; no inferred zero offset; "
        "oracle family/frequency truth used only for scoring",
    }
    owner.publish(budget, path, value, immutable=True)
    return {
        "status": "ok",
        "plan": path.relative_to(owner.root).as_posix(),
        "plan_hash": record(path)["record_hash"],
        "reused": False,
    }


def selected(budget, owner, signal):
    owner.charge(budget, read_audio_seconds=signal["audio"]["duration_seconds"])
    x, audio = decode(owner.root / signal["path"], budget)
    if audio != signal["audio"]:
        raise InputError("B03 comparison: saved source identity changed")
    a, b = signal["event"]
    x = x[a:b]
    return x, {
        "canonical_pcm": pcm_identity(x, RATE),
        "duration_seconds": len(x) / RATE,
        "sample_rate_hz": RATE,
    }


def rank_rows(rows, vectors, candidate_pitch, query_pitch, plan, policy):
    per, aggregate = distances(rows, np.stack(vectors), "cosine")
    hits = []
    for i, candidate in enumerate(plan["candidates"]):
        detail = pitch.contribution(query_pitch, candidate_pitch[i], policy)
        if detail["all_query_estimates_reliable"] and candidate_pitch[i]["hz"] is not None:
            independent = (
                policy["weight"]
                * sum(
                    min(
                        1,
                        abs(12 * math.log2(v["hz"] / candidate_pitch[i]["hz"]))
                        / policy["scale_semitones"],
                    )
                    for v in query_pitch
                )
                / len(query_pitch)
            )
        else:
            independent = 0
        if (
            abs(independent - detail["value"]) > 1e-14
            or not 0 <= detail["value"] <= policy["weight"]
        ):
            raise InputError("B03 independent pitch contribution bound/formula failed")
        hits.append(
            {
                "recording_id": candidate["recording_id"],
                "family": candidate["family"],
                "start_frame": candidate["event"][0],
                "end_frame": candidate["event"][1],
                "timbre_distance": float(aggregate[i]),
                "per_example_distances": per[:, i].tolist(),
                "pitch": candidate_pitch[i],
                "pitch_detail": detail,
                "score": float(aggregate[i]) + detail["value"],
            }
        )
    return sorted(
        hits, key=lambda v: (v["score"], v["recording_id"], v["start_frame"], v["end_frame"])
    )


def case(budget, owner, item, plan, desc):
    cache = Features(budget, owner, desc)
    vectors, candidate_pitch = [], []
    for candidate in plan["candidates"]:
        x, audio = selected(budget, owner, candidate)
        vectors.append(cache.get(x, audio))
        candidate_pitch.append(pitch.cached_estimate(budget, owner, x, RATE))
    spec = item["input"]
    if item.get("processing"):
        from ..separation import artifacts

        result = artifacts.process(budget, item["processing"], "broad", TransformContext(owner))
        spec = {
            "schema_version": "b03-query-input-1",
            "examples": [
                {
                    "transform_record": result["transform"],
                    "component": "harmonic",
                    "selection": SELECTION,
                }
            ],
        }
    created = library.save(budget, owner, spec, "B03 development " + item["case_id"])
    revision = library.revision(owner, created["revision_id"])
    materialization.materialize(budget, owner, revision)
    _, query, rows = materialization.load(budget, owner, revision)
    # Independently resolve each source selection to obtain direct PCM feature rows.
    direct = {}
    for example in revision["recipe"]["examples"]:
        resolved, _ = owner.resolve_example(budget, example)
        from ..preparation import crop_frames

        path = owner.root / resolved["path"]
        from ..inputs import probe

        info = probe(path, budget)
        owner.charge(budget, read_audio_seconds=info.frames / info.samplerate)
        x, _ = decode(path, budget)
        a, b = crop_frames(resolved["start"], resolved["end"], len(x), info.samplerate)
        x = x[a:b]
        metadata = {
            "canonical_pcm": pcm_identity(x, info.samplerate),
            "sample_rate_hz": info.samplerate,
            "duration_seconds": len(x) / info.samplerate,
        }
        direct[metadata["canonical_pcm"]["sha256"]] = cache.get(x, metadata)
    direct_rows = np.stack([direct[k] for k in sorted(direct)])
    if not np.array_equal(direct_rows, rows):
        raise InputError("B03 direct/saved feature round trip differs")
    reopen = materialization.materialize(budget, owner, revision)
    _, reopened, reopened_rows = materialization.load(
        budget, owner, library.revision(owner, created["revision_id"])
    )
    if (
        not reopen["reused"]
        or not np.array_equal(reopened_rows, rows)
        or reopened["query_id"] != query["query_id"]
    ):
        raise InputError("B03 reopened materialization/feature identity differs")
    estimates = [v["pitch"] for v in query["examples"]]
    arms = {}
    for name, policy in plan["arms"].items():
        hits = rank_rows(rows, vectors, candidate_pitch, estimates, plan, policy)
        direct_hits = rank_rows(direct_rows, vectors, candidate_pitch, estimates, plan, library.OFF)
        if name == "off" and hits != direct_hits:
            raise InputError("B03 direct/saved/reopened pitch-off ranks differ")
        arms[name] = {
            "state": "complete",
            "hits": hits,
            "source_family_hits": {
                str(k): any(v["family"] == item["family_truth"] for v in hits[:k])
                for k in (1, 5, 10)
            },
        }
    return {
        "case_id": item["case_id"],
        "stratum": item["stratum"],
        "family_truth": item["family_truth"],
        "revision_id": revision["revision_id"],
        "query_pitch": estimates,
        "arms": arms,
        "off_round_trip_exact": True,
        "reopen_reused": True,
        "features": cache.stats(),
    }


def binding(plan, owner):
    """Pin the prospective producer; allow only a declared execution-only repair."""
    code = code_identity()
    identity = {
        "plan_hash": plan["record_hash"],
        "code": code,
        "configuration": owner.cfg,
    }
    public = owner.root / "manifests/queries"
    if (public / "protocol.json").exists():
        protocol = record(public / "protocol.json")
        if protocol["plan_hash"] != plan["record_hash"]:
            raise InputError("B03 comparison: prospective plan changed")
        if protocol["code"] != code:
            declaration = record(public / "execution-repair-plan.json")
            repair = record(public / "execution-repair.json")
            changed = {
                k
                for k in code.keys() | protocol["code"].keys()
                if code.get(k) != protocol["code"].get(k)
            }
            if (
                declaration["protocol_hash"] != protocol["record_hash"]
                or declaration["before"] != protocol["code"]
                or repair["declaration_hash"] != declaration["record_hash"]
                or repair["before"] != protocol["code"]
                or repair["after"] != code
                or repair["plan_hash"] != plan["record_hash"]
                or repair["configuration"] != owner.cfg
                or not changed <= {"queries/features.py", "queries/development.py"}
            ):
                raise InputError("B03 comparison: undeclared producer drift; no replacement batch")
            identity["execution_repair"] = repair["record_hash"]
    return identity


def step(budget, owner):
    plan = record(owner.root / "manifests/queries/development.json")
    private = record(owner.directory / "development.json")
    if plan != private:
        raise InputError("B03 compare: publish exact verified preflight before comparisons")
    identity = binding(plan, owner)
    path = owner.directory / "comparison/progress.json"
    if path.exists():
        progress = record(path)
        if progress["identity"] != identity:
            raise InputError(
                "B03 comparison: producer drift; retain predictions, no replacement batch"
            )
    else:
        owner.charge(budget, comparisons=1, query_jobs=1)
        progress = {"identity": identity, "completed": []}
        owner.publish(budget, path, progress)
    done = progress["completed"]
    if done != [v["case_id"] for v in plan["cases"][: len(done)]]:
        raise InputError("B03 comparison: completed cases are not the declared prefix")
    if len(done) < len(plan["cases"]):
        item = plan["cases"][len(done)]
        counts = record(owner.directory / "work.json")["counts"]
        # Cases/arms count unique predeclared units, while all retried worker,
        # read, feature and processing reservations remain cumulatively charged.
        if counts["comparison_queries"] != 2 * counts["comparison_cases"]:
            raise InputError("B03 comparison: case/arm counters disagree")
        if counts["comparison_cases"] == len(done):
            owner.charge(budget, comparison_cases=1, comparison_queries=2)
        elif counts["comparison_cases"] != len(done) + 1:
            raise InputError("B03 comparison: counters disagree with pending declared case")
        case_path = owner.directory / "comparison" / (item["case_id"] + ".json")
        if case_path.exists():
            answer = record(case_path)
            if answer["case_id"] != item["case_id"] or answer["batch_identity"] != digest(identity):
                raise InputError("B03 comparison: saved prediction belongs to another batch")
        else:
            _, _, _, _, desc = frozen(budget)
            try:
                answer = case(budget, owner, item, plan, desc)
            except InputError as exc:
                answer = {
                    "case_id": item["case_id"],
                    "stratum": item["stratum"],
                    "family_truth": item["family_truth"],
                    "state": "failed",
                    "error": str(exc),
                    "off_round_trip_exact": False,
                    "arms": {
                        k: {
                            "state": "failed",
                            "error": str(exc),
                            "source_family_hits": {str(n): False for n in (1, 5, 10)},
                        }
                        for k in plan["arms"]
                    },
                }
            answer["batch_identity"] = digest(identity)
            owner.publish(budget, case_path, answer, immutable=True)
        done.append(item["case_id"])
        owner.publish(budget, path, {"identity": identity, "completed": done})
        if len(done) < len(plan["cases"]):
            return {"status": "ok", "state": "in_progress", "cursor": len(done), "cases": len(done)}
    answers = [
        record(owner.directory / "comparison" / (v["case_id"] + ".json")) for v in plan["cases"]
    ]
    primary = [v for v in answers if v["stratum"] == "primary"]
    metrics = {
        arm: {
            str(k): sum(v["arms"][arm]["source_family_hits"][str(k)] for v in primary)
            for k in (1, 5, 10)
        }
        for arm in plan["arms"]
    }
    gains = sum(
        not v["arms"]["off"]["source_family_hits"]["1"]
        and v["arms"]["primary"]["source_family_hits"]["1"]
        for v in primary
    )
    losses = sum(
        v["arms"]["off"]["source_family_hits"]["1"]
        and not v["arms"]["primary"]["source_family_hits"]["1"]
        for v in primary
    )
    value = {
        "schema_version": "b03-comparison-1",
        "identity": identity,
        "cases": answers,
        "primary_denominator": len(primary),
        "diagnostic_denominator": len(answers) - len(primary),
        "source_family_hits": metrics,
        "paired_top1_gains": gains,
        "paired_top1_losses": losses,
        "rank_changes": sum(
            [h["recording_id"] for h in v["arms"]["off"]["hits"]]
            != [h["recording_id"] for h in v["arms"]["primary"]["hits"]]
            for v in answers
            if v.get("state") != "failed"
        ),
        "round_trip_exact_cases": sum(v["off_round_trip_exact"] for v in answers),
        "failures": [v["case_id"] for v in answers if v.get("state") == "failed"],
        "default": "original audio; pitch off",
        "human_relevance": "unmeasured",
    }
    owner.publish(budget, owner.directory / "comparison/summary.json", value, immutable=True)
    return {
        "status": "ok",
        "summary": "data/runs/queries/comparison/summary.json",
        "metrics": metrics,
        "primary_denominator": len(primary),
        "failures": value["failures"],
    }
