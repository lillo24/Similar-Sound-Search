"""Read retained D01 records into a typed, path/token/audio-free public summary.

No worker, settlement, source decode or historical writer is called. This requires
the completed acceptance/QA records; missing evidence is an error, not an empty pass.
"""

import hashlib
import json
import re
from pathlib import Path

from similar_sound_search.application import api, history, pipeline
from similar_sound_search.application.context import Context
from similar_sound_search.storage import atomic_json, digest

ROOT = Path.cwd()
OWNER = Context(ROOT)
QA = ROOT / "reports/local/d01"
JOBS = dict(
    adopted="1c0ef69a1a5156319dec8a976cab164de576d13ba9cc00f5c24b4355b361a678",
    warm="12941fbd35737b6fb7df959d4fbbf9a1425fd5d5c1ba208cb01eb55e943ebef0",
    new_query="589ac27a30d60007e1a7f8ad6fdd695499d23ca0f17b55e858b00d624be0fd6b",
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path):
    if path.stat().st_size > 4 * 1024**2:
        raise RuntimeError("Unexpected metadata size: " + path.name)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def search(key):
    state = api.status(ROOT, key)
    if state["state"] != "complete":
        raise RuntimeError("Incomplete acceptance job: " + key)
    result = api.result(ROOT, key)
    query = OWNER.get(result["query"], "queries")
    before = read(OWNER.directory / "settlements" / ("submit-" + key + ".json"))
    durable = read(api.state_path(OWNER, key))
    final = read(OWNER.directory / "settlements" / (durable["attempt"] + ".json"))
    return dict(
        job_id=key,
        state=state["state"],
        completed=state["completed"],
        requested=state["requested"],
        result=result["record_hash"],
        revision=query["revision"],
        materialization=query["materialization"],
        query_hash=result["query_hash"],
        new_query_encodes=query["new_encodes"],
        new_catalogue_encodes=result["new_catalogue_encodes"],
        population=result["population_count"],
        excluded_groups=result["excluded_groups"],
        policy=result["policy"],
        submission_to_final_snapshot_delta={
            k: final["pool_after"]["counts"][k] - before["pool_after"]["counts"][k]
            for k in ("read_audio_seconds", "feature_windows", "clips", "workers")
        },
        arms={
            k: dict(
                complete=len(v["complete_groups"]),
                shortlist=len(v["shortlist"]),
                display=len(v["display"]),
            )
            for k, v in result["arms"].items()
        },
        chain=result["chain"]["chain"]["record_hash"] if result["chain"] else None,
        cards=[
            dict(
                rank=c["rank"],
                group=c["group"],
                score=c["score"],
                score_direction=c["score_direction"],
                group_ref=c["group_ref"]["record_hash"],
                native=c["passages"][0]["scored_bounds"],
                context=c["passages"][0]["context_bounds"],
                rate=c["passages"][0]["row"]["rate"],
                scored_media=c["passages"][0]["scored"]["record_hash"],
                context_media=c["passages"][0]["context"]["record_hash"],
                retained_passages=len(c["passages"]),
            )
            for c in result["cards"]
        ],
    )


def browser(name):
    value = read(QA / ("browser-" + name + ".json"))
    if not value["passed"] or any(
        value[k] for k in ("page_errors", "console_errors", "external_requests")
    ):
        raise RuntimeError("Browser evidence failed: " + name)
    return dict(
        passed=True,
        players=len(value["players"]),
        busy_controls=value.get("busy_controls"),
        actions=value["actions"],
        page_errors=0,
        console_errors=0,
        external_requests=0,
        evidence_sha256=sha256(QA / ("browser-" + name + ".json")),
    )


def main():
    pool = OWNER.pool()
    searches = {name: search(key) for name, key in JOBS.items()}
    native = {}
    for label in ("warm", "new_query"):
        value = read(QA / ("native-" + JOBS[label] + ".json"))
        checks = [c for op in value["operations"] for c in op["output"]["checks"]]
        if not value["passed"] or len(checks) != 20 or not all(c["samples_exact"] for c in checks):
            raise RuntimeError("Incomplete native QA: " + label)
        native[label] = dict(passed=True, checks=checks)
    http = read(QA / "http-qa.json")
    preservation = read(QA / "preservation-after.json")
    regression = (QA / "regression-final-382.txt").read_text(encoding="utf-8-sig")
    match = re.search(r"Ran (\d+) tests in ([\d.]+)s\s+OK\s*$", regression)
    if not match or not http["passed"] or preservation["state"] != "verified":
        raise RuntimeError("Required final regression/HTTP/preservation evidence missing or failed")
    static_checks = read(QA / "final-static-checks.json")
    if not all(v["passed"] for v in static_checks.values()):
        raise RuntimeError("Required static/setup checks failed")
    settlements = [read(p) for p in (OWNER.directory / "settlements").glob("*.json")]
    worker_evidence = [v["terminal"].get("worker_evidence", {}) for v in settlements]
    preflight = read(QA / "preflight.json")["result"]["output"]
    historical = read(ROOT / "data/runs/processing/pool.json")
    qa_bytes = sum(p.stat().st_size for p in QA.rglob("*") if p.is_file())
    if qa_bytes > 64 * 1024**2:
        raise RuntimeError("Non-inference QA exceeded its retained 64 MiB reservation")
    value = dict(
        schema_version="d01-public-evidence-1",
        outcome="completed D01 acceptance; further full searches exceed the remaining allowance",
        startup="powershell -NoProfile -ExecutionPolicy Bypass "
        "-File scripts/start-sound-search.ps1",
        url="http://127.0.0.1:8774/",
        scope="Real 72-recording catalogue plus separately identified generated engineering tests",
        current_consumer=history.consumer(OWNER),
        renderer_sha256={
            p.name: sha256(p)
            for p in sorted((ROOT / "src/similar_sound_search/application/web").iterdir())
            if p.is_file()
        },
        fixed_protocol_sha256=sha256(ROOT / "manifests/application/protocol.json"),
        source_rows=dict(legacy=44025, long=10914, total=54939, copied_arrays=0),
        acceptance=searches,
        original_query=dict(rate=44100, event=[9613800, 10584000], context=[9569700, 10628100]),
        generated_query=dict(rate=24000, channels=1, events=[[4800, 55200], [74400, 132000]]),
        last_complete=read(OWNER.directory / "last-complete.json")["job_id"],
        metadata_preflight={
            k: preflight[k]
            for k in (
                "proposed_records",
                "counted_publication_bytes",
                "largest_record",
                "comparisons",
            )
        },
        corrected_geometry={str(n): pipeline.geometry_estimate(OWNER, n) for n in (1, 2, 8)},
        same_pool_recovery_allocations={
            name: dict(
                initial_bytes=pool["allocations"][JOBS[name]]["initial_size"],
                final_bytes=pool["allocations"][JOBS[name]]["size"],
                admission=pool["allocations"][JOBS[name]]["recovery_admission"]["record_hash"],
            )
            for name in ("adopted", "new_query")
        },
        resources={
            k: pool[k]
            for k in (
                "counts",
                "ceilings",
                "ordinary_used",
                "ordinary_reserved",
                "protected_used",
                "protected_reserved",
                "acceptance_held",
                "uncertain_worker_seconds",
            )
        },
        memory={
            k: max((v.get(k, 0) for v in worker_evidence), default=0)
            for k in ("peak_working_bytes", "server_peak_working_bytes", "overlap_peak_bound")
        },
        browser_memory=dict(
            scope="one snapshot of owned Chrome during new-query QA; peaks not simultaneous",
            working_bytes=sum(
                v["WorkingSet64"] for v in read(QA / "browser-memory-new-query.json")
            ),
            sum_process_peaks=sum(
                v["PeakWorkingSet64"] for v in read(QA / "browser-memory-new-query.json")
            ),
        ),
        non_inference_qa=dict(reserved_bytes=64 * 1024**2, retained_bytes=qa_bytes),
        browser={
            name: browser(name)
            for name in (
                "warm-reopen",
                "import-cancel",
                "resume-observe",
                "fresh-navigation",
                "fresh-navigation-before-disconnect-fix",
            )
        },
        native=native,
        http={k: v for k, v in http.items() if k != "checks"},
        historical_c03_listener=read(QA / "preserved-c03-http.json"),
        checks=dict(
            full_regression=dict(passed=True, tests=int(match[1]), seconds=float(match[2])),
            static_and_setup=static_checks,
            dependencies=read(QA / "dependency-check.json"),
            isolated_starter_smoke=read(QA / "starter-smoke/reports/local/smoke.json")["status"],
            known_answer=read(QA / "known-answer.json"),
        ),
        preservation=preservation,
        historical_c04=dict(
            state="partial",
            completed=145,
            requested=148,
            job_id=OWNER.protocol["c04_job"],
            plan=OWNER.protocol["c04_plan"],
            metadata_bytes=historical["counts"]["metadata_bytes"],
            worker_seconds=historical["counts"]["job_seconds"],
            workers=historical["counts"]["workers"],
            pending_seconds=historical["pending_worker_seconds"],
            result=None,
        ),
        limitations=[
            "Human similarity, rights, intended layer and master alignment are unverified.",
            "Additional passages are native references in details; the first has players.",
            "Actual symlink creation was refused by Windows; no workaround attempted.",
            "Private audio/model/artifacts are required for real searches in another checkout.",
            "No D02 evaluation, D03 packaging, D04 listening review or production deployment ran.",
        ],
    )
    atomic_json(ROOT / "reports/D01_INTERFACE.json", {**value, "record_hash": digest(value)})
    print(json.dumps(dict(outcome=value["outcome"], tests=int(match[1]), resources=pool["counts"])))


if __name__ == "__main__":
    main()
