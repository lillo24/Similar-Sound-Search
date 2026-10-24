"""Independent emitted-byte QA; debit D02 reads/metadata, never decode or write old pools."""

import hashlib
import json
import sys
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import load_limits
from similar_sound_search.storage import contained, digest
from sound_search_evaluation.budget import CatalogueBudget
from sound_search_evaluation.context import Context

root = Path.cwd()
split = sys.argv[1]
protocol = record(root / "manifests/assessment/protocol.json")
owner = Context(root, "prepare", split)
budget = CatalogueBudget(root, load_limits(root / "config/resource_limits.json", "starter"))
checks = []
for kind, folder, key in (
    ("source", "generated", "source_id"),
    ("query", "generated-queries", "case_id"),
):
    for spec in protocol["splits"][split]["sources" if kind == "source" else "cases"]:
        value = record(root / "data/runs/assessment" / folder / (spec[key] + ".json"))
        items = (
            [dict(path=value["source"]["source"]["local_path"], audio=value["source"]["source"])]
            if kind == "source"
            else value["examples"]
        )
        for item in items:
            target = contained(root / item["path"], root / "data/audio/assessment")
            budget.input_file(target)
            owner.charge(budget, read_audio_seconds=item["audio"]["duration_seconds"])
            h = hashlib.sha256()
            with target.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
                    budget.check_time("byte audit", target.name)
            if h.hexdigest() != item["audio"]["sha256"]:
                raise RuntimeError(
                    "D02 emitted bytes differ from generated metadata: " + target.name
                )
            checks.append(
                dict(identity=spec[key], sha256=h.hexdigest(), bytes=target.stat().st_size)
            )
value = dict(
    schema_version="d02-independent-byte-closure-1",
    split=split,
    passed=True,
    protocol=protocol["record_hash"],
    checks=checks,
)
output = owner.directory / "byte-audits" / (split + ".json")
if output.exists():
    if record(output) != {**value, "record_hash": digest(value)}:
        raise RuntimeError("D02 existing byte audit differs; never replace evidence")
else:
    owner.publish(budget, output, value, immutable=True)
print(json.dumps(dict(split=split, passed=True, files=len(checks))))
