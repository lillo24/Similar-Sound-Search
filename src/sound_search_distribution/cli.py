"""Explicit offline package/workspace lifecycle; startup is always foreground loopback."""

import argparse
import json
import sys
from pathlib import Path

from similar_sound_search.application import server
from similar_sound_search.application.locks import lock
from similar_sound_search.storage import InputError

from . import RELEASE, authority, doctor
from .assets import prepare
from .policy import limits
from .runtime import Runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["version", "prepare", "doctor", "start", "relocate", "seal-verification"],
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--distribution", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--share", choices=["normal", "verification"], default="normal")
    parser.add_argument("--port", type=int, default=8776)
    parser.add_argument("--deep", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "version":
            result = dict(release=RELEASE, core="0.3.0", module=str(Path(__file__).resolve()))
        else:
            if not args.workspace:
                parser.error("--workspace is required")
            root = args.workspace.resolve()
            if args.command == "prepare":
                if not args.source or not args.distribution:
                    parser.error("prepare requires --source and --distribution")
                doctor.interpreter()
                # Check the one external authorization before copying private bytes.
                if (authority.anchor() / "allocation.json").exists():
                    raise InputError("D03 allowance already initialized; reopen or relocate it")
                from .bootstrap import verify

                verify(args.distribution.resolve())
                result = prepare(args.source, root, args.distribution)
                authority.initialize(root)
                result = dict(
                    workspace_id=authority.binding(root)["workspace_id"],
                    private_files=len(result["files"]),
                )
            elif args.command == "relocate":
                if not args.destination:
                    parser.error("relocate requires --destination")
                result = authority.relocate(root, args.destination)
            elif args.command == "doctor":
                result = doctor.inspect(root, args.share, args.deep)
            elif args.command == "seal-verification":
                path, _ = authority.read(root)
                with lock(path.parent, "server"), lock(path.parent, "library"):
                    _, value = authority.read(root)
                    if value["active"]:
                        raise InputError("D03 cannot seal an admitted request")
                    value["verification_closed"] = True
                    authority.save(path, value)
                result = dict(verification_closed=True)
            else:
                status = doctor.inspect(root, args.share)
                if not status["capabilities"]["completed_results"] or status["missing"]:
                    raise InputError("D03 private closure is incomplete; run doctor --deep")
                path, _ = authority.read(root)
                # This external lock prevents concurrent servers across profiles,
                # copied workspaces and installs; worker ownership remains inherited.
                with lock(path.parent, "server"):
                    server.serve(root, limits(root), args.port, Runtime(root, args.share))
                return 0
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (InputError, OSError, ValueError, KeyError, RuntimeError) as exc:
        print(
            json.dumps(
                dict(ok=False, step=args.command, error_type=type(exc).__name__, error=str(exc))
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
