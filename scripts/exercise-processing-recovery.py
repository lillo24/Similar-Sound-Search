"""Terminate only this script's real bounded worker after a committed feature unit."""

# ruff: noqa: E402 -- numerical thread limits must precede NumPy/package imports.

import json
import os
import subprocess
import sys
import time
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

from similar_sound_search.cli import execute
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.processing import api, job
from similar_sound_search.processing.context import Context
from similar_sound_search.processing.runner import python_command
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.storage import atomic_json, project_lock

root = Path.cwd()
owner = Context(root)
limits = load_limits(root / "config/resource_limits.json", "starter")
signal = owner.reports / "recovery-worker-committed.json"

if sys.argv[1:] == ["child"]:
    request = json.load(sys.stdin)
    with project_lock(root, ".c04-worker.lock"):
        budget = CatalogueBudget(root, request["limits"])
        from similar_sound_search.matchers.job import offline_network

        with offline_network():
            answer = job.step(request, budget, Context(root))
            from similar_sound_search.matchers.runner import memory_check

            answer["peak_working_bytes"] = memory_check(budget)
            atomic_json(signal, answer)
            # The parent observes the durable commit and terminates this owned child.
            # A deadline remains in the parent; no daemon or unrelated PID is involved.
            time.sleep(60)
    raise SystemExit(0)

if signal.exists() or (owner.reports / "recovery.json").exists():
    raise RuntimeError("The one declared real interruption already ran; preserve evidence")
old = record(owner.reports / "labels.json")
spec = json.loads(json.dumps(old["input"]))
spec["banks"][0]["grid"] = dict(window_milliseconds=1800, hop_milliseconds=900)
spec["label"] = "C04 one bounded real termination and restart"
plan = api.plan(root, limits, spec, old["plan"])
before = owner.pool()


def interrupt(request):
    child = subprocess.Popen(
        python_command(__file__, ["child"]),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    started = time.monotonic()
    try:
        child.stdin.write(json.dumps(request))
        child.stdin.close()
        while not signal.exists():
            if (
                child.poll() is not None
                or time.monotonic() - started > request["limits"]["max_seconds"] - 2
            ):
                raise RuntimeError("Owned recovery worker exited/timed out before durable commit")
            time.sleep(0.1)
        child.terminate()
        child.wait(timeout=5)
        return dict(
            status="failed",
            error_type="InjectedOwnedTermination",
            error="Parent terminated its own real feature worker after observing durable commit",
            observed_commit=json.loads(signal.read_text()),
            peak_working_bytes=json.loads(signal.read_text())["peak_working_bytes"],
            exit_code=child.returncode,
        )
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
        child.stdout.close()
        child.stderr.close()


failed = api.run(root, limits, plan, "recovery", interrupt, pilot=True)
if failed["status"] != "failed":
    raise RuntimeError("Expected explicit failed interruption")
with project_lock(root, ".c04-coordinator.lock"):
    owner.publish(CatalogueBudget(root, limits), owner.reports / "recovery-failed.json", failed)
state = api.status(root, failed["job"])
job_value = owner.get(failed["job"], "jobs")
p = api.load_plan(owner, job_value["plan"])
_, progress = job.progress(owner, failed["job"])
committed = job.collect(owner, progress, p, "features")
hashes = {key: [(r["key"], r["vector_sha256"]) for r in v["rows"]] for key, v in committed.items()}
after_failure = owner.pool()
recovered = api.resume(root, limits, failed["job"], execute)
_, done = job.progress(owner, failed["job"])
current = job.collect(owner, done, p, "features")
if recovered["status"] != "ok" or recovered["state"] != "complete":
    raise RuntimeError(recovered)
for key, rows in hashes.items():
    if rows != [(r["key"], r["vector_sha256"]) for r in current[key]["rows"]]:
        raise RuntimeError("Committed real feature rows changed after restart")
answer = dict(
    schema_version="c04-real-recovery-1",
    status="ok",
    state="complete",
    job=recovered["job"],
    result=recovered["result"],
    observed_failure=failed,
    retained_committed_hashes=hashes,
    source_units_committed_before_termination=len(committed),
    before=before["counts"],
    after_failure=after_failure["counts"],
    after=owner.pool()["counts"],
    committed_rows_not_reembedded=True,
)
with project_lock(root, ".c04-coordinator.lock"):
    owner.publish(CatalogueBudget(root, limits), owner.reports / "recovery.json", answer)
print(
    json.dumps(
        dict(status="ok", state="complete", committed_units=len(committed), job=recovered["job"])
    ),
    flush=True,
)

from similar_sound_search.processing.commands import admin

checked = admin(
    dict(
        root=str(root),
        limits=limits,
        processing_action="clean-check",
        input=str(root / recovered["job"]["path"]),
    ),
    execute,
)
with project_lock(root, ".c04-coordinator.lock"):
    owner.publish(CatalogueBudget(root, limits), owner.reports / "recovery-clean.json", checked)
if checked["status"] != "ok":
    raise RuntimeError(checked)
