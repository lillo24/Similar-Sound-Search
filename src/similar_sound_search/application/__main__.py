"""Foreground local app entry point; no implicit processing at startup."""

import argparse
from pathlib import Path

from ..resources import load_limits
from .server import serve

parser = argparse.ArgumentParser(description="Local Sound Search · D01")
parser.add_argument("--root", type=Path, default=Path.cwd())
parser.add_argument("--port", type=int, default=8774)
args = parser.parse_args()
try:
    serve(
        args.root.resolve(),
        load_limits(args.root / "config/resource_limits.json", "starter"),
        args.port,
    )
except Exception as exc:
    parser.exit(1, "Sound Search startup failed: " + str(exc) + "\n")
