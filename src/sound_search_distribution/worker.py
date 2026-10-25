"""Installed actual-PID child entry point; no editable/source-tree worker script."""

import json
import sys
from pathlib import Path

from similar_sound_search.application.job import worker
from sound_search_distribution.runtime import Runtime


def main():
    try:
        request = json.load(sys.stdin)
        value = worker(request, Runtime(Path(request["root"])))
        print(json.dumps(value, allow_nan=False), flush=True)
        return 0
    except Exception as exc:
        print(
            json.dumps(dict(status="failed", error_type=type(exc).__name__, error=str(exc))),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
