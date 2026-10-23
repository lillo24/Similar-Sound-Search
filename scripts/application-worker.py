"""Actual-PID child entrypoint; failures are explicit at this process boundary."""

import json
import sys

from similar_sound_search.application.job import worker

try:
    result = worker(json.load(sys.stdin))
except Exception as exc:
    result = dict(status="failed", error_type=type(exc).__name__, error=str(exc))
print(json.dumps(result, allow_nan=False))
raise SystemExit(0 if result["status"] == "ok" else 1)
