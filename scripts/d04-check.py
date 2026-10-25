"""D04's finite validation receipts; uses the existing actual-process timeout pattern."""

import argparse
import os
import subprocess
import time
from pathlib import Path

from listening_review.common import ReviewError, output_limits, put_new, read


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--source-seconds", type=float, default=0)
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    root = a.root.resolve()
    folder = root / "metadata/receipts"
    folder.mkdir(parents=True, exist_ok=True)
    starts = sorted(folder.glob("*-start.json"))
    finishes = sorted(folder.glob("*-finish.json"))
    if len(starts) != len(finishes):
        raise ReviewError("Unsettled D04 invocation; retain its reservation and investigate")
    spent = sum(read(f)["seconds"] for f in finishes)
    decoded = sum(read(f)["reserved_source_seconds"] for f in starts)
    # The amendment raises only the cumulative invocation ceiling. Existing
    # starts/finishes still consume this same allowance and the same 600 seconds.
    if len(starts) >= 24 or spent >= 600 or not 0 <= a.source_seconds <= 6000 - decoded:
        raise ReviewError("D04 preparation allowance exhausted")
    output_limits(root, 1024 * 1024)
    deadline = min(120, 600 - spent)
    index = f"{len(starts) + 1:02}"
    put_new(
        folder / (index + "-start.json"),
        dict(label=a.label, deadline=deadline, reserved_source_seconds=a.source_seconds),
    )
    env = os.environ.copy()
    temp = root / "qa/tmp"
    temp.mkdir(parents=True, exist_ok=True)
    env.update(
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONIOENCODING="utf-8",
        PYTHONDONTWRITEBYTECODE="1",
        TMP=str(temp),
        TEMP=str(temp),
    )
    command = a.command[1:] if a.command[:1] == ["--"] else a.command
    started = time.monotonic()
    code, timeout = 1, False
    peak = {k: 0 for k in ("qa", "metadata", "bundle", "total")}
    failure = None
    # Like application.job.execute, supervise the actual worker, including startup.
    # Browser drivers close their owned browser in finally; the timeout is a failure.
    try:
        process = subprocess.Popen(command, env=env)
        try:
            while True:
                files = output_limits(root, transient=True)
                for category in ("qa", "metadata", "bundle"):
                    live = sum(v for k, v in files.items() if k.startswith(category + "/"))
                    peak[category] = max(peak[category], live)
                peak["total"] = max(peak["total"], sum(files.values()))
                if any(n > 256 * 1024 * 1024 for n in files.values()):
                    raise ReviewError("D04 individual output exceeds 256 MiB")
                remaining = deadline - (time.monotonic() - started)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, deadline)
                try:
                    code = process.wait(timeout=min(0.5, remaining))
                    break
                except subprocess.TimeoutExpired:
                    pass
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        timeout = True
    except (ReviewError, OSError) as exc:
        failure = str(exc)
    finally:
        put_new(
            folder / (index + "-finish.json"),
            dict(
                label=a.label,
                seconds=time.monotonic() - started,
                exit_code=code,
                timeout=timeout,
                observed_peak_bytes=peak,
                error=failure,
            ),
        )
        output_limits(root)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
