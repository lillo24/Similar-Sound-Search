"""Prepare or serve the D04 companion, outside the frozen installed packages."""

import argparse
import sys
from pathlib import Path

# -I deliberately omits the checkout: add only this companion's scripts directory.
# There is no similar_sound_search package here; core imports remain installed.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from listening_review.common import ReviewError  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("prepare", "serve"))
    p.add_argument("--root", type=Path, required=True, help="Owned private D04 output directory")
    p.add_argument("--workspace", type=Path)
    p.add_argument("--port", type=int, default=8777)
    p.add_argument("--qa-feedback", action="store_true", help="Isolated technical QA responses")
    a = p.parse_args()
    try:
        if a.command == "prepare":
            if a.workspace is None:
                p.error("prepare requires the existing D03 --workspace")
            from listening_review.prepare import prepare

            prepare(Path(__file__).resolve().parents[1], a.workspace.resolve(), a.root.resolve())
        else:
            from listening_review.server import make_server

            server = make_server(a.root, a.port, "qa-feedback" if a.qa_feedback else "feedback")
            print(
                f"D04 review: http://127.0.0.1:{a.port}/ (this computer). Ctrl+C stops it.",
                flush=True,
            )
            try:
                server.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        return 0
    except (ReviewError, OSError, ValueError, KeyError, ImportError) as exc:
        print(f"D04 {a.command} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
