"""One prospectively fixed development batch; shared adapter, distances and A04 scorer."""

import hashlib
import time

import numpy as np
from scipy.io.wavfile import write as write_wav

from ..evaluation.artifacts import load_asset, record, write_record
from ..evaluation.protocol import comparison_pair
from ..evaluation.scoring import score
from ..matchers import cache
from ..matchers.acoustic import checked
from ..matchers.models import adapter
from ..matchers.runner import memory_check
from ..matchers.windows import add_route
from ..search.contracts import code_identity, frozen, grid, load_array, save_array
from ..search.ranking import distances
from ..storage import InputError, digest, sha256
from .artifacts import recipe
from .detector import propose
from .fixtures import boundary_cases
from .metrics import aggregate, boundaries
from .selection import automatic


class Features:
    """Read A05 cache only; B01 misses have their own bounded immutable array owner."""

    def __init__(self, budget, context, desc):
        self.budget, self.context, self.desc = budget, context, desc
        self.model = None
        self.reused, self.created = 0, 0

    def get(self, asset, samples, first, last):
        routes = {}
        route = add_route(routes, asset, first, last)
        cached = cache.get(self.budget, routes[route], self.desc)
        if cached is not None:
            self.reused += 1
            return cached[0]
        identity = {
            "version": "b01-comparison-feature-1",
            "route": routes[route],
            "representation": self.desc,
            "dimension": self.desc["dimension"],
        }
        directory = self.budget.root / "data/features/events/comparison"
        path = directory / digest(identity)
        if path.exists():
            self.reused += 1
            return load_array(path, identity, self.budget)[0][0]
        rate = asset["audio"]["sample_rate_hz"]
        self.context.charge(
            self.budget,
            feature_windows=1,
            feature_bytes=self.desc["dimension"] * 4 + 65536,
            processed_window_seconds=(last - first) / rate,
        )
        self.budget.reserve(self.desc["dimension"] * 4 + 65536, 768 * 1024**2 + samples.nbytes * 3)
        if self.model is None:
            self.model, _ = adapter(self.budget, "efficientat", self.desc)
        value = checked(self.model.encode(samples[first:last], rate), self.desc["dimension"])
        save_array(directory, identity, value[None], self.budget)
        self.created += 1
        return value

    def query(self, asset, samples, intervals):
        unique = {}
        for first, last in intervals:
            crop = np.ascontiguousarray(samples[first:last], dtype=np.float32)
            if not np.any(crop):
                continue  # explicit silence abstention, not an inference fallback
            key = digest(
                [
                    asset["audio"]["sample_rate_hz"],
                    crop.shape[1],
                    hashlib.sha256(crop.tobytes()).hexdigest(),
                ]
            )
            if key not in unique:
                unique[key] = (first, last)
        return (
            np.stack([self.get(asset, samples, *unique[k]) for k in sorted(unique)])
            if unique
            else None
        )


def load(budget, context, key):
    metadata = record(budget.root / "manifests/evaluation/assets" / (key + ".json"))
    if metadata["split"] != "development":
        raise InputError("B01 comparison accepts development assets only")
    context.charge(budget, read_audio_seconds=metadata["audio"]["duration_seconds"])
    return load_asset(budget.root, key, budget)


def compare_case(budget, context, case, original_query, desc, settings, directory):
    started = time.perf_counter()
    samples, reference = load(budget, context, case["reference_asset"])
    first, last = case["region"]
    if case["silence"]:
        samples = np.zeros_like(samples)
        # A separate B01 waveform identity prevents cache reuse of the non-silent parent.
        reference = {
            **reference,
            "asset_id": digest(["b01-silence", reference["asset_id"]]),
            "audio": {
                **reference["audio"],
                "sha256": hashlib.sha256(samples.tobytes()).hexdigest(),
                "canonical_pcm": {"b01_synthetic_silence": True},
            },
        }
    context.charge(budget, proposal_inputs=1)
    detection = propose(samples, reference["audio"]["sample_rate_hz"], first, last, context.cfg)
    context.charge(budget, proposed_events=len(detection["events"]))
    selected = automatic(detection["events"], context.cfg)
    # Selection is complete before any retrieval distances, with no truth passed
    # to the proposer or automatic selector. Oracle is a separately labelled mode.
    write_record(
        directory / (case["query_id"] + "-selection.json"),
        {"case": case, "detection": detection, "selected": selected},
        budget,
    )
    features = Features(budget, context, desc)
    pool, vectors = [], []
    search_cfg = record(budget.root / "manifests/search/final-check.json")["binding"][
        "search_configuration"
    ]
    for key in original_query["candidate_assets"]:
        x, asset = load(budget, context, key)
        for a, b in grid(
            asset["audio"]["sample_count"], asset["audio"]["sample_rate_hz"], search_cfg
        ):
            pool.append({"asset_id": key, "start_frame": a, "end_frame": b})
            vectors.append(features.get(asset, x, a, b))
    matrix = np.stack(vectors)
    truth = []
    if case["truth_asset"]:
        truth_record = record(
            budget.root / "manifests/evaluation/assets" / (case["truth_asset"] + ".json")
        )
        # The frozen region is the first complete insertion; A04 note ends include release.
        truth = [
            {"start_frame": first + t["start_frame"], "end_frame": first + t["end_frame"]}
            for t in truth_record["events"]
        ]
    intervals = {
        "coarse": [(first, last)],
        "single": [(e["start_frame"], e["end_frame"]) for e in selected[:1]],
        "multiple": [(e["start_frame"], e["end_frame"]) for e in selected],
        "oracle_diagnostic": [(e["start_frame"], e["end_frame"]) for e in truth],
    }
    outputs, invariance = {}, {}
    for mode, bounds in intervals.items():
        query = features.query(reference, samples, bounds)
        ranked = []
        if query is not None:
            per, mean = distances(query, matrix, desc["distance"])
            delta = float(
                np.max(np.abs(distances(query[::-1], matrix, desc["distance"])[1] - mean))
            )
            if delta > context.cfg["comparison_tolerance"]:
                raise InputError("B01 comparison: unordered distance invariance failed")
            invariance[mode] = {
                "permutation_max_absolute_error": delta,
                "unique_examples": len(query),
                "input_intervals": len(bounds),
                "per_example_distances": per.tolist(),
            }
            ranked = sorted(
                [{**p, "score": float(s)} for p, s in zip(pool, mean, strict=True)],
                key=lambda p: (p["score"], p["asset_id"], p["start_frame"], p["end_frame"]),
            )
        outputs[mode] = {"query_id": case["query_id"], "candidate": ranked, "refined": ranked[:10]}
    # Persist the predictions before evaluating note boundaries or retrieval truth.
    write_record(
        directory / (case["query_id"] + "-predictions.json"),
        {"outputs": outputs, "invariance": invariance},
        budget,
    )
    measured = boundaries(
        detection["events"], truth, reference["audio"]["sample_rate_hz"], settings
    )
    return {
        "case": case,
        "outputs": outputs,
        "note_boundaries": measured,
        "proposal_state": detection["state"],
        "selected": len(selected),
        "empty_modes": [k for k, v in outputs.items() if not v["candidate"]],
        "features_reused": features.reused,
        "features_created": features.created,
        "seconds": time.perf_counter() - started,
        "peak_working_bytes": memory_check(budget),
    }


def fixtures(budget, context, plan, directory):
    state_path = directory / "fixtures.json"
    results = record(state_path)["cases"] if state_path.exists() else []
    for case in boundary_cases():
        if case["case"] not in plan["fixture_cases"]:
            raise InputError("B01 undeclared boundary fixture")
        existing = next((v for v in results if v["case"] == case["case"]), None)
        if existing:
            if sha256(budget.root / existing["local_path"], budget) != existing["audio_sha256"]:
                raise InputError("B01 resumed fixture corrupt: " + case["case"])
            continue
        samples = case["samples"]
        context.charge(budget, proposal_inputs=1, preparation_bytes=samples.nbytes + 65536)
        detection = propose(samples, case["rate"], 0, len(samples), context.cfg)
        context.charge(budget, proposed_events=len(detection["events"]))
        path = budget.root / "data/audio/events/fixtures" / (case["case"] + ".wav")
        budget.reserve(samples.nbytes + 65536)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            from ..inputs import decode

            context.charge(budget, read_audio_seconds=len(samples) / case["rate"])
            current, metadata = decode(path, budget)
            if not np.array_equal(current, samples) or metadata["sample_rate_hz"] != case["rate"]:
                raise InputError("B01 interrupted fixture differs from exact construction")
        else:
            write_wav(path, case["rate"], samples)
        budget.refresh_disk()
        results.append(
            {k: v for k, v in case.items() if k != "samples"}
            | {
                "audio_sha256": sha256(path, budget),
                "local_path": path.relative_to(budget.root).as_posix(),
                "recipe_code": code_identity()["events/fixtures.py"],
                "detection": detection,
                "note_boundaries": boundaries(
                    detection["events"], case["truth"], case["rate"], plan["metrics"]
                ),
            }
        )
        write_record(state_path, {"cases": results}, budget)
    return results


def step(budget, context):
    plan = record(budget.root / "manifests/events/development.json")
    if plan["configuration"] != context.cfg:
        raise InputError("B01 comparison: prospective configuration changed; no tuning")
    protocol, historical_suite = comparison_pair(budget.root)
    if historical_suite["record_hash"] != plan["historical_suite_hash"]:
        raise InputError("B01 comparison: historical suite drift")
    _, _, _, _, desc = frozen(budget, "efficientat")
    identity = {
        "plan": plan["record_hash"],
        "representation": desc,
        "recipe": recipe(context),
        "comparison_code": {p: h for p, h in code_identity().items() if p.startswith("events/")},
    }
    key = digest(identity)
    directory = context.directory / "comparison"
    path = directory / "progress.json"
    if path.exists():
        state = record(path)
        if state["identity"] != identity:
            raise InputError("B01 comparison progress: code/plan changed; retain spent allowance")
    else:
        context.charge(
            budget,
            comparisons=1,
            query_jobs=1,
            comparison_cases=len(plan["cases"]),
            comparison_queries=len(plan["cases"]) * 4,
            managed_output_bytes=2 * 1024**2,
        )
        state = {"identity": identity, "cases": [], "fixtures": False}
        write_record(path, state, budget)
    queries = {q["query_id"]: q for q in historical_suite["queries"] if q["split"] == "development"}
    if len(state["cases"]) < len(plan["cases"]):
        case = plan["cases"][len(state["cases"])]
        result = compare_case(
            budget, context, case, queries[case["query_id"]], desc, plan["metrics"], directory
        )
        state["cases"].append(result)
        write_record(path, state, budget)
        return {
            "status": "ok",
            "state": "in_progress",
            "cursor": len(state["cases"]),
            "completed_cases": len(state["cases"]),
            "expected_cases": len(plan["cases"]),
        }
    if not state["fixtures"]:
        fixtures(budget, context, plan, directory)
        state["fixtures"] = True
        write_record(path, state, budget)
    fixture_results = record(directory / "fixtures.json")["cases"]
    subset = {
        **historical_suite,
        "queries": [{**queries[c["query_id"]], "condition": c["stratum"]} for c in plan["cases"]],
    }
    subset.pop("record_hash")
    subset["record_hash"] = digest(subset)
    assets = {
        k: record(budget.root / "manifests/evaluation/assets" / (k + ".json"))
        for q in subset["queries"]
        for k in q["candidate_assets"]
    }
    scores = {}
    for mode in plan["modes"]:
        prediction = {
            "schema_version": "a04-predictions-1",
            "protocol_hash": protocol["record_hash"],
            "suite_hash": subset["record_hash"],
            "run_id": key + ":" + mode,
            "method_id": "efficientat",
            "configuration": desc,
            "config_hash": digest(desc),
            "split": "development",
            "score_direction": "lower_better",
            "evidence_kind": "matcher",
            "coordinate_basis": "decoded_available_file",
            "human_predictions": [],
            "queries": [c["outputs"][mode] for c in state["cases"]],
            "cost": {
                "wall_seconds": sum(c["seconds"] for c in state["cases"]),
                "processed_audio_seconds": record(context.directory / "work.json")["counts"][
                    "processed_window_seconds"
                ],
                "storage_bytes": record(context.directory / "work.json")["counts"]["feature_bytes"],
                "peak_working_bytes_estimate": max(c["peak_working_bytes"] for c in state["cases"]),
            },
        }
        write_record(directory / (mode + "-predictions.json"), prediction, budget)
        scores[mode] = score(prediction, protocol, subset, assets)
    note = aggregate(
        [c["note_boundaries"] for c in state["cases"]]
        + [c["note_boundaries"] for c in fixture_results]
    )
    summary = {
        "schema_version": "b01-comparison-1",
        "identity": identity,
        "state": "complete",
        "cases": [{k: v for k, v in c.items() if k != "outputs"} for c in state["cases"]],
        "note_boundaries": note,
        "fixtures": fixture_results,
        "scores": scores,
        "default": "explicit/coarse",
        "automatic_status": "experimental",
        "default_reason": "Require all prospective gates; see measured decision",
    }

    def retrieval(mode, k, field):
        return sum(
            c["stages"]["candidate"]["at_k"][str(k)][field]
            for c in scores[mode]["conditions"].values()
        )

    metrics = {
        m: {
            "hit_at_1": retrieval(m, 1, "hit_queries"),
            "recovered_at_10": retrieval(m, 10, "recovered_targets"),
            "present_queries": retrieval(m, 1, "query_denominator"),
            "targets": retrieval(m, 10, "target_denominator"),
            "abstained_queries": sum(m in c["empty_modes"] for c in state["cases"]),
        }
        for m in plan["modes"]
    }
    gates = {
        "precision": (note["precision"] or 0) >= 0.8,
        "recall": (note["recall"] or 0) >= 0.8,
        "attack": (note["minimum_matched_attack_coverage"] or 0) >= 0.95,
        "tail": (note["minimum_matched_tail_coverage"] or 0) >= 0.95,
    }
    for mode in ("single", "multiple"):
        gates[mode + "_not_worse"] = all(
            metrics[mode][k] >= metrics["coarse"][k] for k in ("hit_at_1", "recovered_at_10")
        )
    gates["strict_gain"] = any(
        metrics[m][k] > metrics["coarse"][k]
        for m in ("single", "multiple")
        for k in ("hit_at_1", "recovered_at_10")
    )
    if all(gates.values()):
        summary["default"], summary["automatic_status"] = (
            "automatic proposals",
            "development supported only",
        )
    summary.update(retrieval_totals=metrics, decision_gates=gates)
    write_record(directory / "summary.json", summary, budget)
    return {
        "status": "ok",
        "comparison": (directory / "summary.json").relative_to(budget.root).as_posix(),
        "cases": len(state["cases"]),
        "default": summary["default"],
        "retrieval_totals": metrics,
        "note_boundaries": note,
    }
