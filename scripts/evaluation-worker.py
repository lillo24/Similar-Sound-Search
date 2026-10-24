"""One bounded actual-PID D02 worker; no CLI retry or hidden numerical dispatch."""

import json
import sys

from sound_search_evaluation.jobs import worker

try:
    answer = worker(json.load(sys.stdin))
except Exception as exc:  # Process boundary: explicit actionable failure, never a result.
    import traceback

    traceback.print_exc(file=sys.stderr)
    answer = dict(status="failed", error_type=type(exc).__name__, error=str(exc))
print(json.dumps(answer, allow_nan=False), flush=True)
raise SystemExit(1 if answer["status"] == "failed" else 0)
