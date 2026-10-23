"""The predeclared D01 acceptance sequence; all work shares the fixed D01 pool."""

import argparse
import json
from pathlib import Path

from similar_sound_search.application import api, job
from similar_sound_search.application.context import Context
from similar_sound_search.resources import load_limits
from similar_sound_search.storage import atomic_json

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=("preflight", "adopt", "warm", "copy", "native"))
parser.add_argument("--job-id")
args = parser.parse_args()
root = Path.cwd()
owner = Context(root)
limits = load_limits(root / "config/resource_limits.json", "starter")
query = dict(historical=True, **owner.protocol["delivery"])
kind = "search"
input = dict(query=query, arm="legacy-mean")
if args.action == "preflight":
    kind, input = "metadata-preflight", {}
elif args.action == "copy":
    kind, input = "copy-reference", dict(revision=query["revision"])
elif args.action == "native":
    if not args.job_id:
        parser.error("native requires --job-id")
    values = []
    for i in range(0, 10, 2):
        request = dict(
            kind="native-qa",
            input=dict(job_id=args.job_id, start=i),
            request_id="d01-native-" + args.job_id + "-" + str(i),
        )
        key = api.submit(root, limits, request, acceptance=True)["job_id"]
        state = job.run(root, limits, key)
        if state["state"] != "complete":
            raise RuntimeError(str(state))
        values.append(api.result(root, key))
    atomic_json(
        owner.reports / ("native-" + args.job_id + ".json"), dict(passed=True, operations=values)
    )
    print(
        json.dumps(dict(state="complete", checks=sum(len(v["output"]["checks"]) for v in values)))
    )
    raise SystemExit(0)
request = dict(kind=kind, input=input, request_id="d01-delivery-" + args.action + "-1")
key = api.submit(root, limits, request, acceptance=True)["job_id"]
print(json.dumps(dict(job_id=key, action=args.action)), flush=True)
state = job.run(root, limits, key)
result = api.result(root, key) if state["state"] == "complete" else None
atomic_json(
    owner.reports / (args.action + ".json"), dict(state=state, result=result, pool=owner.pool())
)
print(
    json.dumps(
        dict(
            state=state["state"],
            job_id=key,
            error=state.get("error"),
            result=state["result"],
            counts=owner.pool()["counts"],
        )
    ),
    flush=True,
)
raise SystemExit(0 if state["state"] == "complete" else 1)
