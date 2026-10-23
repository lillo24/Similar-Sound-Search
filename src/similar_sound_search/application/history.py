"""Read-only adoption of exact C04 units and C01 banks, independent of query choice.

Old guards/declarations are never rewritten. The D01 declaration pins the entire
inherited source map; sources/PCM, memberships and arrays receive fresh D01 proofs.
"""

import numpy as np

from ..evaluation.artifacts import record
from ..indexing import reader
from ..indexing.context import Context as IndexContext
from ..processing import cache, contracts, records
from ..processing.api import graph
from ..processing.context import Context as OldContext
from ..processing.job import output
from ..search import sources
from ..search.contracts import code_identity, grid
from ..search.ranking import distances
from ..storage import InputError, contained, digest


def consumer(owner):
    declaration = record(owner.root / "manifests/application/consumer.json")
    current = code_identity()
    if declaration["code"] != current:
        raise InputError("D01 consumer source drift; explicit scoped declaration required")
    old = record(owner.root / "manifests/processing/consumer.json")
    if (
        old["record_hash"] != owner.protocol["c04_consumer"]
        or any(current.get(k) != h for k, h in old["code"].items())
        or set(current) - set(old["code"]) != set(declaration["new_files"])
    ):
        raise InputError("D01 inherited numerical/coordinator source proof changed")
    return dict(
        declaration_hash=declaration["record_hash"],
        numerical_hash=old["numerical_hash"],
        code_hash=digest(current),
        version="d01-consumer-1",
    )


def inputs(owner):
    old = OldContext(owner.root)
    key = owner.protocol["c04_job"]
    job = record(old.directory / "jobs" / (key + ".json"))
    if job["record_hash"] != key or job["plan"]["record_hash"] != owner.protocol["c04_plan"]:
        raise InputError("D01 pinned C04 job/plan differs")
    plan = old.get(job["plan"], "plans")
    state = record(old.directory / "progress" / (key + ".json"))
    if (
        plan["schema_version"] != "c04-plan-1"
        or plan["units"] != graph(plan["input"])
        or plan["protocol_hash"] != digest(old.protocol)
        or state["result"] is not None
        or len(state["completed"]) != 145
        or old.get(plan["input_ref"], "inputs")["value"] != plan["input"]
    ):
        raise InputError("D01 historical partial chain/schema changed")
    # Strict historical import remains strict. Bank reading below is query independent.
    from ..processing.historical import inspect_inputs

    inspect_inputs(old, plan["input"])
    if len(plan["input"]["sources"]) != 72:
        raise InputError("D01 exact historical population required")
    return old, plan, state


def bank_reader(owner):
    """Fresh bank metadata view, with no historical consumer receipt borrowed.

    Exact C01 plans/memberships are revalidated. Legacy metadata is expanded from
    its pinned record; each consumed array/native/source is audited by adopt().
    This operation does not bind a query and cannot authorize encoding.
    """
    view = IndexContext(owner.root)
    snap = record(view.indexes / "snapshots" / (owner.protocol["snapshot"] + ".json"))
    if snap["record_hash"] != owner.protocol["snapshot"]:
        raise InputError("D01 pinned C01 snapshot changed")
    banks = []
    for key in owner.protocol["primary_banks"]:
        ref = next(r for r in snap["banks"] if r["record_hash"] == key)
        path = contained(owner.root / ref["path"], view.indexes)
        value = record(path)
        if value["record_hash"] != key or value["coverage"]["state"] != "complete":
            raise InputError("D01 incomplete/changed bank")
        if value["schema_version"] == "c01-legacy-reference-1":
            expanded = []
            for u in value["committed"]:
                meta = record(
                    contained(owner.root / u["path"], owner.root / "data/indexes/a06")
                    / "record.json"
                )
                if meta["record_hash"] != u["array_record_hash"] or meta["shape"][0] != u["rows"]:
                    raise InputError("D01 legacy array receipt differs")
                expanded.append({**u, "identity": meta["identity"], "array": meta})
            value = {**value, "committed": expanded}
        else:
            value = reader.read_bank(None, view, path)
        banks.append(dict(value=value, binding=dict(historical_bank_hash=key)))
    if banks[0]["value"]["signals"] != banks[1]["value"]["signals"]:
        raise InputError("D01 banks disagree on exact population/ancestry")
    return view, banks


def old_output(owner, kind, subject):
    old, plan, state = inputs(owner)
    unit = next(u for u in plan["units"] if u["kind"] == kind and u["subject"] == subject)
    return old, plan, output(old, state, unit), state["completed"][unit["unit_id"]]


def adopt(budget, owner, rid):
    old, plan, features, ref = old_output(owner, "features", rid)
    source = next(s for s in plan["input"]["sources"] if s["recording_id"] == rid)
    sources.load(budget, source, context=owner)
    refs = records.expand(features).get("rows", features.get("rows"))
    expected = contracts.native_rows(source, plan["input"]["banks"])
    if [r["native_bounds"] for r in refs] != [list(b) for b in expected]:
        raise InputError("D01 native union differs from complete grid")
    matrix = cache.vectors(budget, old, refs)
    view, banks = bank_reader(owner)
    native = {}
    producers = []
    for bank in banks:
        value = bank["value"]
        if value["signals"][rid]["original"] != source:
            raise InputError("D01 bank source/group differs")
        bounds = []
        for unit in value["committed"]:
            if unit["signal_id"] != rid:
                continue
            arr, passages = reader.rows(budget, view, value, unit)
            for i, p in enumerate(passages):
                b = tuple(p["original_bounds"])
                native[b] = cache.vector_hash(arr[i])
                bounds.append(list(b))
            producers.append(
                dict(
                    bank=bank["binding"]["historical_bank_hash"],
                    array=unit["array"]["record_hash"],
                    membership=digest(passages),
                )
            )
        if bounds != [
            list(b)
            for b in grid(
                source["source"]["sample_count"],
                source["source"]["sample_rate_hz"],
                value["bank"]["identity"]["grid"],
            )
        ]:
            raise InputError("D01 original complete bank membership differs")
    if any(native.get(tuple(r["native_bounds"])) != r["vector_sha256"] for r in refs):
        raise InputError("D01 C04/C01 semantic array mismatch")
    audit = old.get(features["audit"], "consumer-audits")
    if audit["source"] != source or not audit["canonical_pcm_verified"] or audit["new_embeddings"]:
        raise InputError("D01 incompatible C04 source audit")
    proof = dict(
        schema_version="d01-bank-adoption-1",
        source=source,
        old_unit=ref,
        old_audit=features["audit"],
        consumer=consumer(owner),
        membership_digest=digest(refs),
        rows=len(refs),
        producers=producers,
        source_pcm_verified=True,
        new_catalogue_encodes=0,
    )
    return proof, refs, matrix


def validate_scores(raw, refs, matrix, qmatrix, query_result, plan):
    identity = dict(
        version="c04-source-distances-2",
        candidate_rows=len(refs),
        candidate_digest=digest([[r["key"], r["vector_sha256"]] for r in refs]),
        query_features=query_result["feature_hash"],
        numerical_contract=plan["consumer"]["numerical_hash"],
        banks=[b["grid"] for b in plan["input"]["banks"]],
    )
    if raw["schema_version"] != "c04-source-scores-1" or raw["identity"] != identity:
        raise InputError("D01 score dependency identity differs")
    per, means = distances(qmatrix, matrix, "cosine")
    lookup = {r["key"]: i for i, r in enumerate(refs)}
    source = next(
        s for s in plan["input"]["sources"] if contracts.source_key(s) == refs[0]["source_key"]
    )
    offset = {tuple(r["native_bounds"]): i for i, r in enumerate(refs)}
    if len(raw["banks"]) != len(plan["input"]["banks"]):
        raise InputError("D01 score bank population differs")
    for bank, policy in zip(raw["banks"], plan["input"]["banks"], strict=True):
        indices = [
            offset[tuple(b)]
            for b in grid(
                source["source"]["sample_count"], source["source"]["sample_rate_hz"], policy["grid"]
            )
        ]
        best = min(
            indices, key=lambda i: (float(means[i]), *refs[i]["native_bounds"], refs[i]["key"])
        )
        if bank["count"] != len(indices) or bank["baseline"]["key"] != refs[best]["key"]:
            raise InputError("D01 complete bank best/count differs")
        if len(bank["supports"]) != len(qmatrix):
            raise InputError("D01 score query-example population differs")
        for k, support in enumerate(bank["supports"]):
            order = sorted(
                indices, key=lambda i: (float(per[k, i]), *refs[i]["native_bounds"], refs[i]["key"])
            )[:16]
            if [r["key"] for r in support] != [refs[i]["key"] for i in order]:
                raise InputError("D01 exact top support ordering differs")
        for row in [bank["baseline"], *[r for group in bank["supports"] for r in group]]:
            i = lookup[row["key"]]
            if (
                row["bounds"] != refs[i]["native_bounds"]
                or not np.allclose(per[:, i], row["per"], rtol=0, atol=2e-15)
                or abs(float(means[i]) - row["mean"]) > 2e-15
            ):
                raise InputError("D01 historical score/native dependency validation failed")
    return True


class NumericalView:
    """Existing C04 operations, historical row store and D01-only publication.

    The unchanged score reader can reuse a historical locator. New score locators
    are redirected to D01; no method writes or charges a historical owner.
    """

    def __init__(self, owner):
        self.owner = owner
        self.root, self.protocol = owner.root, owner.protocol
        self.directory = owner.root / "data/runs/processing"
        self.query_vectors_cache = {}

    def put(self, *args, **kwargs):
        return self.owner.put(*args, **kwargs)

    def get(self, ref, kind):
        if ref["path"].startswith("data/runs/processing/"):
            return OldContext(self.root).get(ref, kind)
        return self.owner.get(ref, kind)

    def publish(self, budget, path, value, immutable=False):
        relative = contained(path, self.directory / "scores").relative_to(self.directory)
        return self.owner.publish(budget, self.owner.directory / relative, value, immutable)

    def charge(self, *args, **kwargs):
        return self.owner.charge(*args, **kwargs)


def cache_query(view, value, matrix):
    key = digest(
        dict(
            query=value["query"]["record_hash"],
            features=value["feature_hash"],
            saved=value.get("saved_input"),
        )
    )
    view.query_vectors_cache[key] = matrix


def compatible(owner, previous):
    """Only the explicitly pinned D01 path/accounting repair, no unknown drift."""
    current = consumer(owner)
    proof = record(owner.root / "manifests/application/compatibility.json")
    declaration = record(owner.root / "manifests/application/consumer.json")
    if declaration.get("compatibility") != proof["record_hash"]:
        raise InputError("D01 compatibility declaration binding changed")
    if (
        previous not in [proof["before"], *proof.get("additional_before", [])]
        or proof["after_code"] != code_identity()
        or current["numerical_hash"] != previous["numerical_hash"]
    ):
        return None
    if proof["changed_inherited_files"] or not proof["numerical_functions_unchanged"]:
        raise InputError("D01 compatibility changes inherited numerical code")
    return proof["record_hash"]
