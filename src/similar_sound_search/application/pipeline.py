"""Thin numerical adapters and bounded publication around the unchanged C04 engine."""

from ..evaluation.artifacts import record
from ..processing import engine
from ..processing.historical import refinement
from ..retrieval.context import Context as RetrievalContext
from ..retrieval.engine import read_shortlist
from ..storage import InputError, digest
from . import history, queries
from .context import payload


class Capture:
    """Build immutable records in bounded memory, then publish useful chunks.

    C04's exact complete-population algorithm is called unchanged. This adapter
    collects its intended records without invoking C04 publication or its pool.
    """

    def __init__(self, owner):
        self.owner, self.root, self.records = owner, owner.root, {}

    def put(self, budget, kind, value):
        from .codec import encode

        saved, _ = payload(encode(kind, value))
        ref = dict(
            path=(self.owner.directory / kind / (saved["record_hash"] + ".json"))
            .relative_to(self.root)
            .as_posix(),
            record_hash=saved["record_hash"],
        )
        self.records[ref["path"]] = (kind, value)
        return ref

    def get(self, ref, kind):
        return history.NumericalView(self.owner).get(ref, kind)


def aggregate(budget, owner, plan, values, query_result):
    capture = Capture(owner)
    oldplan = history.inputs(owner)[1]
    adapted = {
        **oldplan,
        "input": {
            **oldplan["input"],
            "policy": dict(
                arm="event-multi" if plan["arm"] == "historical-refinement" else plan["arm"],
                association=None,
            ),
        },
        "consumer": {"numerical_hash": history.consumer(owner)["numerical_hash"]},
    }
    scored = {k: v["scores"] for k, v in values.items()}
    memberships = {k: v["proof"] for k, v in values.items()}
    result = engine.aggregate(budget, capture, adapted, {}, query_result, scored, memberships)
    result["population"] = oldplan["input"]["sources"]
    return result, capture


def source_unit(budget, owner, plan, rid, query_result, qmatrix):
    proof, refs, matrix = history.adopt(budget, owner, rid)
    old, oldplan, scores, oldref = history.old_output(owner, "score", rid)
    source = proof["source"]
    raw = engine.load_scores(old, scores)
    exact = (
        query_result["query"]["record_hash"]
        == history.old_output(owner, "query", "query")[2]["query"]["record_hash"]
    )
    if exact:
        # Scores were produced across the final declared numerical contract.
        oldplan = {
            **oldplan,
            "consumer": {"numerical_hash": history.consumer(owner)["numerical_hash"]},
        }
        history.validate_scores(raw, refs, matrix, qmatrix, query_result, oldplan)
        score_ref = scores
        proof.update(score_unit=oldref, score_dependencies_verified=True)
    else:
        view = history.NumericalView(owner)
        history.cache_query(view, query_result, qmatrix)
        adapted = {
            **oldplan,
            "consumer": {"numerical_hash": history.consumer(owner)["numerical_hash"]},
        }
        score_ref = engine.score(budget, view, adapted, source, dict(rows=refs), query_result)
        proof.update(score_unit=None, query_dependent_scores=True)
    return dict(proof=owner.put(budget, "adoptions", proof), scores=score_ref, new_encodes=0)


def audit_chain(budget, owner, plan, aggregate_result, query_result):
    old, oldplan, _ = history.inputs(owner)
    view = history.NumericalView(owner)
    # Legacy output compared against the complete pinned C02 population, including exact
    # original native intervals and distances. Row IDs differ by semantic-key scheme.
    previous = RetrievalContext(owner.root)
    execution, _ = read_shortlist(previous, owner.protocol["execution"], "legacy-mean")
    for arm in ("legacy-mean", "event-multi"):
        before = [previous.get(r, "c03-groups") for r in execution["arms"][arm]["complete_groups"]]
        after = [
            owner.get(r, "group-results") for r in aggregate_result["arms"][arm]["complete_groups"]
        ]
        if len(before) != len(after):
            raise InputError("D01 full eligible group denominator differs from C02")
        for a, b in zip(before, after, strict=True):
            ar, br = a["passages"][0]["representative"], b["passages"][0]["representative"]
            if (
                a["group"] != b["group"]
                or a["score"] != b["score"]
                or ar["recording_id"] != br["recording_id"]
                or ar["original_bounds"] != br["original_bounds"]
            ):
                raise InputError(
                    "D01 complete legacy/event order, score or native representative differs"
                )
    # Audit original C02 support rows against native C01 arrays, not only C03's self hashes.
    from ..refinement import importing

    bank_view, banks = history.bank_reader(owner)
    _, input_groups = read_shortlist(previous, owner.protocol["execution"], "event-multi")
    _, qmatrix = queries.load(budget, owner, plan["query"])
    for g in input_groups:
        importing.group_rows(
            budget, owner, previous, g, bank_view, banks, query_result["query"], qmatrix
        )
    adapted = {**oldplan, "consumer": history.consumer(owner)}
    result = refinement(budget, view, adapted, aggregate_result, query_result)
    declaration = record(owner.root / "manifests/refinement/report-repair.json")
    publication = record(owner.root / "manifests/refinement/consumer-publication.json")
    if (
        publication["record_hash"]
        != "d062a58002c8e1eb8a03e0f978f975403a54ba57fec618c6651bbcc0f55ca085"
        or declaration["record_hash"]
        != "05e6594f057eb6910f5b9590e94dce92508ba01de9b03efd7f80db05a1a0219c"
    ):
        raise InputError("D01 C03 separate numerical/report consumer declaration differs")
    result.update(
        resource_owner="D01",
        old_request_state="C04 remains partial, 145/148",
        full_support_rows_verified=True,
        baseline_legacy_exact=True,
        baseline_event_order_exact=True,
        c03_report_consumer=declaration["record_hash"],
    )
    return result


def geometry_estimate(owner, examples=1):
    """Whole-population admission geometry without decoding or inference.

    Distinct generated support hashes/float values avoid an unrealistically
    compressible repeated row. The largest group is charged for both arms/all
    groups, plus complete source and finalization transitions and pool writes.
    """
    from .codec import encode

    if not 1 <= examples <= 8:
        raise InputError("D01 geometry needs one to eight examples")
    rows = []
    for i in range(examples * 2 * 16):
        values = [int(digest([i, k])[:13], 16) / 16**13 for k in range(examples)]
        rows.append(
            dict(
                row_id=digest(["row", i]),
                recording_id="e" * 64,
                group="d" * 64,
                bank_hash=digest(["bank", i % 2]),
                original_bounds=[i * 11025, i * 11025 + 105840],
                original_context=[max(0, i * 11025 - 44100), i * 11025 + 149940],
                per_example_distances=values,
                rate=44100,
                distance=values[0],
                signal_id="e" * 64,
                signal_bounds=[i * 11025, i * 11025 + 105840],
                padding_is_support=False,
                credit=values[0],
                event_id=digest(["event", i % examples]),
                variant_id=digest(["variant", i % examples]),
                bank_id=digest(["bank", i % 2]),
                master_offset=None,
                master_offset_evidence=None,
            )
        )
    group = dict(
        schema_version="c04-group-1",
        rank=72,
        group="d" * 64,
        score=0.1,
        passages=[
            dict(
                representative=rows[k],
                supports=rows[k::3],
                scored_bounds=rows[k]["original_bounds"],
                display_envelope=rows[k]["original_bounds"],
                envelope_is_scored=False,
            )
            for k in range(3)
        ],
        contributions=[
            dict(
                event_id=digest(["event", i]),
                bank_hash=digest(["bank", i % 2]),
                rank=72,
                credit=0.1,
                best_row=digest(["row", i]),
                variant_id=digest(["variant", i]),
            )
            for i in range(examples * 2)
        ],
    )
    _, largest = payload(encode("group-results", group))
    # Include newly produced per-source score payloads (up to eight per-example
    # distances on every support), all pool writes and final media/query bookkeeping.
    # Old scores reused by reference can cost less; that is not an admission assumption.
    estimate = 144 * (largest * 2 + 16384) + 72 * (512 * 1024) + 32 * (256 * 1024)
    return dict(
        schema_version="d01-geometry-1",
        groups=72,
        arms=2,
        max_examples=examples,
        largest_group_counted_bytes=largest,
        complete_path_counted_bytes=estimate,
        ordinary_ceiling=96 * 1024**2,
        protected_bytes=32 * 1024**2,
        fits=estimate < 96 * 1024**2,
        inference=False,
    )


def metadata_preflight(budget, owner):
    """Exact private 72-group geometry; proposed ranks are not adopted results."""
    old, plan, _ = history.inputs(owner)
    q = history.old_output(owner, "query", "query")[2]
    values = {}
    for source in plan["input"]["sources"]:
        rid = source["recording_id"]
        values[rid] = dict(
            scores=history.old_output(owner, "score", rid)[2],
            proof=history.old_output(owner, "features", rid)[3],
        )
    result, capture = aggregate(budget, owner, dict(arm="legacy-mean"), values, q)
    sizes = [
        payload(
            __import__("similar_sound_search.application.codec", fromlist=["encode"]).encode(
                kind, data
            )
        )[1]
        for kind, data in capture.records.values()
    ]
    previous = RetrievalContext(owner.root)
    execution, _ = read_shortlist(previous, owner.protocol["execution"], "legacy-mean")
    comparisons = {}
    for arm in ("legacy-mean", "event-multi"):
        after = [capture.records[r["path"]][1] for r in result["arms"][arm]["complete_groups"]]
        before = [previous.get(r, "c03-groups") for r in execution["arms"][arm]["complete_groups"]]
        comparisons[arm] = dict(
            groups=len(after),
            order=[g["group"] for g in after] == [g["group"] for g in before],
            max_score_delta=max(
                abs(a["score"] - b["score"]) for a, b in zip(after, before, strict=True)
            ),
            native_representatives=all(
                a["passages"][0]["scored_bounds"] == b["passages"][0]["scored_bounds"]
                for a, b in zip(after, before, strict=True)
            ),
        )
    return dict(
        geometry=geometry_estimate(owner),
        eight_example_geometry=geometry_estimate(owner, 8),
        proposed_records=len(sizes),
        counted_publication_bytes=sum(sizes),
        largest_record=max(sizes),
        comparisons=comparisons,
        audio_inference=False,
        scope="metadata preflight only; no freshness/completion claim",
    )
