"""Read-only C04 reporting after the fixed pool stops; never dispatches processing."""

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.processing import api, job
from similar_sound_search.processing.context import Context
from similar_sound_search.storage import digest

root = Path.cwd()
owner = Context(root)
job_path = (
    owner.directory / "jobs/6d5edff624a49b8529ff2add0593f3953f668c7baa140f65568e922979d7176b.json"
)
job_ref = api.reference(owner, job_path, "jobs")
manifest = owner.get(job_ref, "jobs")
plan = owner.get(manifest["plan"], "plans")
_, state = job.progress(owner, job_ref)
sources = job.collect(owner, state, plan, "features")
query = job.collect(owner, state, plan, "query")["query"]
scores = job.collect(owner, state, plan, "score")
old_query = record(root / owner.protocol["execution"]["path"])["identity"]["query_hash"]
assert query["query"]["record_hash"] == old_query
scenarios = []
for name in (
    "cold",
    "warm",
    "add",
    "replace",
    "remove",
    "query",
    "objective",
    "packing",
    "window",
    "labels",
):
    value = record(owner.reports / (name + ".json"))
    checked = owner.reports / (name + "-clean.json")
    clean = record(checked) if checked.exists() else None
    p = owner.get(value["plan"], "plans")
    earlier_path = owner.reports / (name + "-first-consumer.json")
    earlier = record(earlier_path) if earlier_path.exists() else None
    scenarios.append(
        dict(
            name=name,
            state=value["state"],
            plan=value["plan"],
            job=value["job"],
            result=value["result"],
            delta=value["measured_delta"],
            estimates=p["estimates"],
            tombstones=p["tombstones"],
            changed_dependencies=p["changed_dependencies"],
            previous_consumer_run=None
            if earlier is None
            else {k: earlier[k] for k in ("plan", "job", "result", "measured_delta")},
            clean=None
            if clean is None
            else {
                k: clean[k]
                for k in (
                    "comparison",
                    "passed",
                    "new_clean_encodes",
                    "exact_feature_bytes",
                    "exact_native_membership",
                    "scalar_pairs",
                    "max_scalar_error",
                )
            },
        )
    )
recovery = record(owner.reports / "recovery.json")
recovery_clean = record(owner.reports / "recovery-clean.json")
audit_consumers = Counter()
source_summary = []
for key, value in sorted(sources.items()):
    audit = owner.get(value["audit"], "consumer-audits")
    audit_consumers[audit["consumer"]["declaration_hash"]] += 1
    source_summary.append(
        dict(
            recording_id=key,
            rows=len(value["rows"]),
            new_encodes=value["new_encodes"],
            audit=value["audit"],
            original_memberships=audit["original_memberships"],
        )
    )
groups = {s["group"] for s in plan["input"]["sources"]}
partial_groups = {"legacy-mean": [], "event-multi": []}
for path in sorted((owner.directory / "group-results").glob("*.json")):
    value = record(path)
    if value["group"] in groups:
        arm = "event-multi" if value["contributions"] else "legacy-mean"
        partial_groups[arm].append(
            dict(
                group=value["group"],
                rank=value["rank"],
                score=value["score"],
                ref=dict(path=path.relative_to(root).as_posix(), record_hash=value["record_hash"]),
            )
        )
for values in partial_groups.values():
    values.sort(key=lambda v: v["rank"])
pool = owner.pool()
namespaces = {}
for base in (
    owner.directory,
    owner.features,
    owner.indexes,
    owner.audio,
    owner.reports,
    root / "manifests/processing",
):
    files = [p for p in base.rglob("*") if p.is_file()]
    namespaces[base.relative_to(root).as_posix()] = dict(
        files=len(files), bytes=sum(p.stat().st_size for p in files)
    )
arrays = [record(p) for p in owner.features.rglob("record.json")]
working = [
    record(p).get("peak_working_bytes", 0)
    for p in (owner.directory / "worker-settlements").glob("*.json")
]
regression = (owner.reports / "regression-final.txt").read_text(encoding="utf-8")
test_count, test_seconds = re.search(r"Ran (\d+) tests in ([\d.]+)s", regression).groups()
assert regression.rstrip().endswith("OK")
assert all(v["new_encodes"] == 0 for v in sources.values())
evidence = dict(
    schema_version="c04-processing-evidence-1",
    state="partial-metadata-ceiling",
    source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    consumer=record(root / "manifests/processing/consumer.json")["record_hash"],
    declarations=dict(
        protocol=digest(owner.protocol),
        correctness=record(root / "manifests/processing/consumer-repair.json")["record_hash"],
        metadata_compatibility=record(root / "manifests/processing/metadata-compatibility.json")[
            "record_hash"
        ],
    ),
    scenarios=scenarios,
    recovery={
        k: recovery[k]
        for k in (
            "job",
            "result",
            "source_units_committed_before_termination",
            "retained_committed_hashes",
            "committed_rows_not_reembedded",
        )
    },
    recovery_clean={
        k: recovery_clean[k]
        for k in ("comparison", "passed", "new_clean_encodes", "max_scalar_error")
    },
    historical=dict(
        job=job_ref,
        plan=manifest["plan"],
        requested_units=len(plan["units"]),
        committed_units=len(state["completed"]),
        sources=len(sources),
        groups=len(groups),
        rows=sum(len(v["rows"]) for v in sources.values()),
        banks=owner.protocol["primary_banks"],
        snapshot=owner.protocol["snapshot"],
        c02=owner.protocol["execution"],
        c03=owner.protocol["refinement_execution"],
        saved_query=owner.protocol["delivery"],
        exact_query_hash=old_query,
        query_committed=True,
        source_scores_committed=len(scores),
        new_catalogue_encodes=0,
        copied_catalogue_arrays=0,
        source_audit_consumers=dict(audit_consumers),
        source_units=source_summary,
        incomplete_group_publications=partial_groups,
        remaining=[u for u in plan["units"] if u["unit_id"] not in state["completed"]],
        current_result=None,
        last_complete=record(owner.directory / "last-complete.json"),
        real_warm_final_result=False,
        c04_completed_job_playback_exercised=False,
    ),
    pool=pool,
    recorded_max_working_bytes=max(working),
    worker_107=dict(
        state="unsettled reservation retained",
        seconds=pool["pending_worker_seconds"],
        journal_present=(owner.directory / "worker-settlements/107.json").exists(),
        live_locks="independently acquired/released after stop; no live C04 owner",
    ),
    namespace_inventory=namespaces,
    actual_new_managed_bytes=sum(v["bytes"] for v in namespaces.values()),
    own_arrays=dict(
        bundles=len(arrays),
        published_rows=sum(v["shape"][0] for v in arrays),
        bytes=sum(v["bytes"] for v in arrays),
        reserved_feature_windows=pool["counts"]["feature_windows"],
        interpretation=(
            "Includes independent clean outputs and retained failed-clean output. "
            "Published and reserved row counts are reported separately."
        ),
    ),
    checks=dict(
        full_regression=dict(passed=True, tests=int(test_count), seconds=float(test_seconds)),
        processing_tests=36,
        ruff="check and format passed on source/tests/scripts",
        setup="offline editable install and pip check passed",
        smoke=(
            "Isolated C04 starter root passed after restoring required reference metadata; "
            "earlier missing-setup failure retained."
        ),
        live_known_answer="Passed before expansion; unchanged oracle also covered by final tests",
        preservation=json.loads(
            (owner.reports / "preservation-after.json").read_text(encoding="utf-8")
        ),
        hosted_ci="PR 26: no configured statuses/check runs/workflows; main unprotected, no rulesets",
    ),
    playback=dict(
        bundle=owner.protocol["playback_bundle"],
        path="reports/local/c03/refinement-6f80c1786000d30144d0a3bf3da4dc777059f6cd391c13393e2dd3f712a6c405/index.html",
        startup="scripts/listen-refinement.ps1",
        port=8772,
        new_bundles=0,
        new_clips=0,
        native_http_browser_proofs="historical C03 proofs retained; no fresh C04 browser claim",
    ),
    limitations=[
        (
            "Metadata admission did not protect final-bookkeeping headroom; "
            "aggregate publication and settlement stopped at the ceiling."
        ),
        (
            "Progress remains in_progress/error=null: metadata refusal prevented error journaling. "
            "Pool, null current result and observed failure are authoritative."
        ),
        "Declared 32 MiB recovery reserve was prospective, not a separate admission floor.",
        (
            "Final aggregation, C03 import, snapshot/result, real warm result and "
            "completed-C04 playback remain blocked."
        ),
        (
            "D01 needs an authorized owner/allowance and metadata admission repair. "
            "No C04 reset or renaming is authorized."
        ),
        (
            "Cold pilot measured inclusive worker startup/decode/encode/publication; "
            "separate startup and physical I/O components were not isolated before the cap."
        ),
        (
            "Setup/regression/preservation/static publication are separate. Public declarations "
            "and non-inference QA are not per-worker charged writes."
        ),
        (
            "A03 remains 72/120; optional banks partial; human relevance, Loulou layer, "
            "rights, version and master alignment unverified."
        ),
    ],
    after_cap=(
        "No further processing dispatched; counters and reservation preserved. "
        "No cap increase/reset, GC, deployment or dependency change."
    ),
    delivery_pr="https://github.com/lillo24/Similar-Sound-Search/pull/26",
)
raw = json.dumps({**evidence, "record_hash": digest(evidence)}, indent=2, allow_nan=False) + "\n"
if len(raw.encode("utf-8")) > 1024**2:
    raise RuntimeError("C04 public evidence exceeds reader limit")
(root / "reports/C04_PROCESSING_EVIDENCE.json").write_text(raw, encoding="utf-8", newline="\n")
print(
    json.dumps(
        dict(
            state=evidence["state"],
            bytes=len(raw.encode("utf-8")),
            historical_units=len(state["completed"]),
            published_rows=evidence["own_arrays"]["published_rows"],
        )
    )
)
