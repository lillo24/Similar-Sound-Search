"""Execute only the predeclared finite C04 engineering scenarios in the shared pool."""

# ruff: noqa: E402 -- numerical thread limits must precede NumPy/package imports.

import copy
import json
import os
import sys
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

from similar_sound_search.cli import execute
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.processing import api
from similar_sound_search.processing.commands import admin
from similar_sound_search.processing.context import Context
from similar_sound_search.processing.contracts import row_key
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.storage import InputError, project_lock

root = Path.cwd()
owner = Context(root)
limits = load_limits(root / "config/resource_limits.json", "starter")


def save(name, value):
    with project_lock(root, ".c04-coordinator.lock"):
        owner.publish(CatalogueBudget(root, limits), owner.reports / name, value)


def run_case(name, spec, previous=None, clean=False, pilot=False):
    summary = owner.reports / (name + ".json")
    if summary.exists():
        old = record(summary)
        if old.get("status") == "ok" and old.get("state") == "complete":
            checked = owner.reports / (name + "-clean.json")
            if not clean or (checked.exists() and record(checked).get("status") == "ok"):
                return old
            if checked.exists():
                save(name + "-clean-first-consumer.json", record(checked))
    before = owner.pool()
    plan = None
    if summary.exists():
        old = record(summary)
        try:
            if api.load_plan(owner, old["plan"])["input"] == spec:
                plan = old["plan"]
                save(name + "-before-resume.json", old)
        except InputError:
            # Only a declared compatible old plan may resume; other changes create
            # a new explicit revision/job under the same pool.
            pass
    plan = plan or api.plan(root, limits, spec, previous)
    if summary.exists():
        old = record(summary)
        old_plan = owner.get(old["plan"], "plans")
        if old_plan["consumer"] != owner.get(plan, "plans")["consumer"]:
            save(name + "-first-consumer.json", old)
            result = api.run(root, limits, plan, name + "-consumer-2", execute)
        else:
            result = api.resume(root, limits, old["job"], execute)
    else:
        result = api.run(root, limits, plan, name, execute, pilot=pilot)
        if pilot and result["status"] == "ok" and result["state"] != "complete":
            save(name + "-pilot.json", result)
            result = api.resume(root, limits, result["job"], execute)
    after = owner.pool()
    answer = dict(
        **result,
        plan=plan,
        input=spec,
        measured_delta={k: after["counts"][k] - before["counts"][k] for k in after["counts"]},
    )
    save(name + ".json", answer)
    print(
        json.dumps(
            dict(
                name=name,
                state=result.get("state"),
                status=result["status"],
                delta=answer["measured_delta"],
            )
        ),
        flush=True,
    )
    if result["status"] != "ok" or result["state"] != "complete":
        raise RuntimeError("C04 declared scenario incomplete: " + name)
    if clean:
        checked = admin(
            dict(
                root=str(root),
                limits=limits,
                processing_action="clean-check",
                input=str(root / result["job"]["path"]),
            ),
            execute,
        )
        save(name + "-clean.json", checked)
        print(
            json.dumps(
                dict(
                    name=name + "-clean",
                    status=checked["status"],
                    encodes=checked.get("new_clean_encodes"),
                )
            ),
            flush=True,
        )
        if checked["status"] != "ok":
            raise RuntimeError(checked)
    return answer


def scenarios():
    fixtures = record(owner.reports / "fixtures-command.json")["fixtures"]
    registered = owner.get(fixtures, "fixtures")["sources"]
    sources = {v["source"]["recording_id"].removeprefix("c04-"): v["source"] for v in registered}
    query = sources["q1"]
    spec = dict(
        schema_version="c04-input-1",
        label="C04 generated native engineering sequence",
        sources=[sources["a"], sources["b"]],
        banks=[dict(label="original", grid=dict(window_milliseconds=2400, hop_milliseconds=1200))],
        query=dict(
            kind="native",
            source=query,
            bounds=[[0, 57600]],
            excluded_groups=[],
            lineage=dict(source_sha256=query["source"]["sha256"], cue=None, transform="original"),
        ),
        policy=dict(arm="legacy-mean", association=None),
        packing=128,
        refinement="off",
        historical=False,
    )
    outputs = []
    cold = run_case("cold", spec, clean=True, pilot=True)
    outputs.append(cold)
    warm = run_case("warm", spec, cold["plan"])
    outputs.append(warm)
    if warm["measured_delta"]["feature_windows"] != 0:
        raise RuntimeError("C04 warm encoded new rows")
    spec = copy.deepcopy(spec)
    spec["sources"].append(sources["c"])
    outputs.append(run_case("add", spec, outputs[-1]["plan"], clean=True))
    spec = copy.deepcopy(spec)
    replacement = copy.deepcopy(sources["b2"])
    replacement.update(recording_id="c04-b", group="c04-b")
    spec["sources"][1] = replacement
    outputs.append(run_case("replace", spec, outputs[-1]["plan"], clean=True))
    spec = copy.deepcopy(spec)
    spec["sources"] = [sources["a"], sources["c"]]
    outputs.append(run_case("remove", spec, outputs[-1]["plan"], clean=True))
    spec = copy.deepcopy(spec)
    query = sources["q2"]
    spec["query"].update(
        source=query,
        lineage=dict(source_sha256=query["source"]["sha256"], cue=None, transform="original"),
    )
    outputs.append(run_case("query", spec, outputs[-1]["plan"], clean=True))
    spec = copy.deepcopy(spec)
    desc = owner.get(outputs[-1]["plan"], "plans")["representation"]
    variant = row_key(query, [0, 57600], desc)
    spec["policy"] = dict(
        arm="event-multi",
        association={
            variant: dict(
                source_pcm=query["source"]["canonical_pcm"]["sha256"],
                native_bounds=[0, 57600],
                rate=24000,
            )
        },
    )
    outputs.append(run_case("objective", spec, outputs[-1]["plan"], clean=True))
    spec = copy.deepcopy(spec)
    spec["packing"] = 1
    outputs.append(run_case("packing", spec, outputs[-1]["plan"]))
    spec = copy.deepcopy(spec)
    spec["banks"][0]["grid"]["hop_milliseconds"] = 600
    outputs.append(run_case("window", spec, outputs[-1]["plan"], clean=True))
    spec = copy.deepcopy(spec)
    spec["label"] = "C04 renamed report metadata"
    spec["sources"][0]["title"] = "Renamed generated source; same bytes"
    outputs.append(run_case("labels", spec, outputs[-1]["plan"]))
    save(
        "scenarios.json",
        dict(
            schema_version="c04-scenarios-1",
            complete=True,
            scenarios=[
                dict(
                    name=v["input"]["label"],
                    plan=v["plan"],
                    job=v["job"],
                    result=v["result"],
                    delta=v["measured_delta"],
                )
                for v in outputs
            ],
        ),
    )


def historical():
    snapshot = record(root / "data/indexes/c01/snapshots" / (owner.protocol["snapshot"] + ".json"))
    banks = [
        record(root / next(r["path"] for r in snapshot["banks"] if r["record_hash"] == k))
        for k in owner.protocol["primary_banks"]
    ]
    spec = dict(
        schema_version="c04-input-1",
        label="C04 audited full original banks and exact Loulou/C03 chain",
        sources=[v["original"] for _, v in sorted(banks[0]["signals"].items())],
        banks=[
            dict(
                label="legacy-original" if i == 0 else "long-original",
                grid=b["bank"]["identity"]["grid"],
            )
            for i, b in enumerate(banks)
        ],
        query=dict(kind="saved", **owner.protocol["delivery"]),
        policy=dict(arm="event-multi", association=None),
        packing=128,
        refinement="historical",
        historical=True,
    )
    return run_case("historical-adoption", spec, pilot=True)


phase = sys.argv[1]
if phase == "scenarios":
    scenarios()
elif phase == "historical":
    historical()
elif phase == "warm":
    old = record(owner.reports / "historical-adoption.json")
    before = owner.pool()
    result = api.resume(root, limits, old["job"], execute)
    after = owner.pool()
    delta = {k: after["counts"][k] - before["counts"][k] for k in after["counts"]}
    if result["status"] != "ok" or result["state"] != "complete" or delta["feature_windows"]:
        raise RuntimeError("C04 historical warm validation failed: " + str(result))
    save("historical-warm.json", dict(**result, measured_delta=delta))
    print(
        json.dumps(dict(status="ok", state="complete", job=result["job"], delta=delta)), flush=True
    )
else:
    raise RuntimeError("Choose predeclared scenarios, historical or warm")
