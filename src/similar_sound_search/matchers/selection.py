"""Scoring joins only persisted predictions; frozen development ordering and choice."""

import numpy as np

from ..evaluation.artifacts import record, write_record
from ..evaluation.scoring import event_matches, ranked, score
from ..storage import InputError
from .correction import controls


def criteria(result):
    if (
        result.get("status") != "ok"
        or result["evidence_kind"] != "matcher"
        or result["provided_queries"] != 80
        or result["expected_queries"] != 80
    ):
        raise InputError("A05 selection: only successful complete 80-query matcher runs eligible")
    groups = result["conditions"]
    primary = float(
        np.mean(
            [
                groups["source_consistency:" + level]["stages"]["candidate"]["at_k"]["1"][
                    "hit_rate"
                ]
                for level in ("-12", "0", "12")
            ]
        )
    )
    secondary = float(
        np.mean(
            [
                groups[c]["stages"]["candidate"]["at_k"]["5"]["hit_rate"]
                for c in ("performance", "pitch")
            ]
        )
    )
    old = float(
        np.mean(
            [
                groups["source_consistency:" + level]["stages"]["candidate"]["at_k"]["10"][
                    "hit_rate"
                ]
                for level in ("-12", "0", "12")
            ]
        )
    )
    return {
        "primary_hit_at_1": primary,
        "secondary_hit_at_5": secondary,
        "former_primary_hit_at_10": old,
        "model_wall_seconds": result["model_cost"]["wall_seconds"],
    }


def choose(results):
    eligible = [(criteria(r), r) for r in results]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda pair: (
            -pair[0]["primary_hit_at_1"],
            -pair[0]["secondary_hit_at_5"],
            pair[0]["model_wall_seconds"],
            pair[1]["method_id"],
            pair[1]["config_hash"],
        ),
    )[1]


def family_report(pred, suite, assets, protocol):
    outputs = {q["query_id"]: q for q in pred["queries"]}
    result = {}
    for q in suite["queries"]:
        if q["split"] != "development" or not q["condition"].startswith("source_consistency:"):
            continue
        family = assets[q["query_asset_id"]]["families"][0]
        group = result.setdefault(
            family, {"queries": 0, "targets": 0, "hit_queries_at_1": 0, "recovered_targets_at_1": 0}
        )
        values = ranked(outputs[q["query_id"]]["candidate"], pred["score_direction"], assets)[:1]
        matches = event_matches(values, q["targets"], protocol["matching"]["minimum_iou"])
        group["queries"] += 1
        group["targets"] += len(q["targets"])
        group["hit_queries_at_1"] += bool(matches)
        group["recovered_targets_at_1"] += len(matches)
    return result


def compare(budget, protocol, suite, assets, frozen):
    control = controls(protocol, suite, assets, budget)
    results, details = [], {}
    for method in frozen["methods"]:
        path = budget.root / "data/runs/matchers" / (method + "-predictions.json")
        progress_path = budget.root / "data/runs/matchers" / (method + "-progress.json")
        progress = record(progress_path) if progress_path.exists() else None
        if not path.exists() or not progress or progress.get("state") != "complete":
            details[method] = {
                "state": "incomplete",
                "reason": "successful complete progress and persisted predictions required",
            }
            continue
        pred = record(path)
        if (
            pred["configuration"] != frozen["methods"][method]
            or progress["shortlist_hash"] != frozen["record_hash"]
            or pred["cost"] != progress["cost"]
        ):
            raise InputError("comparison: prediction configuration differs from frozen shortlist")
        result = score(pred, protocol, suite, assets)
        results.append(result)
        write_record(budget.root / "data/runs/matchers" / (method + "-scores.json"), result, budget)
        details[method] = {
            "state": "complete",
            "criteria": criteria(result),
            "per_family_source_consistency": family_report(pred, suite, assets, protocol),
            "model_cost": result["model_cost"],
            "conditions": {
                name: {
                    "queries": g["queries"],
                    "targets": g["targets"],
                    "at_k": {
                        k: {
                            field: m[field]
                            for field in (
                                "hit_queries",
                                "query_denominator",
                                "hit_rate",
                                "recovered_targets",
                                "target_denominator",
                                "target_coverage",
                                "missed_targets",
                                "mean_absolute_boundary_error_seconds",
                            )
                        }
                        for k, m in g["stages"]["candidate"]["at_k"].items()
                    },
                    "first_target_ranks": g["stages"]["candidate"]["first_target_ranks"],
                    "absent_top_scores": g["stages"]["candidate"]["absent_top_scores"],
                }
                for name, g in result["conditions"].items()
            },
        }
    selected = choose(results)
    control_primary = {
        name: float(
            np.mean(
                [
                    r["conditions"]["source_consistency:" + level]["stages"]["candidate"]["at_k"][
                        "1"
                    ]["hit_rate"]
                    for level in ("-12", "0", "12")
                ]
            )
        )
        for name, r in control["controls"].items()
    }
    value = {
        "schema_version": "a05-comparison-report-1",
        "protocol_hash": protocol["record_hash"],
        "suite_hash": suite["record_hash"],
        "methods": details,
        "control_primary": control_primary,
        "human": "unavailable: Grey1977 remains quarantined",
        "uncertainty": "descriptive family groups; no independent-window significance",
        "held_out_model_scores": False,
    }
    write_record(budget.root / "manifests/matchers/comparison.json", value, budget)
    choice = {
        "schema_version": "a05-choice-1",
        "stage": "A05",
        "selected_on": "development",
        "protocol_hash": protocol["record_hash"],
        "suite_hash": suite["record_hash"],
        "shortlist_hash": frozen["record_hash"],
        "method_id": selected["method_id"] if selected else None,
        "config_hash": selected["config_hash"] if selected else None,
        "configuration": frozen["methods"][selected["method_id"]] if selected else None,
        "development_runs": {m: details[m].get("criteria") for m in details},
        "exclusions": frozen["exclusions"],
        "control_primary": control_primary,
        "outperforms_both_controls": criteria(selected)["primary_hit_at_1"]
        > max(control_primary.values())
        if selected
        else False,
        "limitations": (
            "provisional controlled-source evidence; placement bias; four related "
            "families, reused backgrounds; no human evidence, cross-song test, "
            "Loulou or held-out claim; unknown pretraining overlap"
        ),
    }
    write_record(budget.root / "manifests/matchers/choice.json", choice, budget)
    return {
        "status": "ok",
        "selected": choice["method_id"],
        "outperforms_both_controls": choice["outperforms_both_controls"],
        "methods": {m: details[m].get("criteria", details[m]) for m in details},
        "control_primary": control_primary,
        "stage": "A05",
    }
