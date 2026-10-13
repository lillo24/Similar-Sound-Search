"""Prospective geometry controls and atomic paired protocol/suite revision."""

import math

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..evaluation.scoring import event_matches, score
from ..storage import InputError, digest
from .windows import POLICY, routes

OLD_PROTOCOL = "b5fd2d1e87040e8a9b929a65a4b3a2d92ae69e99dfab88e3e0c87c28aa70093d"
OLD_SUITE = "59b781f3fbf75a7bad52f49c051e02142528f402cbde1c74041927ef4f081a2a"


def prediction(protocol, suite, method, config, outputs, kind="harness_control", cost=None):
    return {
        "schema_version": "a04-predictions-1",
        "protocol_hash": protocol["record_hash"],
        "suite_hash": suite["record_hash"],
        "run_id": "a05-development-" + method,
        "method_id": method,
        "configuration": config,
        "config_hash": digest(config),
        "split": "development",
        "coordinate_basis": "decoded_available_file",
        "score_direction": "lower_better",
        "evidence_kind": kind,
        "queries": outputs,
        "cost": cost
        or {
            "wall_seconds": 0,
            "processed_audio_seconds": 0,
            "storage_bytes": 0,
            "peak_working_bytes_estimate": 0,
        },
        "human_predictions": [],
    }


def controls(protocol, suite, assets, budget):
    _, query_routes = routes(suite, assets)
    by_query = {q["query_id"]: q for q in suite["queries"]}
    rng = np.random.default_rng(42105)
    results = {}
    for name in ("constant", "random"):
        outputs = []
        for q in query_routes:
            values = []
            random_scores = rng.permutation(len(q["pool"]))
            for i, p in enumerate(q["pool"]):
                values.append(
                    {k: p[k] for k in ("asset_id", "start_frame", "end_frame")}
                    | {"score": 0.0 if name == "constant" else float(random_scores[i])}
                )
            outputs.append({"query_id": q["query_id"], "candidate": values, "refined": []})
        pred = prediction(
            protocol, suite, name, {"grid": POLICY, "seed": 42105, "control": name}, outputs
        )
        directory = budget.root / "data/runs/matchers"
        write_record(directory / (name + "-predictions.json"), pred, budget)
        results[name] = score(pred, protocol, suite, assets)
        write_record(directory / (name + "-scores.json"), results[name], budget)
    geometry = {}
    for condition in ("source_consistency:-12", "source_consistency:0", "source_consistency:12"):
        rows = []
        for q in query_routes:
            truth = by_query[q["query_id"]]
            if truth["condition"] != condition:
                continue
            n = len(q["pool"])
            m = sum(bool(event_matches([p], truth["targets"])) for p in q["pool"])
            rows.append(
                {
                    "windows": n,
                    "matching_windows": m,
                    "random_expected_hit": {
                        str(k): 1
                        - (
                            math.comb(n - m, min(k, n)) / math.comb(n, min(k, n))
                            if min(k, n) <= n - m
                            else 0
                        )
                        for k in protocol["k"]
                    },
                }
            )
        geometry[condition] = rows
    return {
        "geometry": geometry,
        "controls": results,
        "random_is": "one seeded order; analytical expectation separately calculated",
        "model_scores_inspected": False,
    }


def revise(budget):
    directory = budget.root / "manifests/evaluation"
    atomic = directory / "comparison.json"
    if atomic.exists():
        bundle = record(atomic)
        for name in ("protocol", "suite"):
            write_record(directory / (name + ".json"), bundle[name], budget)
        return {
            "status": "ok",
            "reused": True,
            "protocol_hash": bundle["protocol"]["record_hash"],
            "suite_hash": bundle["suite"]["record_hash"],
        }
    if (budget.root / "manifests/matchers/choice.json").exists() or any(
        (budget.root / "data/runs/matchers" / (m + "-predictions.json")).exists()
        for m in ("acoustic", "efficientat")
    ):
        raise InputError(
            "protocol revision: model choice already exists; cannot claim prospective freeze"
        )
    protocol, suite = record(directory / "protocol.json"), record(directory / "suite.json")
    if protocol["record_hash"] != OLD_PROTOCOL or suite["record_hash"] != OLD_SUITE:
        raise InputError("A05 correction: expected original A04 protocol/suite identity")
    assets = {k: record(directory / "assets" / (k + ".json")) for k in suite["assets"]}
    audit = controls(protocol, suite, assets, budget)
    for condition, rows in audit["geometry"].items():
        expected = 8 if condition.endswith(":-12") else 7
        if (
            len(rows) != 8
            or any(r["windows"] != 24 or r["matching_windows"] != expected for r in rows)
            or audit["controls"]["constant"]["conditions"][condition]["stages"]["candidate"][
                "at_k"
            ]["10"]["hit_rate"]
            != 1
        ):
            raise InputError("A05 prospective geometry audit differs from reviewed counts")
    write_record(budget.root / "manifests/matchers/geometry-before.json", audit, budget)
    write_record(directory / "protocol-history" / (OLD_PROTOCOL + ".json"), protocol, budget)
    write_record(directory / "suite-history" / (OLD_SUITE + ".json"), suite, budget)
    protocol.pop("record_hash")
    protocol.update(
        {
            "protocol_version": "2026-10-13.1",
            "comparison_interval_policy": POLICY,
            "comparison_revision": {
                "prior_protocol": OLD_PROTOCOL,
                "prior_suite": OLD_SUITE,
                "reason": "hit@10 geometry saturation; prospective A05 correction",
            },
        }
    )
    protocol["selection_rule"]["primary"] = (
        "macro mean candidate query hit rate at K=1 over the three "
        "source_consistency mixture levels"
    )
    protocol["record_hash"] = digest(protocol)
    suite.pop("record_hash")
    suite["protocol_hash"] = protocol["record_hash"]
    suite["record_hash"] = digest(suite)
    # One atomic record commits both identities; canonical files are recoverable mirrors.
    write_record(
        atomic, {"schema_version": "a05-comparison-1", "protocol": protocol, "suite": suite}, budget
    )
    for name, value in (("protocol", protocol), ("suite", suite)):
        write_record(directory / (name + ".json"), value, budget)
    return {
        "status": "ok",
        "reused": False,
        "protocol_hash": protocol["record_hash"],
        "suite_hash": suite["record_hash"],
        "geometry": "verified through original real scorer before models",
    }
