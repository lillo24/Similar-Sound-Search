"""One actual Windows worker PID with this environment's explicit package paths."""

import json
import os
import subprocess
import sys
from pathlib import Path

from ..storage import InputError


def python_command(script=None, arguments=()):
    """Avoid the extra Windows venv launcher process. Keep resolved paths/prefix.

    -S excludes base site initialization; the current environment's package paths
    and editable source are restored explicitly. Dependencies/model stay unchanged.
    Linux uses its native executable. The timeout therefore owns the actual worker.
    """
    if os.name != "nt" or sys.executable == getattr(sys, "_base_executable", sys.executable):
        return (
            [sys.executable, str(script), *arguments]
            if script
            else [sys.executable, "-m", "similar_sound_search", "_worker"]
        )
    paths = [str(Path(__file__).resolve().parents[2]), *sys.path]
    bootstrap = (
        "import json,sys;sys.path=json.loads(sys.argv.pop(1));"
        "sys.prefix=sys.exec_prefix=sys.argv.pop(1);"
    )
    if script:
        bootstrap += (
            "import runpy;sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"
        )
        suffix = [str(script), *arguments]
    else:
        bootstrap += "from similar_sound_search.cli import main;raise SystemExit(main(['_worker']))"
        suffix = []
    return [sys._base_executable, "-S", "-c", bootstrap, json.dumps(paths), sys.prefix, *suffix]


def execute(request):
    env = os.environ.copy()
    env.update(
        OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONIOENCODING="utf-8"
    )
    try:
        completed = subprocess.run(
            python_command(),
            input=json.dumps(request),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=request["limits"]["max_seconds"],
            check=False,
        )
    except subprocess.TimeoutExpired:
        return dict(
            status="failed",
            error_type="ResourceError",
            error="C04 actual worker exceeded deadline and was terminated; retain charges/commits",
        )
    try:
        value = json.loads(completed.stdout)
    except ValueError as exc:
        raise InputError(
            "C04 worker exited without JSON: exit="
            + str(completed.returncode)
            + "; stderr="
            + completed.stderr[-2000:]
        ) from exc
    if completed.returncode and value.get("status") != "failed":
        raise InputError("C04 worker nonzero exit without explicit failure")
    return value
