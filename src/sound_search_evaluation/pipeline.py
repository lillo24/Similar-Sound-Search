"""Generated memberships through unchanged product features, scoring and fusion."""

from similar_sound_search.application import codec, history, media, queries
from similar_sound_search.application.context import payload
from similar_sound_search.application.pipeline import Capture
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.processing import cache, engine
from similar_sound_search.search import sources
from similar_sound_search.storage import InputError, digest

from . import contracts


def plan(owner, budget, arm="legacy-mean"):
    pop = contracts.population(owner)
    return dict(
        representation=contracts.representation(budget),
        consumer=contracts.consumer(owner),
        input=dict(
            sources=pop["sources"],
            historical=False,
            packing=128,
            banks=[
                dict(label=label, grid=grid)
                for label, grid in zip(("legacy", "long"), owner.protocol["banks"], strict=True)
            ],
            policy=dict(arm=arm, association=None),
        ),
        tombstones=[],
    )


def index_sources(budget, owner, ordinals):
    value = plan(owner, budget)
    pop = contracts.population(owner)
    stats = []
    producer = dict(owner="D02", consumer=value["consumer"], protocol=owner.protocol["record_hash"])
    for i in ordinals:
        source = pop["sources"][i]
        output = engine.features(budget, owner, value, source, producer, lambda _: None)
        path = owner.directory / "index" / (source["recording_id"] + ".json")
        if path.exists():
            saved = record(path)
            if saved["source"] != source or saved["features"]["rows"] != output["rows"]:
                raise InputError("D02 unchanged index/native membership differs")
        else:
            owner.publish(
                budget,
                path,
                dict(
                    schema_version="d02-index-1",
                    source=source,
                    representation=value["representation"],
                    features=output,
                    producer=producer,
                ),
                immutable=True,
            )
        stats.append(
            dict(
                source=source["recording_id"],
                new_encodes=output["new_encodes"],
                reused=output["reused_rows"],
                rows=len(output["rows"]),
            )
        )
    return dict(sources=stats, new_encodes=sum(s["new_encodes"] for s in stats))


def query_signature(recipe):
    return sorted(
        {
            digest(
                dict(
                    bytes=recipe["assets"][e["asset_id"]]["audio"]["sha256"],
                    event=e["event"],
                    context=e["context"],
                )
            )
            for e in recipe["examples"]
        }
    )


def case_for_revision(owner, revision):
    from similar_sound_search.queries.library import revision as read_revision

    recipe = read_revision(queries.QueryOwner(owner), revision)["recipe"]
    actual = query_signature(recipe)
    for case in contracts.inputs(owner)["queries"]:
        expected = sorted(
            {
                digest(dict(bytes=e["audio"]["sha256"], event=e["event"], context=e["context"]))
                for e in case["examples"]
            }
        )
        if actual == expected:
            return case["case_id"]
    raise InputError("D02 query differs from every frozen neutral input; no undeclared quality run")


def load_case(budget, owner, case_id, revision=None):
    path = owner.directory / "case-bindings" / (case_id + ".json")
    previous = record(path) if path.exists() else None
    revision = revision or previous["revision"]
    if case_for_revision(owner, revision) != case_id:
        raise InputError("D02 case/revision binding differs")
    selection = dict(
        historical=False,
        revision=revision,
        materialization=previous.get("materialization") if previous else None,
    )
    q, matrix = queries.load(budget, owner, selection)
    # Persist the cold query wrapper once. Later source freshness is a separate
    # audit, not a replacement of producer/statistical identity.
    ref = previous.get("query") if previous else None
    if ref is None:
        ref = owner.put(budget, "queries", q)
    else:
        original = owner.get(ref, "queries")
        if original["query"]["record_hash"] != q["query"]["record_hash"]:
            raise InputError("D02 validated materialization changed semantic query")
    owner.publish(
        budget,
        path,
        dict(case_id=case_id, revision=revision, materialization=q["materialization"], query=ref),
    )
    return q, matrix, ref


def publish_groups(budget, owner, result, capture):
    mapping = {}
    groups = [
        (path, data)
        for path, (kind, data) in sorted(capture.records.items())
        if kind == "group-results"
    ]
    for _, (kind, data) in sorted(capture.records.items()):
        if kind != "group-results":
            owner.put(budget, kind, data)
    for i in range(0, len(groups), 8):
        items = [payload(codec.encode("group-results", v))[0] for _, v in groups[i : i + 8]]
        container = owner.put(
            budget, "group-batches", dict(schema_version="d02-group-batch-1", items=items)
        )
        for slot, (path, _) in enumerate(groups[i : i + 8]):
            key = path.rsplit("/", 1)[-1][:-5]
            if items[slot]["record_hash"] != key:
                raise InputError("D02 group packing changed numerical content")
            mapping[key] = dict(
                path=container["path"],
                container=container["record_hash"],
                record_hash=key,
                slot=slot,
            )
    for arm in result["arms"].values():
        for key in ("complete_groups", "shortlist", "display"):
            arm[key] = [mapping[r["record_hash"]] for r in arm[key]]
    return result


def calculate(budget, owner, case_id, revision=None, category="initial"):
    """No truth read: exact source/array validation, supports and full population fusion."""
    value = plan(owner, budget)
    contracts.claim(owner, budget, case_id, category)
    q, matrix, query_ref = load_case(budget, owner, case_id, revision)
    owner.query_vectors_cache = {}
    history.cache_query(owner, q, matrix)
    scores, memberships = {}, {}
    for source in value["input"]["sources"]:
        if getattr(owner, "job_id", None):
            cancel = owner.directory / "cancels" / (owner.job_id + ".json")
            if cancel.exists() and not record(cancel).get("resumed", False):
                raise contracts.Cancelled("D02 cancelled before the next source unit")
        # Fresh full decode/PCM checks, not mtime-based reuse. Score consumption
        # independently reopens and validates every array through C04 cache.vectors.
        sources.load(budget, source, context=owner)
        path = owner.directory / "index" / (source["recording_id"] + ".json")
        index = record(path)
        if index["source"] != source or index["representation"] != value["representation"]:
            raise InputError("D02 indexed source/representation differs")
        cache.vectors(budget, owner, index["features"]["rows"])
        scores[source["recording_id"]] = engine.score(
            budget, owner, value, source, index["features"], q
        )
        memberships[source["recording_id"]] = dict(
            path=path.relative_to(owner.root).as_posix(), record_hash=index["record_hash"]
        )
    capture = Capture(owner)
    result = engine.aggregate(budget, capture, value, {}, q, scores, memberships)
    result = publish_groups(budget, owner, result, capture)
    result["population"] = value["input"]["sources"]
    aggregate = owner.put(budget, "aggregates", result)
    return dict(
        aggregate=aggregate,
        query=query_ref,
        scores=scores,
        case_id=case_id,
        new_query_encodes=q["new_encodes"],
        category=category,
    )


def prediction(budget, owner, output, scope="component", job_id=None):
    result = owner.get(output["aggregate"], "aggregates")
    q = owner.get(output["query"], "queries")
    value = dict(
        schema_version="d02-prediction-1",
        state="complete",
        case_id=output["case_id"],
        split=owner.split,
        protocol=owner.protocol["record_hash"],
        consumer=contracts.consumer(owner),
        population=contracts.population(owner)["record_hash"],
        query=output["query"],
        query_hash=result["query_hash"],
        revision=q["revision"],
        materialization=q["materialization"],
        arms=result["arms"],
        excluded_groups=result["excluded_groups"],
        scores=output["scores"],
        aggregate=output["aggregate"],
        scope=scope,
        job_id=job_id,
        category=output["category"],
        selected_representatives="Product scored_bounds; contexts are unscored",
    )
    ref = owner.put(budget, "predictions", value)
    folder = (
        "prediction-bindings"
        if output["category"] == "initial"
        else "technical-prediction-bindings"
    )
    suffix = "-" + owner.job_id if output["category"] == "technical" else ""
    path = owner.directory / folder / (owner.split + "-" + output["case_id"] + suffix + ".json")
    if path.exists():
        prior = owner.get(record(path)["prediction"], "predictions")
        if semantic(prior) != semantic(value):
            raise InputError("D02 technical reuse changed complete numerical prediction")
    else:
        owner.publish(budget, path, dict(case_id=output["case_id"], prediction=ref), immutable=True)
    return ref


def semantic(value):
    return {
        k: v
        for k, v in value.items()
        if k not in {"record_hash", "scope", "job_id", "consumer", "category"}
    }


def product_result(budget, owner, key, spec, output):
    result = owner.get(output["aggregate"], "aggregates")
    result = {**result, "selected_arm": spec["arm"]}
    cards = media.cards(budget, owner, result, 0, 10)
    ref = owner.put(
        budget,
        "results",
        dict(
            schema_version="d01-result-1",
            state="complete",
            job_id=key,
            query=output["query"],
            selection=spec["query"],
            policy=spec["arm"],
            consumer=contracts.consumer(owner),
            **result,
            cards=cards,
            chain=None,
            historical_view=False,
            resource_owner="data/runs/assessment/pool.json",
            historical_c04_state="partial 145/148",
            new_catalogue_encodes=0,
            generated_evaluation_population=True,
            defaults=dict(audio="original", arm="legacy-mean", pitch="off"),
        ),
    )
    prediction(budget, owner, output, "product-api", key)
    return ref


def saved_prediction(owner, case_id):
    binding = record(
        owner.directory / "prediction-bindings" / (owner.split + "-" + case_id + ".json")
    )
    return owner.get(binding["prediction"], "predictions")
