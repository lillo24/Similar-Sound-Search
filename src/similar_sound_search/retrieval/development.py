"""One frozen 33-group audio batch, independent geometry and exact policy ablation."""

import numpy as np
from scipy.io.wavfile import write as write_wav
from scipy.signal import correlate, correlation_lags

from ..evaluation import rendering
from ..evaluation.artifacts import record
from ..indexing.development import public
from ..inputs import decode
from ..matchers.acoustic import checked
from ..search.contracts import frozen, grid, load_array, save_array
from ..search.ranking import distances, timbre_key
from ..storage import InputError, digest
from . import engine, fusion


def audio(budget, owner, name, samples, rate):
    samples = np.asarray(samples, np.float32).reshape(-1, 1)
    path = owner.root / "data/audio/retrieval" / (name + ".wav")
    if not path.exists():
        owner.charge(budget, preparation_bytes=samples.nbytes + 4096)
        budget.reserve(samples.nbytes + 4096, samples.nbytes * 4)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(path, rate, samples)
    owner.charge(budget, read_audio_seconds=len(samples) / rate)
    actual, meta = decode(path, budget)
    if not np.array_equal(actual, samples):
        raise InputError("C02 generated waveform conflicts: " + name)
    return {**meta, "local_path": path.relative_to(owner.root).as_posix()}


def reconstruct(spec, rate):
    rng = np.random.default_rng(spec["background_seed"])
    n = spec["frames"]
    bg = 0.006 * np.sin(2 * np.pi * 83 * np.arange(n) / rate) + 0.002 * rng.standard_normal(n)
    parts = []
    for item in spec["parts"]:
        tone, _ = rendering.render_tone(item["preset"], item["phrase"], item["pitch"], item["seed"])
        parts.append((item["first"], tone))
    x = bg.copy()
    for first, tone in parts:
        x[first : first + len(tone)] += tone
    return x, bg, parts


def generate(budget, owner):
    path = owner.directory / "development/fixtures.json"
    if path.exists():
        raise InputError("C02 fixed fixtures already generated; use geometry/build")
    cfg = owner.protocol["development"]
    seed = cfg["seed"]
    rate = cfg["rate"]
    presets = [
        p for p in rendering.presets(cfg["family_selection_seed"]) if p["split"] == "development"
    ]
    specs = []
    tones = {}
    for f, family in enumerate(cfg["families"]):
        for variant in range(2):
            preset = next(
                p for p in presets if p["mechanism"] == family and p["variant"] == variant
            )
            part = {
                "preset": preset,
                "phrase": variant,
                "pitch": variant * 2,
                "seed": seed + f * 10 + variant,
                "first": round(cfg["insertions_seconds"][f][variant] * rate),
                "family": family,
            }
            tone, _ = rendering.render_tone(preset, part["phrase"], part["pitch"], part["seed"])
            tones[family, variant] = tone
            specs.append(
                {
                    "id": family + "-" + str(variant),
                    "group": "c02-family-" + family,
                    "frames": round(cfg["duration_seconds"] * rate),
                    "background_seed": seed + 100 + f * 2 + variant,
                    "parts": [part],
                }
            )
    for i in range(cfg["distractor_groups"]):
        preset = dict(presets[i % len(presets)])
        preset["parameters"] = {
            **preset["parameters"],
            "spectral_slope": 2.2 + i * 0.09,
            "fm_ratio": 2.11 + i * 0.071,
            "cutoff_hz": 1300 + i * 240,
        }
        specs.append(
            {
                "id": f"distractor-{i:02}",
                "group": f"c02-distractor-{i:02}",
                "frames": round(cfg["distractor_duration_seconds"][i % 3] * rate),
                "background_seed": seed + 500 + i,
                "parts": [
                    {
                        "preset": preset,
                        "phrase": i % 3,
                        "pitch": (i % 7) - 3,
                        "seed": seed + 600 + i,
                        "first": round((0.07 + (i % 3) * 0.31) * rate),
                        "family": None,
                    }
                ],
            }
        )
    specs.append(
        {
            "id": "hybrid",
            "group": "c02-hybrid",
            "frames": round(6.4 * rate),
            "background_seed": seed + 800,
            "parts": [
                {**specs[2]["parts"][0], "first": round(0.11 * rate)},
                {**specs[4]["parts"][0], "first": round(3.77 * rate)},
            ],
        }
    )
    sources = []
    for spec in specs:
        x, _, parts = reconstruct(spec, rate)
        a = audio(budget, owner, spec["id"], x, rate)
        source = public(a, spec["id"], spec["group"])
        source.update(
            group=spec["group"], rights={"permitted_use": "Generated C02 development audio"}
        )
        sources.append(
            {
                "source": source,
                "recipe": spec,
                "truth": [
                    {"family": p["family"], "bounds": [first, first + len(tone)]}
                    for p, (first, tone) in zip(spec["parts"], parts)
                ],
            }
        )
    query_audio = {}
    for f, family in enumerate(cfg["families"]):
        preset = next(p for p in presets if p["mechanism"] == family and p["variant"] == 1)
        tone, _ = rendering.render_tone(preset, 2, 3, seed + 900 + f)
        query_audio[family] = audio(budget, owner, "query-" + family, tone, rate)
        if family == "pluck":
            query_audio["attack"] = audio(
                budget, owner, "query-attack", tone[: round(0.3 * rate)], rate
            )
    for label, family in [("exact-tail", "noise"), ("agree", "harmonic")]:
        query_audio[label] = audio(budget, owner, "query-" + label, tones[family, 0], rate)
    query_audio["absent"] = audio(
        budget,
        owner,
        "query-absent",
        0.08 * np.sin(2 * np.pi * 10000 * np.arange(rendering.FRAMES) / rate),
        rate,
    )
    query_audio["silence"] = audio(budget, owner, "query-silence", np.zeros(rendering.FRAMES), rate)
    cases = []
    for name in cfg["cases"]:
        excluded = []
        families = []
        if name.startswith("one-"):
            families = [name[4:]]
            examples = [families[0]]
        elif name == "exact-tail":
            families = ["noise"]
            examples = ["exact-tail"]
        elif name == "agreement":
            families = ["harmonic"]
            examples = ["harmonic", "agree"]
        elif name == "conflict":
            families = ["pluck", "fm"]
            examples = ["pluck", "fm"]
        elif name == "repeated-variant":
            families = ["pluck"]
            examples = ["pluck", "pluck"]
        elif name == "parent-excluded":
            families = ["pluck"]
            examples = ["pluck"]
            excluded = ["c02-family-pluck", "c02-hybrid", "c02-distractor-00"]
        elif name == "boundary":
            families = ["pluck"]
            examples = ["attack"]
        else:
            examples = [name]
        positive = {}
        for item in sources:
            matching = [v["bounds"] for v in item["truth"] if v["family"] in families]
            if matching and item["source"]["group"] not in excluded:
                positive.setdefault(item["source"]["group"], []).append(
                    {"recording_id": item["source"]["recording_id"], "bounds": matching}
                )
        cases.append(
            {
                "id": name,
                "query_names": examples,
                "excluded_groups": excluded,
                "positives": positive,
                "primary": name in cfg["primary"],
                "stratum": "alternate" if name in cfg["primary"] else "diagnostic",
            }
        )
    value = {
        "schema_version": "c02-fixtures-1",
        "protocol_hash": digest(owner.protocol),
        "sources": sources,
        "queries": query_audio,
        "cases": cases,
        "rate": rate,
        "eligible_groups": len({v["source"]["group"] for v in sources}),
        "truth_kind": "familiar procedural development; no human relevance or fresh holdout",
    }
    if (
        len(sources) != cfg["candidate_recordings"]
        or value["eligible_groups"] != cfg["candidate_groups"]
    ):
        raise InputError("C02 prospective development population differs")
    owner.publish(budget, path, value, immutable=True)
    return {"status": "ok", "sources": len(sources), "groups": value["eligible_groups"]}


def geometry(budget, owner):
    fixtures = record(owner.directory / "development/fixtures.json")
    answers = []
    for item in fixtures["sources"]:
        a = item["source"]["source"]
        owner.charge(budget, read_audio_seconds=a["duration_seconds"])
        x, meta = decode(owner.root / a["local_path"], budget)
        if meta != {k: v for k, v in a.items() if k != "local_path"}:
            raise InputError("C02 saved native source differs")
        expected, bg, parts = reconstruct(item["recipe"], fixtures["rate"])
        if not np.array_equal(x[:, 0], expected.astype(np.float32)):
            raise InputError("C02 independent native reconstruction differs")
        lags = []
        for n, (first, tone) in enumerate(parts):
            isolated = x[:, 0].astype(float) - bg
            for m, (other, t) in enumerate(parts):
                if m != n:
                    isolated[other : other + len(t)] -= t
            corr = correlate(isolated, tone, method="fft")
            lag = int(correlation_lags(len(isolated), len(tone))[np.argmax(corr)])
            if lag != first:
                raise InputError("C02 independent FFT insertion lag differs")
            lags.append(lag)
        answers.append(
            {
                "recording_id": item["source"]["recording_id"],
                "audio_sha256": a["sha256"],
                "native_frames": len(x),
                "fft_lags": lags,
                "truth": item["truth"],
            }
        )
    result = {
        "schema_version": "c02-geometry-1",
        "fixtures_hash": fixtures["record_hash"],
        "passed": True,
        "native_checks": answers,
        "no_features_or_scores": True,
    }
    owner.publish(budget, owner.directory / "development/geometry.json", result, immutable=True)
    return {"status": "ok", "passed": True, "sources": len(answers)}


def encode(budget, owner, identity, samples, rate):
    path = owner.features / "development" / digest(identity)
    if path.exists():
        return load_array(path, identity, budget)[1]
    bounds = identity["bounds"]
    desc = identity["representation"]
    if np.max(np.abs(samples)) <= 1e-12:
        raise InputError("C02 silence has no feature; explicit failed diagnostic")
    budget.reserve(len(bounds) * desc["dimension"] * 4 + 65536, 768 * 1024**2 + samples.nbytes * 3)
    owner.charge(
        budget,
        feature_windows=len(bounds),
        feature_bytes=len(bounds) * desc["dimension"] * 4 + 65536,
        processed_window_seconds=sum(b - a for a, b in bounds) / rate,
    )
    owner.publish(
        budget,
        owner.directory / "development/pending" / (digest(identity) + ".json"),
        {"state": "reserved", "identity": identity, "consumer_code": identity["producer"]},
    )
    array = np.stack(
        [
            checked(owner.model(budget, desc).encode(samples[a:b], rate), desc["dimension"])
            for a, b in bounds
        ]
    )
    return save_array(path.parent, identity, array, budget)


def build(budget, owner):
    from ..search.contracts import code_identity

    fixtures = record(owner.directory / "development/fixtures.json")
    geom = record(owner.directory / "development/geometry.json")
    if not geom["passed"] or geom["fixtures_hash"] != fixtures["record_hash"]:
        raise InputError("C02 independent native geometry required before features")
    desc = frozen(budget)[-1]
    producer = code_identity()
    path = owner.directory / "development/encoded.json"
    state = (
        record(path)
        if path.exists()
        else {
            "fixtures_hash": fixtures["record_hash"],
            "producer": producer,
            "sources": {},
            "queries": {},
            "state": "pending",
        }
    )
    if state["producer"] != producer or state["fixtures_hash"] != fixtures["record_hash"]:
        raise InputError("C02 development producer/fixtures changed; retain old work")
    if state["state"] == "complete":
        raise InputError("C02 development features already complete")
    for item in [
        v for v in fixtures["sources"] if v["source"]["recording_id"] not in state["sources"]
    ][:2]:
        source = item["source"]
        a = source["source"]
        owner.charge(budget, read_audio_seconds=a["duration_seconds"])
        x, meta = decode(owner.root / a["local_path"], budget)
        if meta != {k: v for k, v in a.items() if k != "local_path"}:
            raise InputError("C02 development audio changed")
        refs = []
        for ms, hop in owner.protocol["development"]["grids"]:
            bank_hash = digest(
                {"scope": "C02 engineering only", "representation": desc, "grid": [ms, hop]}
            )
            bounds = [
                list(v)
                for v in grid(
                    len(x),
                    a["sample_rate_hz"],
                    {"window_milliseconds": ms, "hop_milliseconds": hop},
                )
            ]
            identity = {
                "version": "c02-development-feature-1",
                "audio_sha256": a["sha256"],
                "bounds": bounds,
                "representation": desc,
                "dimension": desc["dimension"],
                "bank_hash": bank_hash,
                "producer": producer,
            }
            meta = encode(budget, owner, identity, x, a["sample_rate_hz"])
            refs.append(
                {
                    "path": (owner.features / "development" / digest(identity))
                    .relative_to(owner.root)
                    .as_posix(),
                    "metadata": meta,
                }
            )
        state["sources"][source["recording_id"]] = refs
        owner.publish(budget, path, state)
    if len(state["sources"]) < len(fixtures["sources"]):
        return {"status": "ok", "state": "in_progress", "sources": len(state["sources"])}
    for name, a in fixtures["queries"].items():
        if name == "silence" or name in state["queries"]:
            continue
        owner.charge(budget, read_audio_seconds=a["duration_seconds"], query_jobs=1)
        x, meta = decode(owner.root / a["local_path"], budget)
        if meta != {k: v for k, v in a.items() if k != "local_path"}:
            raise InputError("C02 development query changed")
        identity = {
            "version": "c02-development-query-1",
            "audio_sha256": a["sha256"],
            "bounds": [[0, len(x)]],
            "representation": desc,
            "dimension": desc["dimension"],
            "producer": producer,
        }
        meta = encode(budget, owner, identity, x, a["sample_rate_hz"])
        state["queries"][name] = {
            "path": (owner.features / "development" / digest(identity))
            .relative_to(owner.root)
            .as_posix(),
            "metadata": meta,
            "example_id": a["canonical_pcm"]["sha256"],
        }
        owner.publish(budget, path, state)
    state["state"] = "complete"
    owner.publish(budget, path, state)
    return {
        "status": "ok",
        "state": "complete",
        "sources": len(state["sources"]),
        "queries": len(state["queries"]),
    }


def feature(budget, owner, ref):
    array, meta = load_array(owner.root / ref["path"], ref["metadata"]["identity"], budget)
    if meta != ref["metadata"]:
        raise InputError("C02 development feature record changed")
    return array


def true_passage(row, case):
    return any(
        row["recording_id"] == t["recording_id"]
        and fusion.intersects(row["original_bounds"], b) >= (b[1] - b[0]) * 0.5
        for t in case["positives"].get(row["group"], [])
        for b in t["bounds"]
    )


def coverage(ranking, case, k, cfg):
    positive = set(case["positives"])
    top = ranking[:k]
    found = positive & {g["group"] for g in top}
    details = []
    passage_groups = set()
    for group in top:
        for t in case["positives"].get(group["group"], []):
            for c in group["passages"]:
                r = c["representative"]
                if r["recording_id"] != t["recording_id"]:
                    continue
                a = r["original_bounds"]
                for b in t["bounds"]:
                    overlap = fusion.intersects(a, b)
                    union = max(a[1], b[1]) - min(a[0], b[0])
                    good = overlap >= (b[1] - b[0]) * 0.5
                    if good:
                        passage_groups.add(group["group"])
                    details.append(
                        {
                            "group": group["group"],
                            "recording_id": r["recording_id"],
                            "scored": a,
                            "truth": b,
                            "half_truth_overlap": good,
                            "contains": a[0] <= b[0] and a[1] >= b[1],
                            "iou": overlap / union,
                            "boundary_error_frames": [abs(a[0] - b[0]), abs(a[1] - b[1])],
                        }
                    )
    return {
        "positive_groups": sorted(positive),
        "found_positive_groups": sorted(found),
        "passage_positive_groups": sorted(passage_groups),
        "eligible_positive_count": len(positive),
        "hit_at_least_one": None if not positive else bool(found),
        "recall_all_positives": None if not positive else len(found) / len(positive),
        "passage_hit": None if not positive else bool(passage_groups),
        "localization": details,
    }


def compare(budget, owner):
    from ..search.contracts import code_identity

    fixtures = record(owner.directory / "development/fixtures.json")
    encoded = record(owner.directory / "development/encoded.json")
    if encoded["state"] != "complete" or encoded["producer"] != code_identity():
        raise InputError("C02 comparison requires complete unchanged development features")
    path = owner.directory / "development/comparison.json"
    if path.exists():
        raise InputError("C02 fixed comparison closed; no replacement batch")
    pending = owner.directory / "development/comparison-progress.json"
    if pending.exists():
        state = record(pending)
    else:
        owner.charge(budget, comparison_batches=1, query_jobs=36, case_policy_evaluations=36)
        state = {
            "fixtures_hash": fixtures["record_hash"],
            "encoded_hash": encoded["record_hash"],
            "cases": {},
        }
        owner.publish(budget, pending, state)
    if state["encoded_hash"] != encoded["record_hash"]:
        raise InputError("C02 comparison inputs changed")
    for case in [v for v in fixtures["cases"] if v["id"] not in state["cases"]][:1]:
        if case["id"] == "silence":
            outcome = {
                "case": case,
                "arms": {
                    a: {"state": "failed-silence", "reason": "no valid nonzero query feature"}
                    for a in owner.protocol["fusion"]["arms"]
                },
            }
        else:
            unique = {
                encoded["queries"][n]["example_id"]: encoded["queries"][n]
                for n in case["query_names"]
            }
            variants = sorted(unique)
            features = np.stack([feature(budget, owner, unique[n])[0] for n in variants])
            event_map = fusion.events(variants)
            values = []
            generated_positive = {}
            banks = []
            query = {
                "examples": [
                    {"audio": fixtures["queries"][case["query_names"][0]]} for _ in variants
                ]
            }
            for item in fixtures["sources"]:
                source = item["source"]
                rid = source["recording_id"]
                value = {
                    "source_id": rid,
                    "group": source["group"],
                    "source_ref": {"development_source": rid},
                    "objectives": {},
                    "opportunities": {},
                    "baseline": None,
                    "excluded": source["group"] in case["excluded_groups"],
                }
                if value["excluded"]:
                    values.append(value)
                    continue
                for b, ref in enumerate(encoded["sources"][rid]):
                    arr = feature(budget, owner, ref)
                    identity = ref["metadata"]["identity"]
                    bh = identity["bank_hash"]
                    if bh not in banks:
                        banks.append(bh)
                    per, means = distances(features, arr, "cosine")
                    for i, bounds in enumerate(identity["bounds"]):
                        passage = {
                            "row_id": digest([bh, rid, bounds]),
                            "bank_id": bh,
                            "signal_id": rid,
                            "shard": digest(identity),
                            "row": i,
                            "signal_bounds": bounds,
                            "original_bounds": bounds,
                            "padding_is_support": False,
                        }
                        row = engine.evidence(source, bh, passage, per[:, i], means[i])
                        if true_passage(row, case):
                            generated_positive.setdefault(bh, set()).add(source["group"])
                        if b == 0:
                            from ..indexing.ranking import hit

                            candidate = hit(source, query, per[:, i], means[i], passage)
                            if value["baseline"] is None or timbre_key(candidate) < timbre_key(
                                value["baseline"]
                            ):
                                value["baseline"], value["baseline_row"] = candidate, row
                        for q, variant in enumerate(variants):
                            obj = value["objectives"].setdefault(
                                bh + ":" + variant, {"count": 0, "rows": []}
                            )
                            obj["count"] += 1
                            obj["rows"] = fusion.retain(
                                [*obj["rows"], {**row, "distance": float(per[q, i])}],
                                owner.cfg["raw_support_cap"],
                            )
                    value["opportunities"][bh] = len(arr)
                values.append(value)
            groups = engine.group_sources(values, owner.cfg)
            supports = {
                g: owner.put(budget, "development/group-supports", v) for g, v in groups.items()
            }
            arms = {}
            for arm in owner.protocol["fusion"]["arms"]:
                ranking = fusion.results(groups, event_map, banks, owner.cfg, arm)
                selected = banks if arm == "event-multi" else banks[:1]
                generated = set().union(*(generated_positive.get(b, set()) for b in selected))
                retained = {
                    g
                    for g, v in groups.items()
                    if any(
                        true_passage(r, case)
                        for key, obj in v["objectives"].items()
                        if key.split(":")[0] in selected
                        for r in obj["rows"]
                    )
                }
                if arm == "legacy-mean":
                    retained = {
                        g for g, v in groups.items() if true_passage(v["baseline_row"], case)
                    }
                consolidated = set(
                    coverage(ranking, case, len(ranking), owner.cfg)["passage_positive_groups"]
                )
                final = set(coverage(ranking, case, 20, owner.cfg)["passage_positive_groups"])
                arms[arm] = {
                    "state": "complete",
                    "eligible_groups": len(groups),
                    "complete_order": [r["group"] for r in ranking],
                    "coverage": {
                        str(k): coverage(ranking, case, k, owner.cfg) for k in (1, 5, 10, 20)
                    },
                    "support_truncated_groups": sum(v["support_truncated"] for v in ranking),
                    "opportunities": {g: v["opportunities"] for g, v in groups.items()},
                    "complete_support_digest": digest(groups),
                    "passage_loss_decomposition": {
                        "positive_groups": sorted(case["positives"]),
                        "generation": sorted(generated),
                        "retained_support": sorted(retained),
                        "after_grouping": sorted(consolidated),
                        "shortlist20": sorted(final),
                        "generation_misses": sorted(set(case["positives"]) - generated),
                        "support_selection_losses": sorted(generated - retained),
                        "grouping_losses": sorted(retained - consolidated),
                        "shortlist_losses": sorted(consolidated - final),
                        "support_selection": "mean winner"
                        if arm == "legacy-mean"
                        else "top16 per event/variant/bank/group",
                    },
                }
            outcome = {
                "case": case,
                "events": event_map,
                "arms": arms,
                "complete_supports": supports,
            }
        state["cases"][case["id"]] = owner.put(budget, "development/outcomes", outcome)
        owner.publish(budget, pending, state)
    if len(state["cases"]) < len(fixtures["cases"]):
        return {"status": "ok", "state": "in_progress", "cases": len(state["cases"])}
    result = {
        "schema_version": "c02-comparison-1",
        "fixtures_hash": fixtures["record_hash"],
        "encoded_hash": encoded["record_hash"],
        "cases": state["cases"],
        "primary_cases": owner.protocol["development"]["primary"],
        "interpretation": (
            "familiar development, forced candidates, no relevance promotion; baseline "
            "remains default"
        ),
    }
    owner.publish(budget, path, result, immutable=True)
    return {"status": "ok", "state": "complete", "cases": len(state["cases"]), "evaluations": 36}
