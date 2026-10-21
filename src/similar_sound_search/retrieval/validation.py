"""Independent scalar known answers and explicitly scoped historical HPSS checks."""

import math

import numpy as np

from ..evaluation.artifacts import record
from ..indexing import banks, build, reader
from ..search import sources
from ..search.contracts import code_identity
from ..search.ranking import distances, excluded_source
from ..storage import InputError, digest
from . import development, engine, fusion, history


def oracle_fixture():
    query = np.eye(2, dtype=np.float32)
    vectors = [np.asarray([1, 0], np.float32), np.asarray([0, 1], np.float32)]
    candidates = [("needed", 0, vectors[0]), ("needed", 30, vectors[1])]
    candidates.extend((f"decoy-{n:02}", 0, np.asarray([1, 1], np.float32)) for n in range(32))
    groups = {}
    per, means = distances(query, np.stack([v[2] for v in candidates]), "cosine")
    for i, (group, first, vector) in enumerate(candidates):
        target = groups.setdefault(
            group,
            {
                "baseline": None,
                "baseline_row": None,
                "opportunities": {"legacy": 0},
                "objectives": {},
            },
        )
        target["opportunities"]["legacy"] += 1
        row = {
            "row_id": digest([group, first]),
            "distance": float(means[i]),
            "recording_id": group,
            "original_bounds": [first, first + 10],
            "bank_hash": "legacy",
            "rate": 10,
        }
        if target["baseline"] is None or means[i] < target["baseline"]["timbre_distance"]:
            target["baseline"] = {
                "timbre_distance": float(means[i]),
                "recording_id": group,
                "start_frame": first,
                "end_frame": first + 10,
            }
            target["baseline_row"] = row
        for q, variant in enumerate(("a", "b")):
            # Independent scalar cosine, not the vectorized reduction being tested.
            numerator = math.fsum(float(x) * float(y) for x, y in zip(query[q], vector))
            expected = 1 - numerator / (
                math.sqrt(math.fsum(float(x) ** 2 for x in query[q]))
                * math.sqrt(math.fsum(float(x) ** 2 for x in vector))
            )
            if abs(per[q, i] - expected) > 1e-15:
                raise InputError("C02 scalar cosine oracle disagrees")
            obj = target["objectives"].setdefault("legacy:" + variant, {"count": 0, "rows": []})
            obj["count"] += 1
            obj["rows"].append({**row, "distance": expected})
            obj["rows"].sort(key=fusion.row_key)
    return groups, {"a": ["a"], "b": ["b"]}


def known_answer():
    cfg = dict(
        raw_support_cap=16,
        passages_per_track=3,
        rrf_constant=60,
        overlap_fraction=0.5,
        max_span_seconds=8,
    )
    groups, events = oracle_fixture()
    old = fusion.results(groups, events, ["legacy"], cfg, "legacy-mean")
    new = fusion.results(groups, events, ["legacy"], cfg, "event-legacy")
    if (
        "needed" in {v["group"] for v in old[:20]}
        or new[0]["group"] != "needed"
        or new[0]["score"] != 1
    ):
        raise InputError("C02 per-event recovery/contribution oracle failed")
    if len(new[0]["passages"]) != 2:
        raise InputError("C02 disjoint-event support oracle failed")
    reversed_groups = dict(reversed(list(groups.items())))
    if (
        fusion.results(
            reversed_groups,
            dict(reversed(list(events.items()))),
            ["legacy", "legacy"],
            cfg,
            "event-legacy",
        )
        != new
    ):
        raise InputError("C02 order/copied-bank invariance oracle failed")
    base = {
        "distance": 0.0,
        "recording_id": "r",
        "bank_hash": "b",
        "rate": 10,
        "credit": 1.0,
        "variant_id": "q",
    }
    rows = [
        {**base, "row_id": str(i), "original_bounds": [a, a + 10]}
        for i, a in enumerate((0, 5, 10, 40))
    ]
    selected, info = fusion.consolidate(rows, cfg)
    if [v["scored_bounds"] for v in selected] != [[0, 10], [10, 20], [40, 50]] or info[
        "clusters"
    ] != 3:
        raise InputError("C02 anchored nontransitive grouping oracle failed")
    return {
        "status": "ok",
        "passed": True,
        "checks": [
            "exhaustive scalar cosine",
            "33-group mean-loss/event-recovery",
            "independent reciprocal-rank arithmetic",
            "disjoint support",
            "order/duplicate-bank invariance",
            "anchored chain/endpoints",
        ],
    }


def diagnostics(budget, owner):
    output = owner.directory / "development/representation-diagnostics.json"
    if output.exists():
        raise InputError("C02 scoped representation diagnostics already closed")
    pending = owner.directory / "development/diagnostic-pending.json"
    if not pending.exists():
        owner.charge(budget, query_jobs=2, case_policy_evaluations=2)
        owner.publish(budget, pending, {"state": "pending"}, immutable=True)
    view = history.BankView(owner)
    snapshot = record(view.indexes / "snapshots" / (owner.protocol["snapshot"] + ".json"))
    qref = next(
        v
        for v in snapshot["engineering_banks_outside_discovery"]
        if v["kind"]["component"] == "harmonic"
    )
    qb = reader.read_bank(budget, view, owner.root / qref["path"], True)
    signal = next(iter(qb["signals"].values()))
    build.load_signal(budget, view, signal)
    original = sources.load(budget, signal["original"], context=owner)
    qa, qrows = reader.rows(budget, view, qb, qb["committed"][0])
    native = qrows[0]["original_bounds"]
    if banks.original_bounds(signal, qrows[0]["signal_bounds"]) != native:
        raise InputError("C02 component association native map differs")
    audio = development.audio(
        budget,
        owner,
        "diagnostic-original-query",
        original[native[0] : native[1]],
        signal["audio"]["sample_rate_hz"],
    )
    desc = qb["bank"]["identity"]["representation"]
    identity = {
        "version": "c02-diagnostic-query-1",
        "audio_sha256": audio["sha256"],
        "bounds": [[0, native[1] - native[0]]],
        "representation": desc,
        "dimension": desc["dimension"],
        "producer": code_identity(),
    }
    development.encode(
        budget, owner, identity, original[native[0] : native[1]], audio["sample_rate_hz"]
    )
    from ..search.contracts import load_array

    orig = load_array(owner.features / "development" / digest(identity), identity, budget)[0][0]
    ids = [
        audio["canonical_pcm"]["sha256"],
        digest([signal["transformation"]["record_hash"], qrows[0]["row_id"]]),
    ]
    witness = {
        "source_pcm": signal["original"]["source"]["canonical_pcm"]["sha256"],
        "native_bounds": native,
        "rate": signal["original"]["source"]["sample_rate_hz"],
    }
    event_map = fusion.events(ids, {v: witness for v in ids})
    vectors = dict(zip(ids, [orig, qa[0]]))
    variants = sorted(vectors)
    features = np.stack([vectors[v] for v in variants])
    exclusions = set(signal.get("ancestry_groups", [])) | {signal["original"]["group"]}
    query = {
        "identity": {"excluded_groups": sorted(exclusions)},
        "examples": [
            {
                "audio": audio,
                "prepared": {
                    "source": signal["original"]["source"],
                    "technical_metadata": signal["original"]["source"],
                },
            }
            for _ in variants
        ],
    }
    values = []
    bank_ids = []
    for ref in snapshot["banks"]:
        if not isinstance(ref["kind"], dict):
            continue
        value = reader.read_bank(budget, view, owner.root / ref["path"], True)
        bank_ids.append(ref["record_hash"])
        sig = next(iter(value["signals"].values()))
        source = sig["original"]
        build.load_signal(budget, view, sig)
        excluded = excluded_source(source, query) or bool(
            exclusions & set(sig.get("ancestry_groups", []))
        )
        entry = {
            "source_id": source["recording_id"],
            "group": source["group"],
            "source_ref": owner.put(
                budget, "sources", {"schema_version": "c02-source-1", "source": source}
            ),
            "objectives": {},
            "opportunities": {},
            "baseline": None,
            "excluded": excluded,
        }
        if not excluded:
            for unit in value["committed"]:
                array, rows = reader.rows(budget, view, value, unit)
                per, means = distances(features, array, "cosine")
                for i, row in enumerate(rows):
                    for q, variant in enumerate(variants):
                        obj = entry["objectives"].setdefault(
                            ref["record_hash"] + ":" + variant, {"count": 0, "rows": []}
                        )
                        obj["count"] += 1
                        obj["rows"].append(
                            engine.evidence(source, ref["record_hash"], row, per[:, i], per[q, i])
                        )
                    from ..indexing.ranking import hit

                    h = hit(source, query, per[:, i], means[i], row)
                    if (
                        entry["baseline"] is None
                        or h["timbre_distance"] < entry["baseline"]["timbre_distance"]
                    ):
                        entry["baseline"], entry["baseline_row"] = (
                            h,
                            engine.evidence(source, ref["record_hash"], row, per[:, i], means[i]),
                        )
                entry["opportunities"][ref["record_hash"]] = len(array)
            for obj in entry["objectives"].values():
                obj["rows"] = fusion.retain(obj["rows"], owner.cfg["raw_support_cap"])
        values.append(entry)
    groups = engine.group_sources(values, owner.cfg)
    a = fusion.results(groups, event_map, bank_ids, owner.cfg, "event-multi")
    b = fusion.results(groups, event_map, bank_ids + bank_ids, owner.cfg, "event-multi")
    if a != b or len(event_map) != 1:
        raise InputError("C02 correlated/copy diagnostic changed credits")
    result = {
        "schema_version": "c02-representation-diagnostics-1",
        "passed": True,
        "association": witness,
        "query_original": audio,
        "query_component": signal,
        "event_map": event_map,
        "excluded_groups": sorted(exclusions),
        "scoped_eligible_groups": len(groups),
        "bank_refs": bank_ids,
        "results": a,
        "copy_reference_invariant": True,
        "two_variants_one_event": True,
        "scope": (
            "two partial one-region HPSS banks only; no full-catalogue ranks, presence "
            "or quality claim"
        ),
        "new_separator_processing": 0,
    }
    owner.publish(budget, output, result, immutable=True)
    return {
        "status": "ok",
        "passed": True,
        "events": 1,
        "variants": 2,
        "eligible_groups": len(groups),
    }
