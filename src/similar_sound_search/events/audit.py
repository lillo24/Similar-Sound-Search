"""Explicit post-run boundary/accounting correction; no feature inference or new queries."""

from ..evaluation.artifacts import load_asset, record, write_record
from ..evaluation.protocol import comparison_pair
from ..evaluation.scoring import score
from ..search.contracts import code_identity, frozen
from ..storage import InputError, contained, digest, read_json
from .metrics import aggregate, boundaries, reference_notes


def account_parents(budget, context):
    plan = record(budget.root / "manifests/events/accounting-audit-plan.json")
    path = context.directory / "accounting-audit.json"
    if path.exists():
        value = record(path)
        if value["plan_hash"] != plan["record_hash"]:
            raise InputError("B01 accounting audit: plan differs from retained receipt")
        return value
    seconds = 0
    for item in plan["successful_prepare_inputs_before_fix"]:
        spec = read_json(contained(budget.root / item["path"], context.directory / "extractions"))
        if digest(spec) != item["spec_hash"] or len(spec["examples"]) != len(item["examples"]):
            raise InputError("B01 accounting audit: original query handoff changed")
        for example, expected in zip(spec["examples"], item["examples"], strict=True):
            parent = record(
                contained(
                    budget.root / example["parent_record"], budget.root / "data/audio/prepared"
                )
            )
            if (
                parent["record_hash"] != expected["parent_hash"]
                or parent["source"]["sha256"] != expected["root_source_sha256"]
                or parent["source"]["duration_seconds"] != expected["root_read_seconds"]
            ):
                raise InputError("B01 accounting audit: parent/source identity changed")
            seconds += expected["root_read_seconds"]
    if seconds != plan["missed_root_read_seconds"]:
        raise InputError("B01 accounting audit: expected read total differs")
    # Charge before publishing. A crash can retain a conservative double charge,
    # never refund or conceal an initial unaccounted validation read.
    context.charge(budget, read_audio_seconds=seconds, managed_output_bytes=65536)
    value = {
        "schema_version": "b01-accounting-audit-1",
        "plan_hash": plan["record_hash"],
        "additional_root_read_seconds": seconds,
        "counter": "read_audio_seconds",
        "historical_ledgers_modified": False,
        "refunds": 0,
    }
    write_record(path, value, budget)
    return record(path)


def saved(budget, context):
    declaration = record(budget.root / "manifests/events/boundary-audit-plan.json")
    plan = record(budget.root / "manifests/events/development.json")
    directory = context.directory / "comparison"
    original = record(directory / "summary.json")
    state = record(directory / "progress.json")
    if (
        declaration["original_plan_hash"] != plan["record_hash"]
        or original["identity"] != state["identity"]
        or original["identity"]["plan"] != plan["record_hash"]
        or [c["case"] for c in original["cases"]] != plan["cases"]
        or context.cfg != plan["configuration"]
    ):
        raise InputError("B01 boundary audit: original plan/predictions changed")
    _, _, _, _, desc = frozen(budget, "efficientat")
    if original["identity"]["representation"] != desc:
        raise InputError("B01 boundary audit: frozen representation changed")
    accounting = account_parents(budget, context)
    identity = {
        "declaration_hash": declaration["record_hash"],
        "original_summary_hash": original["record_hash"],
        "accounting_hash": accounting["record_hash"],
        "code": {p: h for p, h in code_identity().items() if p.startswith("events/")},
    }
    path = directory / "boundary-audit.json"
    if path.exists() and record(path)["identity"] != identity:
        raise InputError("B01 boundary audit: correction changed; preserve completed audit")
    rows, invalid = [], []
    for case in plan["cases"]:
        key = case["reference_asset"]
        ref = record(budget.root / "manifests/evaluation/assets" / (key + ".json"))
        context.charge(budget, read_audio_seconds=ref["audio"]["duration_seconds"])
        _, reference = load_asset(budget.root, key, budget)
        tone = (
            record(budget.root / "manifests/evaluation/assets" / (case["truth_asset"] + ".json"))
            if case["truth_asset"]
            else None
        )
        first, last = case["region"]
        notes = reference_notes(reference, tone, first, last)
        selected = record(directory / (case["query_id"] + "-selection.json"))
        if selected["case"] != case:
            raise InputError("B01 boundary audit: saved proposal case differs")
        measured = boundaries(
            selected["detection"]["events"], notes, ref["audio"]["sample_rate_hz"], plan["metrics"]
        )
        before = (
            [(first + e["start_frame"], first + e["end_frame"]) for e in tone["events"]]
            if tone
            else []
        )
        actual_oracle = [
            (e["start_frame"], e["end_frame"])
            for e in notes
            if first <= e["start_frame"] < e["end_frame"] <= last
        ]
        bad = before != actual_oracle
        if bad:
            invalid.append(case["query_id"])
        rows.append(
            {
                "case": case,
                "selection_record_hash": selected["record_hash"],
                "reference_notes": notes,
                "note_boundaries": measured,
                "target_present_in_selected_region": bool(notes),
                "region_censored_notes": sum(
                    n["selection_start_censored"] or n["selection_end_censored"] for n in notes
                ),
                "original_oracle_invalid": bad,
                "reason": "zero-offset oracle did not match actual complete in-region notes"
                if bad
                else None,
            }
        )
    if path.exists():
        value = record(path)
        if value["cases"] != rows:
            raise InputError("B01 boundary audit repeat: source/truth/proposal differs")
        return {"status": "ok", "audit": path.relative_to(budget.root).as_posix(), "reused": True}
    affected = {r["case"]["stratum"] for r in rows if r["original_oracle_invalid"]}
    if affected != set(declaration["affected_strata"]):
        raise InputError("B01 boundary audit: affected cases differ from the declared correction")
    protocol, suite = comparison_pair(budget.root)
    queries = {q["query_id"]: q for q in suite["queries"] if q["split"] == "development"}
    subset = {
        **suite,
        "queries": [{**queries[c["query_id"]], "condition": c["stratum"]} for c in plan["cases"]],
    }
    subset.pop("record_hash")
    subset["record_hash"] = digest(subset)
    prediction = record(directory / "oracle_diagnostic-predictions.json")
    prediction = {
        **prediction,
        "run_id": prediction["run_id"] + ":boundary-audit",
        "queries": [
            {"query_id": q["query_id"], "candidate": [], "refined": []}
            if q["query_id"] in invalid
            else q
            for q in prediction["queries"]
        ],
    }
    assets = {
        k: record(budget.root / "manifests/evaluation/assets" / (k + ".json"))
        for q in subset["queries"]
        for k in q["candidate_assets"]
    }
    oracle = score(prediction, protocol, subset, assets)
    fixtures = record(directory / "fixtures.json")["cases"]
    note = aggregate(
        [r["note_boundaries"] for r in rows] + [f["note_boundaries"] for f in fixtures]
    )
    conditions = oracle["conditions"].values()
    totals = {
        "hit_at_1": sum(c["stages"]["candidate"]["at_k"]["1"]["hit_queries"] for c in conditions),
        "recovered_at_10": sum(
            c["stages"]["candidate"]["at_k"]["10"]["recovered_targets"]
            for c in oracle["conditions"].values()
        ),
        "present_queries": original["retrieval_totals"]["oracle_diagnostic"]["present_queries"],
        "targets": original["retrieval_totals"]["oracle_diagnostic"]["targets"],
        "invalid_queries_counted_as_misses": len(invalid),
    }
    value = {
        "schema_version": "b01-boundary-audit-1",
        "identity": identity,
        "cases": rows,
        "note_boundaries": note,
        "oracle_invalid_queries": invalid,
        "oracle_corrected_scores": oracle,
        "oracle_totals": totals,
        "retrieval_totals_unchanged": {
            m: v for m, v in original["retrieval_totals"].items() if m != "oracle_diagnostic"
        },
        "new_inference_windows": 0,
        "new_query_jobs": 0,
        "new_comparison_queries": 0,
        "default": "explicit/coarse",
        "automatic_status": "experimental",
        "evaluation_status": (
            "partial: fixed regions truncate two reference phrases and omit one target; "
            "three oracle outputs invalid"
        ),
        "original_evidence_preserved": True,
    }
    context.charge(budget, managed_output_bytes=512 * 1024)
    write_record(directory / "oracle-audited-predictions.json", prediction, budget)
    write_record(path, value, budget)
    return {
        "status": "ok",
        "audit": path.relative_to(budget.root).as_posix(),
        "note_boundaries": note,
        "invalid_oracle_queries": len(invalid),
        "new_inference_windows": 0,
    }
