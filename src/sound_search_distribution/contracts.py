"""Exact distribution/code/UI proof; no new numerical producer or permissive version range."""

import hashlib
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity
from similar_sound_search.storage import InputError, digest


def own_code():
    return {
        p.name: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for p in sorted(Path(__file__).parent.glob("*.py"))
    }


def consumer(owner):
    value = record(owner.root / "manifests/distribution/consumer.json")
    before = record(owner.root / "manifests/assessment/consumer.json")
    after = code_identity()
    allowed = {
        "application/api.py",
        "application/history.py",
        "application/queries.py",
        "application/job.py",
        "application/validation.py",
        "application/server.py",
    }
    changed = {k for k, h in before["code"].items() if after.get(k) != h}
    if (
        value["code"] != after
        or value["distribution_code"] != own_code()
        or value["before"] != before["record_hash"]
        or value["before_code"] != before["code"]
        or set(after) != set(before["code"])
        or changed != set(value["changed_files"])
        or changed - allowed
        or value["numerical_hash"] != before["numerical_hash"]
    ):
        raise InputError("D03 exact full-source/packaging compatibility proof differs")
    static = Path(__import__("similar_sound_search.application.server", fromlist=["STATIC"]).STATIC)
    for name, expected in value["web"].items():
        if (
            hashlib.sha256((static / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            != expected
        ):
            raise InputError("D03 packaged web asset differs: " + name)
    return dict(
        declaration_hash=value["record_hash"],
        numerical_hash=value["numerical_hash"],
        code_hash=digest(after),
        version="d03-consumer-1",
    )


def compatible(owner, previous):
    current = consumer(owner)
    value = record(owner.root / "manifests/distribution/consumer.json")
    if previous not in value["accepted_previous"]:
        return None
    if previous["numerical_hash"] != current["numerical_hash"]:
        raise InputError("D03 cannot accept a changed numerical producer")
    return value["record_hash"]
