"""Pinned D02 consumer, neutral input signatures and prospective execution claims."""

import hashlib
from pathlib import Path

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.search.contracts import code_identity, frozen
from similar_sound_search.storage import InputError, ResourceError, digest

D01_CONSUMER = "feb882325c29159d34b723df3b8a63deea5101561aa25d68ebca24df5859860a"


class Cancelled(RuntimeError):
    """Cooperative stop at a useful boundary, with every spent charge retained."""


def own_code():
    base = Path(__file__).parent
    return {
        p.name: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for p in sorted(base.glob("*.py"))
    }


def consumer(owner):
    value = record(owner.root / "manifests/assessment/consumer.json")
    if value["code"] != code_identity() or value["evaluation_code"] != own_code():
        raise InputError("D02 source drift; exact scoped consumer declaration required")
    old = record(owner.root / "manifests/application/consumer.json")
    proof = record(owner.root / "manifests/assessment/compatibility.json")
    if (
        old["record_hash"] != D01_CONSUMER
        or value["compatibility"] != proof["record_hash"]
        or proof["before_consumer"] != old["record_hash"]
        or proof["before_code"] != old["code"]
        or proof["after_code"] != value["code"]
        or {k for k, h in old["code"].items() if value["code"].get(k) != h}
        != set(proof["changed_files"])
        or set(value["code"]) != set(old["code"])
        or set(proof["changed_files"])
        - {
            "application/api.py",
            "application/server.py",
            "application/queries.py",
            "application/history.py",
            "application/context.py",
        }
        or value["numerical_hash"] != old["numerical_hash"]
    ):
        raise InputError("D02 inherited numerical/ownership source proof differs")
    return dict(
        declaration_hash=value["record_hash"],
        numerical_hash=value["numerical_hash"],
        code_hash=digest(value["code"]),
        version="d02-consumer-1",
    )


def compatible(owner, previous):
    current = consumer(owner)
    proof = record(owner.root / "manifests/assessment/compatibility.json")
    if previous not in proof["accepted_previous"]:
        return None
    if current["numerical_hash"] != previous["numerical_hash"]:
        raise InputError("D02 scoped consumer cannot alter inherited numerical semantics")
    return proof["record_hash"]


def representation(budget):
    return frozen(budget)[-1]


def population(owner):
    value = record(owner.directory / "populations" / (owner.split + ".json"))
    if (
        value["schema_version"] != "d02-population-1"
        or value["split"] != owner.split
        or len(value["sources"]) != 32
        or len({s["group"] for s in value["sources"]}) < 24
    ):
        raise InputError("D02 genuine generated population/membership is incomplete")
    return value


def inputs(owner):
    value = record(owner.directory / "inputs" / (owner.split + ".json"))
    if value["split"] != owner.split or value["protocol"] != owner.protocol["record_hash"]:
        raise InputError("D02 neutral inputs do not bind the prospective protocol")
    return value


def claim(owner, budget, case, category="initial"):
    """Reserve both published policies before scoring; reuse an exact existing claim."""
    if category not in {"initial", "technical"}:
        raise InputError("D02 undeclared execution category")
    execution = owner.job_id
    key = digest(
        [
            owner.protocol["record_hash"],
            owner.split,
            case,
            category,
            execution if category == "technical" else None,
        ]
    )
    path = owner.directory / "execution-claims" / (key + ".json")
    if path.exists():
        prior = record(path)
        if prior["execution"] != execution:
            raise ResourceError(
                "D02 initial case already claimed by another job; use an explicit technical replay"
            )
        return prior
    existing = [record(p) for p in path.parent.glob("*.json")]
    total = sum(len(v["policies"]) for v in existing)
    technical = sum(len(v["policies"]) for v in existing if v["category"] == "technical")
    if total + 2 > 112 or (category == "technical" and technical + 2 > 8):
        raise ResourceError("D02 query-policy execution/replay allowance exhausted")
    if owner.split == "confirmation":
        frozen_candidate = record(owner.root / "manifests/assessment/candidate.json")
        if (
            frozen_candidate["protocol"] != owner.protocol["record_hash"]
            or frozen_candidate["candidate"] != "event-multi"
            or frozen_candidate["revision"] is not None
        ):
            raise InputError("D02 final candidate/gate must freeze before confirmation")
    value = dict(
        schema_version="d02-execution-claim-1",
        case=case,
        split=owner.split,
        protocol=owner.protocol["record_hash"],
        category=category,
        execution=execution,
        policies=["legacy-mean", "event-multi"],
    )
    return owner.publish(budget, path, value, immutable=True)
