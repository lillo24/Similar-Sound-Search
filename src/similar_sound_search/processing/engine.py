"""Bounded native feature, query and per-source numerical units; complete-population fusion."""

import numpy as np

from ..evaluation.artifacts import record
from ..indexing import ranking as baseline
from ..retrieval import engine as retrieval_engine
from ..retrieval import fusion
from ..retrieval.context import configuration as retrieval_configuration
from ..search import sources
from ..search.contracts import grid
from ..search.ranking import distances, excluded_source
from ..storage import InputError, digest
from . import cache, contracts


def features(budget, owner, plan, source, producer, fault):
    if plan["input"]["historical"]:
        from .historical import adopt_source

        return adopt_source(budget, owner, plan, source, producer)
    desc = plan["representation"]
    samples = sources.load(budget, source, context=owner)
    required = contracts.native_rows(source, plan["input"]["banks"])
    have = cache.lookup(owner, source, desc, budget)
    missing = [b for b in required if contracts.row_key(source, b, desc) not in have]
    new = 0
    size = plan["input"]["packing"]
    for i in range(0, len(missing), size):
        new += cache.encode(
            budget, owner, source, desc, samples, missing[i : i + size], producer, fault
        )
    rows = cache.lookup(owner, source, desc, budget)
    return dict(
        source=source["recording_id"],
        rows=[rows[contracts.row_key(source, b, desc)] for b in required],
        new_encodes=new,
        reused_rows=len(required) - new,
        validated_source=True,
    )


def query(budget, owner, plan, producer, fault):
    value = plan["input"]["query"]
    if value["kind"] in {"saved", "saved-derived"}:
        from .historical import saved_query

        return saved_query(budget, owner, value)
    source, desc = value["source"], plan["representation"]
    samples = sources.load(budget, source, context=owner)
    have = cache.lookup(owner, source, desc, budget)
    bounds = sorted(set(map(tuple, value["bounds"])))
    missing = [b for b in bounds if contracts.row_key(source, b, desc) not in have]
    n = (
        cache.encode(budget, owner, source, desc, samples, missing, producer, fault)
        if missing
        else 0
    )
    have = cache.lookup(owner, source, desc, budget)
    refs = [have[contracts.row_key(source, b, desc)] for b in bounds]
    examples = [
        dict(
            example_id=r["key"],
            audio=dict(duration_seconds=(b[1] - b[0]) / source["source"]["sample_rate_hz"]),
            prepared=dict(
                source=dict(sha256=source["source"]["sha256"]),
                technical_metadata=dict(canonical_pcm=source["source"]["canonical_pcm"]),
            ),
        )
        for r, b in zip(refs, bounds, strict=True)
    ]
    q = dict(
        schema_version="c04-native-query-1",
        examples=examples,
        identity=dict(
            excluded_groups=sorted(set(value["excluded_groups"]) | {source["group"]}),
            representation=desc,
        ),
        native_source=source,
        native_bounds=[list(b) for b in bounds],
        lineage=value["lineage"],
    )
    q["record_hash"] = digest(q)
    return dict(
        query=q,
        features=refs,
        new_encodes=n,
        feature_hash=digest([r["vector_sha256"] for r in refs]),
    )


def query_vectors(budget, owner, value):
    if "features" in value:
        return cache.vectors(budget, owner, value["features"])
    from .historical import saved_query

    return saved_query(budget, owner, value["saved_input"], arrays=True)[1]


def score(budget, owner, plan, source, feature_result, query_result):
    refs = feature_result["rows"]
    q = query_result["query"]
    query_hash = query_result["feature_hash"]
    identity = dict(
        version="c04-source-distances-1",
        candidate=[[r["key"], r["vector_sha256"]] for r in refs],
        query_features=query_hash,
        numerical_contract=plan["consumer"]["numerical_hash"],
        banks=[b["grid"] for b in plan["input"]["banks"]],
    )
    key = digest(identity)
    path = owner.directory / "scores" / (key + ".json")
    # All candidate arrays have been verified by this job's feature unit; reopen again
    # at actual consumption so external corruption cannot be hidden by cached scores.
    matrix = cache.vectors(budget, owner, refs)
    if path.exists():
        value = record(path)
        if value["identity"] != identity:
            raise InputError("C04 score dependency locator changed")
        return load_scores(owner, value)
    examples = query_vectors(budget, owner, query_result)
    per, means = distances(examples, matrix, "cosine")
    offsets = {tuple(r["native_bounds"]): i for i, r in enumerate(refs)}
    banks = []
    rate = source["source"]["sample_rate_hz"]
    for b in plan["input"]["banks"]:
        indices = [
            offsets[tuple(v)] for v in grid(source["source"]["sample_count"], rate, b["grid"])
        ]
        best = min(
            indices, key=lambda i: (float(means[i]), *refs[i]["native_bounds"], refs[i]["key"])
        )
        supports = []
        for k in range(len(q["examples"])):
            order = sorted(
                indices, key=lambda i: (float(per[k, i]), *refs[i]["native_bounds"], refs[i]["key"])
            )[:16]
            supports.append(
                [
                    dict(
                        key=refs[i]["key"],
                        bounds=refs[i]["native_bounds"],
                        per=per[:, i].tolist(),
                        mean=float(means[i]),
                    )
                    for i in order
                ]
            )
        banks.append(
            dict(
                count=len(indices),
                baseline=dict(
                    key=refs[best]["key"],
                    bounds=refs[best]["native_bounds"],
                    per=per[:, best].tolist(),
                    mean=float(means[best]),
                ),
                supports=supports,
            )
        )
    result = dict(schema_version="c04-source-scores-1", identity=identity, banks=banks)
    # Dependency-keyed immutable locator explicitly binds a content-addressed record.
    ref = owner.put(budget, "score-results", result)
    owner.publish(budget, path, dict(identity=identity, result=ref), immutable=True)
    return result


def load_scores(owner, value):
    return (
        owner.get(value["result"], "score-results")
        if "result" in value and "banks" not in value
        else value
    )


def aggregate(budget, owner, plan, features_by_source, queries, scored, memberships=None):
    cfg = retrieval_configuration(owner.root)
    q = queries["query"]
    variants = [v["example_id"] for v in q["examples"]]
    association = plan["input"]["policy"]["association"]
    if association is not None:
        if "native_source" not in q:
            raise InputError(
                "C04 saved-query custom association requires an unsupported native witness adapter"
            )
        source = q["native_source"]
        expected = {
            v: dict(
                source_pcm=source["source"]["canonical_pcm"]["sha256"],
                native_bounds=b,
                rate=source["source"]["sample_rate_hz"],
            )
            for v, b in zip(variants, q["native_bounds"], strict=True)
        }
        if association != expected:
            raise InputError(
                "C04 event association differs from actual query native parent witness"
            )
    event_map = fusion.events(variants, plan["input"]["policy"]["association"])
    bank_keys = [
        digest(
            dict(version="c04-bank-policy-1", grid=b["grid"], representation=plan["representation"])
        )
        for b in plan["input"]["banks"]
    ]
    complete = []
    for source in sorted(plan["input"]["sources"], key=lambda s: s["recording_id"]):
        rid = source["recording_id"]
        raw = load_scores(owner, scored[rid])
        value = dict(
            source_id=rid,
            group=source["group"],
            objectives={},
            opportunities={},
            baseline=None,
            baseline_row=None,
            excluded=excluded_source(source, q),
            source_ref=owner.put(
                budget, "sources", dict(schema_version="c04-source-1", source=source)
            ),
        )
        if value["excluded"]:
            complete.append(value)
            continue
        for k, (bank, bh) in enumerate(zip(raw["banks"], bank_keys, strict=True)):

            def passage(row):
                return dict(
                    row_id=row["key"],
                    signal_id=rid,
                    original_bounds=row["bounds"],
                    signal_bounds=row["bounds"],
                    bank_id=bh,
                    padding_is_support=False,
                )

            if k == 0:
                row = bank["baseline"]
                value["baseline"] = baseline.hit(
                    source, q, np.asarray(row["per"]), row["mean"], passage(row)
                )
                value["baseline_row"] = retrieval_engine.evidence(
                    source, bh, passage(row), row["per"], row["mean"]
                )
            value["opportunities"][bh] = bank["count"]
            for i, variant in enumerate(variants):
                rows = [
                    retrieval_engine.evidence(source, bh, passage(r), r["per"], r["per"][i])
                    for r in bank["supports"][i]
                ]
                value["objectives"][bh + ":" + variant] = dict(count=bank["count"], rows=rows)
        complete.append(value)
    groups = retrieval_engine.group_sources(complete, cfg)
    arms = {}
    for arm in ("legacy-mean", "event-legacy", "event-multi"):
        ranking = fusion.results(groups, event_map, bank_keys, cfg, arm)
        refs = [
            owner.put(budget, "group-results", dict(schema_version="c04-group-1", rank=i + 1, **g))
            for i, g in enumerate(ranking)
        ]
        arms[arm] = dict(
            complete_groups=refs,
            shortlist=refs[:20],
            display=refs[:10],
            eligible_groups=len(refs),
            shortfall_reason=None
            if len(refs) >= 20
            else "fewer eligible groups in the complete population",
        )
    memberships = memberships or {
        k: owner.put(budget, "population-memberships", dict(source=k, rows=v["rows"]))
        for k, v in features_by_source.items()
    }
    snapshot = owner.put(
        budget,
        "snapshots",
        dict(
            schema_version="c04-snapshot-1",
            state="complete",
            population=plan["input"]["sources"],
            banks=plan["input"]["banks"],
            bank_keys=bank_keys,
            memberships=memberships,
            tombstones=plan["tombstones"],
        ),
    )
    return dict(
        snapshot=snapshot,
        arms=arms,
        events=event_map,
        excluded_groups=sorted(
            set(q["identity"]["excluded_groups"]) | {s["group"] for s in complete if s["excluded"]}
        ),
        query_hash=q["record_hash"],
        selected_arm=plan["input"]["policy"]["arm"],
        complete_groups=len(groups),
        population_count=len(complete),
        all_eligible_groups_ranked=True,
    )
