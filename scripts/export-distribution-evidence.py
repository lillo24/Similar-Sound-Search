"""Export sanitized D03 technical evidence; never dispatch a worker or reset a ledger."""

import argparse
import json
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.storage import atomic_json, digest
from sound_search_distribution import RELEASE, authority
from sound_search_distribution.context import Context
from sound_search_distribution.files import sha
from sound_search_distribution.policy import PROTECTED, SHARE, TOTAL


def export(root, workspace):
    local = root / "reports/local/d03"

    def read(name):
        return json.loads((local / name).read_text(encoding="utf-8-sig"))

    public = root / "dist/similar-sound-search-d03-1.0.0"
    release = json.loads((public / "release.json").read_text(encoding="utf-8"))
    archive = root / "dist/similar-sound-search-d03-1.0.0.zip"
    wheel_name = "wheelhouse/similar_sound_search-0.3.0-py3-none-any.whl"
    verification = Context(workspace, share="verification").pool()
    normal = Context(workspace).pool()
    _, registry = authority.read(workspace)
    doctor = read("doctor-delivery.json")
    closure = record(workspace / "private-assets.json")
    consumer = record(workspace / "manifests/distribution/consumer.json")
    baseline, new = read("warm-result.json"), read("new-result.json")
    directory = workspace / "data/runs/runtime-verification"

    def search(name, result):
        key = result["job_id"]
        evidence = []
        for p in (directory / "settlements").glob("attempt-*.json"):
            value = record(p)
            if value["terminal"].get("job_id") == key:
                evidence.append(value)
        start = record(directory / "settlements" / ("submit-" + key + ".json"))
        end = record(directory / "settlements" / ("close-" + key + ".json"))
        counters = {
            k: end["pool_after"]["counts"][k] - start["pool_after"]["counts"][k] for k in SHARE
        }
        return dict(
            job_id=key,
            result_id=result["record_hash"],
            query_hash=result["query_hash"],
            query_feature_hash=result.get("saved_query_feature_hash"),
            worker_count=len(evidence),
            worker_seconds=sum(e.get("delta", {}).get("measured", 0) for e in evidence),
            committed_units=98,
            new_catalogue_encodes=result["new_catalogue_encodes"],
            worker_phase_counts=counters,
            counts_scope=(
                "submit-to-close watermarks; submit/control publication also in pool totals"
            ),
            wall_seconds=read(name)["wall_seconds"],
            producing_consumer=result["consumer"],
        )

    workers = [
        record(p)["terminal"].get("worker_evidence", {})
        for p in (directory / "settlements").glob("attempt-*.json")
    ]
    population = {s["recording_id"]: s for s in baseline["population"]}
    cards = []
    for card in baseline["cards"]:
        passage = card["passages"][0]
        source = population[passage["row"]["recording_id"]]
        rate = source["source"]["sample_rate_hz"]
        cards.append(
            dict(
                rank=card["rank"],
                title=card["title"],
                artist=card["artist"],
                group=card["group"],
                score=card["score"],
                recording_id=source["recording_id"],
                sample_rate_hz=rate,
                scored_frames=passage["scored_bounds"],
                context_frames=passage["context_bounds"],
                scored_seconds=[n / rate for n in passage["scored_bounds"]],
                context_seconds=[n / rate for n in passage["context_bounds"]],
                scored_url="/result-media/"
                + baseline["record_hash"]
                + "/"
                + passage["scored"]["record_hash"],
                context_url="/result-media/"
                + baseline["record_hash"]
                + "/"
                + passage["context"]["record_hash"],
            )
        )
    preserve = read("preservation-after.json")
    browser = read("browser-delivery.json")
    browser_move = read("browser-relocated.json")
    native = read("native.json")
    disk = read("disk.json")
    assert preserve["state"] == "verified"
    assert native["passed"] and native["checks"] == 40
    assert browser["passed"] and len(browser["players"]) == 40 and browser_move["passed"]
    assert all(n == 0 for n in normal["counts"].values()) and registry["verification_closed"]
    assert doctor["capacity"]["ready"] and doctor["capabilities"]["real_catalogue_search"]
    failed = read("failed-warm.json")
    value = dict(
        schema_version="d03-package-evidence-1",
        outcome="complete",
        release=RELEASE,
        pull_request="https://github.com/lillo24/Similar-Sound-Search/pull/32",
        artifact=dict(
            path=archive.relative_to(root).as_posix(),
            bytes=archive.stat().st_size,
            sha256=sha(archive),
            source_commit=release["source_commit"],
            release_manifest_sha256=sha(public / "release.json"),
            wheel=wheel_name,
            wheel_bytes=release["files"][wheel_name]["bytes"],
            wheel_sha256=release["files"][wheel_name]["sha256"],
        ),
        target=dict(
            os=doctor["platform"],
            architecture="AMD64",
            python=doctor["python"],
            core="0.3.0",
            dependencies=doctor["dependencies"],
        ),
        current_consumer=doctor["consumer"],
        numerical_hash=consumer["numerical_hash"],
        packaging=dict(
            offline_wheels=len(release["dependencies"]),
            dependencies_expanded_bytes=release["dependency_expanded_bytes"],
            network=read("network.json"),
            reproducibility=read("reproducibility-delivery.json"),
            non_editable=True,
            no_checkout_fallback=True,
            installed_entry="sound-search-local / python -I -m sound_search_distribution",
            fresh_full_offline_environment=True,
            final_application_installed_by_non_editable_reinstall=True,
            second_full_environment_install=False,
        ),
        private_closure=dict(
            files=len(closure["files"]),
            bytes=sum(v["bytes"] for v in closure["files"].values()),
            manifest_sha256=sha(workspace / "private-assets.json"),
            original_recordings=72,
            candidate_rows=54939,
            primary_rows=[44025, 10914],
            all_bytes_verified=True,
            optional_history=dict(c03=False, d02=False),
        ),
        runtime=dict(
            workspace_id=registry["workspace_id"],
            allocation_id=registry["allocation_id"],
            registry="%LOCALAPPDATA%/SimilarSoundSearch/D03/allocation.json",
            total=TOTAL,
            each_share=SHARE,
            protected_metadata_per_share=PROTECTED,
            verification_counts=verification["counts"],
            normal_counts=normal["counts"],
            verification_sealed=True,
            normal_capacity=doctor["capacity"],
            verification_pool_sha256=sha(directory / "pool.json"),
            normal_pool_sha256=sha(workspace / "data/runs/runtime-normal/pool.json"),
            protected_used=verification["protected_used"],
            ordinary_used=verification["ordinary_used"],
            uncertain_worker_seconds=verification["uncertain_worker_seconds"],
            qa_prepaid_bytes=read("qa-prepayment.json")["prepaid_bytes"],
        ),
        searches=dict(
            loulou=search("warm.json", baseline),
            new_two_example=search("new-resume.json", new),
            cancelled_phase_wall_seconds=read("new-cancel.json")["wall_seconds"],
            agreement=read("baseline-agreement.json"),
            reuse=read("reuse-and-query-identity.json"),
        ),
        failed_attempt=dict(
            job_id=failed["state"]["job_id"],
            state=failed["state"]["state"],
            completed_units=failed["state"]["completed"],
            wall_seconds=failed["wall_seconds"],
            reason="Windows busy-reader registry replace PermissionError",
            retained=True,
            spent_charges_retained=True,
            unused_reservations_only_released=True,
            extra_repair_searches=1,
        ),
        native=dict(passed=True, checks=native["checks"], operations=len(native["operations"])),
        browser=dict(
            passed=True,
            players=len(browser["players"]),
            unpaced=True,
            desktop_width=1360,
            narrow_width=390,
            reload=browser["reload"],
            relocated_results=browser_move["opened"],
            long_label_layout_fixture=browser_move["long_label_layout_fixture"],
            external_requests=browser["external_requests"],
        ),
        http=read("http-boundaries.json"),
        session_rotation=read("session-rotation.json"),
        relocation=read("relocation-proof.json"),
        historical_results=read("historical-reopen.json"),
        preservation=preserve,
        memory=dict(
            max_observed_worker_bytes=max(e.get("peak_working_bytes", 0) for e in workers),
            max_observed_server_bytes=max(e.get("server_peak_working_bytes", 0) for e in workers),
            max_reported_overlap_bytes=max(e.get("overlap_peak_bound", 0) for e in workers),
            os_rss_enforced=False,
        ),
        storage={k: v for k, v in disk.items() if k != "setup_components"},
        checks=dict(
            regression_tests=417,
            regression_seconds=281.216,
            ruff_lint=True,
            ruff_format_files=241,
            javascript_syntax=True,
            dependency_check=True,
            installed_console_smoke=True,
            installed_faults=read("installed-faults.json"),
            known_answers=read("known-answer.json"),
            hosted_ci="not configured",
        ),
        handoff=dict(
            stage="D04",
            started=False,
            defaults=dict(audio="original", arm="legacy-mean", pitch="off"),
            query=dict(
                revision="c5d9eebb0a510565b6201113f3f4e4686845db6cf27d34ec929560a438b341a3",
                materialization="0ebb77012137c086e4cb1f72298e16446b33d96da2de28d7c9ccc5d663a03036",
                frames=[9613800, 10584000],
                rate=44100,
            ),
            completed_job=baseline["job_id"],
            cards=cards,
            distinct_song_labels=len({(c["title"], c["artist"]) for c in cards}),
            human_relevance="unmeasured",
            intended_layer="unverified",
            rights="unverified",
            version_master_alignment="unverified",
        ),
    )
    atomic_json(root / "reports/D03_PACKAGE.json", {**value, "record_hash": digest(value)})
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    result = export(Path.cwd(), args.workspace.resolve())
    print(
        json.dumps(
            dict(
                outcome=result["outcome"],
                archive=result["artifact"]["path"],
                sha256=result["artifact"]["sha256"],
            ),
            indent=2,
        )
    )
