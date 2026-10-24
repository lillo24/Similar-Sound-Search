"""Sanitized saved-evidence export; no inference, ledger settlement or pool reset."""

import hashlib
import importlib.metadata
import json
import platform
import shutil
import statistics
import sys
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import load_limits
from similar_sound_search.storage import digest
from sound_search_evaluation import contracts
from sound_search_evaluation.budget import CatalogueBudget
from sound_search_evaluation.context import Context

root = Path.cwd()
owner = Context(root)
splits = {}
for split in ("development", "confirmation"):
    view = Context(root, split=split)
    saved = view.get(
        record(view.directory / "scores" / (split + "-summary.json"))["assessment"], "assessments"
    )
    if saved["state"] != "complete" or saved["declared_queries"] != len(
        owner.protocol["splits"][split]["cases"]
    ):
        raise RuntimeError("D02 cannot export a missing/partial declared split")
    boundaries = {}
    for arm in ("legacy-mean", "event-multi"):
        m = [v for c in saved["cases"] if c["primary"] for v in c["arms"][arm]["10"]["matched"]]
        targets = sum(c["arms"][arm]["10"]["targets"] for c in saved["cases"] if c["primary"])
        boundaries[arm] = dict(
            matched=len(m),
            targets=targets,
            misses=targets - len(m),
            mean_iou=statistics.mean(v["iou"] for v in m) if m else None,
            mean_truth_coverage=statistics.mean(v["truth_coverage"] for v in m) if m else None,
            mean_prediction_containment=statistics.mean(v["prediction_containment"] for v in m)
            if m
            else None,
            median_absolute_start_error_seconds=statistics.median(
                abs(v["start_error_seconds"]) for v in m
            )
            if m
            else None,
            median_absolute_end_error_seconds=statistics.median(
                abs(v["end_error_seconds"]) for v in m
            )
            if m
            else None,
            interpretation=(
                "Conditional on one-to-one IoU matches; misses remain in event-recall denominators"
            ),
        )
    splits[split] = dict(
        assessment_hash=saved["record_hash"],
        queries=saved["declared_queries"],
        primary_queries=saved["primary_queries"],
        summary=saved["summary"],
        gate=saved["gate"],
        boundary_errors_at_10=boundaries,
        truth_hash=saved["truth"],
        ancestry_hash=record(view.directory / "truth" / (split + ".json"))["ancestry"],
        population_hash=contracts.population(view)["record_hash"],
        inputs_hash=contracts.inputs(view)["record_hash"],
        cases=saved["cases"],
    )
qa = {}
for name in (
    "browser-completed-final-0.json",
    "browser-multi-correct-16.json",
    "browser-case-20.json",
):
    v = json.loads((owner.reports / name).read_text(encoding="utf-8"))
    if not v["passed"] or not v["native_qa"]["passed"]:
        raise RuntimeError("D02 actual product/native/browser QA missing: " + name)
    qa[str(v["ordinal"])] = dict(
        passed=True,
        job_id=v["job_id"],
        result_hash=v["result_hash"],
        query_hash=v["query_hash"],
        desktop_players=len(v["players"]),
        native_players=len(v["native_qa"]["checked"]),
        http_range=v["http_range"],
        read_only_refresh=v["read_only_refresh"],
        browser_reload=v.get("browser_reload", False),
        unexpected_browser_errors=len(v["page_errors"]) + len(v["console_errors"]),
        external_requests=len(v["external_requests"]),
    )
d01 = json.loads((owner.reports / "d01-ui-final.json").read_text(encoding="utf-8"))
if not d01["passed"] or not d01["pool_unchanged"]:
    raise RuntimeError("D02 D01 renderer regression QA incomplete")
report_qa = json.loads((owner.reports / "report-browser.json").read_text(encoding="utf-8"))
c03 = json.loads((owner.reports / "c03-browser.json").read_text(encoding="utf-8"))
invariance = json.loads((owner.reports / "invariance-browser.json").read_text(encoding="utf-8"))
replay = json.loads((owner.reports / "invariance-replay.json").read_text(encoding="utf-8"))
validation = json.loads((owner.reports / "validation.json").read_text(encoding="utf-8"))
if not all(v["passed"] for v in (report_qa, c03, invariance, replay, validation)):
    raise RuntimeError("D02 report, preserved route, invariance or regression check incomplete")
preserve = json.loads((owner.reports / "preservation-after.json").read_text(encoding="utf-8"))
if preserve["state"] != "verified":
    raise RuntimeError("D02 historical preservation not verified")
claims = [record(p) for p in (owner.directory / "execution-claims").glob("*.json")]
states = [record(p) for p in (owner.directory / "states").glob("*.json")]
journals = [record(p) for p in (owner.directory / "settlements").glob("*.json")]
terminals = [j["terminal"] for j in journals]
workers = [s["worker_evidence"] for s in states + terminals if s.get("worker_evidence")]
pool = owner.pool()
if any(pool["counts"][k] > n for k, n in pool["ceilings"].items()) or any(
    not a["settled"] for a in pool["attempts"].values()
):
    raise RuntimeError("D02 final resource bounds or settlement invalid")
qa_bytes = sum(p.stat().st_size for p in owner.reports.rglob("*") if p.is_file())
if qa_bytes > 64 * 1024**2:
    raise RuntimeError("D02 non-inference QA/report artifacts exceed their 64 MiB allowance")
query = record(next((owner.directory / "queries").glob("*.json")))
representation = query["query"]["identity"]["representation"]
initial_executions = sum(len(c["policies"]) for c in claims if c["category"] == "initial")
technical_executions = sum(len(c["policies"]) for c in claims if c["category"] == "technical")
if initial_executions != 80 or technical_executions != 8:
    raise RuntimeError("D02 full initial matrix and four paired technical replays required")
budget = CatalogueBudget(root, load_limits(root / "config/resource_limits.json", "starter"))
combined_managed = budget.managed_bytes()
budget.cap("max_managed_bytes", combined_managed, "D02 final complete physical inventory")
free_bytes = shutil.disk_usage(root).free
if free_bytes < budget.limits["min_free_bytes"]:
    raise RuntimeError("D02 final starter free-space headroom is unavailable")
latency = {}
latency_jobs = {
    "two_source_cold_index": "6ab43f6a7671c415cfd6bf4087b692d264e538189a35c7d956bd0fd74171c409",
    "two_source_reuse_index": "2148e09a8452dc99345de0ba1a7bf9b9dde7be0aea2805667418f53305aa70b5",
    **{"product_case_" + k: v["job_id"] for k, v in qa.items()},
}
for name, key in latency_jobs.items():
    attempts = [
        j
        for j in journals
        if j["attempt"].startswith("attempt-") and j["terminal"]["job_id"] == key
    ]
    latency[name] = dict(
        job_id=key,
        worker_attempts=len(attempts),
        worker_elapsed_seconds=sum(j["delta"]["measured"] for j in attempts),
        uncertain_worker_seconds=sum(j["delta"]["uncertain"] for j in attempts),
        interpretation=(
            "Settled worker elapsed time including retries; browser interaction excluded"
        ),
    )
value = dict(
    schema_version="d02-public-evidence-1",
    protocol=owner.protocol["record_hash"],
    consumer=contracts.consumer(owner),
    candidate=record(root / "manifests/assessment/candidate.json")["record_hash"],
    ui_proof=record(root / "manifests/assessment/ui-compatibility.json")["record_hash"],
    environment=dict(
        python=sys.version.split()[0],
        platform=platform.system(),
        machine=platform.machine(),
        numerical_threads=1,
        packages={
            name: importlib.metadata.version(name)
            for name in (
                "numpy",
                "scipy",
                "soundfile",
                "truststore",
                "torch",
                "ruff",
                "setuptools",
                "wheel",
            )
        },
    ),
    representation=representation,
    splits=splits,
    product_qa=qa,
    d01_regression=dict(
        passed=True,
        players=len(d01["players"]),
        results=d01["results"],
        pool_unchanged=True,
        dispatch=False,
    ),
    report_qa=dict(
        passed=True,
        cases=report_qa["case_count"],
        players=len(report_qa["players"]),
        prediction_links=report_qa["complete_prediction_links"],
        narrow_no_overflow=report_qa["narrow_no_overflow"],
        no_pool_write=report_qa["d02_pool_unchanged"],
        bundle_hash=record(owner.directory / "report-bundle.json")["record_hash"],
    ),
    c03_regression=dict(
        passed=True,
        players=len(c03["players"]),
        http_transport=c03["http_transport"],
        unpaced_metadata_connection_failures_retained=True,
        bundle_hash=json.loads(
            (root / "reports/local/c03/report-command.json").read_text(encoding="utf-8")
        )["bundle_hash"],
        dispatch=False,
    ),
    invariance=dict(
        browser_save=True,
        revision=invariance["revision_after"],
        charged_replay=replay["job_id"],
        new_encodes=replay["new_feature_windows"],
        scope=replay["comparison"],
    ),
    validation=validation,
    measured_latency=latency,
    executions=dict(
        initial=initial_executions,
        technical=technical_executions,
        ceiling=112,
    ),
    resources=dict(
        counts=pool["counts"],
        ceilings=pool["ceilings"],
        measured_worker_seconds=pool["measured_worker_seconds"],
        uncertain_worker_seconds=pool["uncertain_worker_seconds"],
        combined_managed_bytes=combined_managed,
        combined_managed_ceiling=budget.limits["max_managed_bytes"],
        available_disk_bytes=free_bytes,
        free_disk_minimum=budget.limits["min_free_bytes"],
        protected_used=pool["protected_used"],
        protected_reserved=pool["protected_reserved"],
        peak_worker_working_bytes=max(v.get("peak_working_bytes", 0) for v in workers),
        peak_worker_server_overlap_bound=max(v.get("overlap_peak_bound", 0) for v in workers),
        ordinary_remaining={
            k: a["remaining"] for k, a in pool["allocations"].items() if not a.get("closed")
        },
        qa_report_bytes=qa_bytes,
        actual_owned_bytes=sum(
            p.stat().st_size
            for base in (owner.directory, owner.features, owner.audio, owner.reports)
            for p in base.rglob("*")
            if p.is_file()
        ),
        actual_owned_bytes_scope=[
            base.relative_to(root).as_posix()
            for base in (owner.directory, owner.features, owner.audio, owner.reports)
        ],
    ),
    preservation=dict(
        historical_files=preserve["historical_files"],
        changed_or_missing=preserve["changed_or_missing"],
        unexpected_additions=preserve["unexpected_additions"],
        new_shared_preparations=len(preserve["new_shared_preparation"]),
        c01_denied_staging="retained",
    ),
    qualification=all(s["gate"]["passed"] for s in splits.values()),
    defaults=dict(audio="original", arm="legacy-mean", pitch="off"),
    interpretation=(
        "Prospective confirmation within familiar A04 mechanisms; "
        "no unseen-music or human relevance claim"
    ),
    human_agreement_pairs=0,
    full_private_report="reports/local/d02/index.html",
)
value["record_hash"] = digest(value)
target = root / "reports/D02_EVALUATION.json"
target.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(
    json.dumps(
        dict(
            exported=True,
            sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            qualification=value["qualification"],
        )
    )
)
