"""Read-only C01/C02/C03 adapters with fresh C04 source/array and consumer proofs."""

import numpy as np

from ..evaluation.artifacts import record
from ..events import compatibility
from ..indexing import reader
from ..refinement import geometry
from ..refinement.context import Context as RefinementContext
from ..retrieval.context import Context as RetrievalContext
from ..retrieval.context import load_query
from ..retrieval.engine import read_shortlist
from ..retrieval.history import BankView
from ..search import sources
from ..search.contracts import load_array
from ..search.report import verify_bundle
from ..storage import InputError, contained, digest
from . import cache, contracts


def inspect_inputs(owner, value):
    """Metadata-only exact membership; no source/array freshness claim."""
    snapshot = record(
        owner.root / "data/indexes/c01/snapshots" / (owner.protocol["snapshot"] + ".json")
    )
    if (
        snapshot["record_hash"] != owner.protocol["snapshot"]
        or snapshot["schema_version"] != "c01-index-snapshot-1"
    ):
        raise InputError("C04 historical snapshot differs")
    expected = []
    for key in owner.protocol["primary_banks"]:
        refs = [r for r in snapshot["banks"] if r["record_hash"] == key]
        if len(refs) != 1:
            raise InputError("C04 required complete bank missing/duplicated")
        bank = record(contained(owner.root / refs[0]["path"], owner.root / "data/indexes"))
        if bank["record_hash"] != key or bank["coverage"]["state"] != "complete":
            raise InputError("C04 historical primary bank incomplete or changed")
        expected.append(bank)
    legacy = expected[0]
    if sorted(value["sources"], key=lambda s: s["recording_id"]) != sorted(
        [s["original"] for s in legacy["signals"].values()], key=lambda s: s["recording_id"]
    ):
        raise InputError("C04 historical mode requires exact 72-source ancestry/population")
    grids = [b["bank"]["identity"]["grid"] for b in expected]
    if [b["grid"] for b in value["banks"]] != grids:
        raise InputError("C04 historical bank policy/native grid differs")
    if value["query"] != dict(
        kind="saved",
        revision=owner.protocol["delivery"]["revision"],
        materialization=owner.protocol["delivery"]["materialization"],
    ):
        raise InputError("C04 historical refinement/query dependency changed")
    return snapshot, expected


def adopt_source(budget, owner, plan, source, producer):
    _, expected = inspect_inputs(owner, plan["input"])
    path = owner.root / "data/indexes/a06" / compatibility.INDEX / "index.json"
    index, desc, cfg, identity = compatibility.snapshot(budget, path)
    if desc != plan["representation"]:
        raise InputError("C04 historical representation incompatible")
    samples = sources.load(budget, source, context=owner)
    del samples
    view = BankView(owner)
    legacy = expected[0]
    value = {**legacy, "committed": []}
    for unit in legacy["committed"]:
        if unit["signal_id"] != source["recording_id"]:
            continue
        meta = record(owner.root / unit["path"] / "record.json")
        witness = identity["nodes"][source["recording_id"]]["shards"].get(unit["unit_id"])
        if (
            not witness
            or witness["record_hash"] != meta["record_hash"]
            or unit["array_record_hash"] != meta["record_hash"]
        ):
            raise InputError("C04 original legacy membership/producer differs")
        value["committed"].append({**unit, "identity": meta["identity"], "array": meta})
    snapshot = record(view.indexes / "snapshots" / (owner.protocol["snapshot"] + ".json"))
    long_ref = next(
        r for r in snapshot["banks"] if r["record_hash"] == owner.protocol["primary_banks"][1]
    )
    long = reader.read_bank(budget, view, owner.root / long_ref["path"])
    if long["record_hash"] != owner.protocol["primary_banks"][1]:
        raise InputError("C04 long-bank immutable identity changed")
    seen, array_hashes, originals = set(), [], []
    for number, bank in enumerate((value, long)):
        bounds = []
        if bank["signals"][source["recording_id"]]["original"] != source:
            raise InputError("C04 historical banks disagree on source/group")
        for unit in bank["committed"]:
            if unit["signal_id"] != source["recording_id"]:
                continue
            array, passages = reader.rows(budget, view, bank, unit)
            native = [p["original_bounds"] for p in passages]
            bounds.extend(native)
            cache.register(
                budget,
                owner,
                source,
                desc,
                native,
                array,
                owner.root / unit["path"],
                unit["array"],
                dict(
                    owner="A06" if number == 0 else "C01",
                    original_unit=unit["unit_id"],
                    historical_bank_hash=owner.protocol["primary_banks"][number],
                    original_producer=index["identity"]["code"]
                    if number == 0
                    else long["plan_value"]["producer"],
                    original_membership=digest(passages),
                ),
            )
            array_hashes.append(unit["array"]["sha256"])
            originals.append(
                dict(
                    bank_hash=owner.protocol["primary_banks"][number],
                    unit=unit["unit_id"],
                    passage_digest=digest(passages),
                    rows=len(passages),
                )
            )
            seen.update(contracts.row_key(source, b, desc) for b in native)
        from ..search.contracts import grid

        if bounds != [
            list(b)
            for b in grid(
                source["source"]["sample_count"],
                source["source"]["sample_rate_hz"],
                cfg if number == 0 else long["bank"]["identity"]["grid"],
            )
        ]:
            raise InputError("C04 historical native rows differ from exact complete grid")
    rows = cache.lookup(owner, source, desc, budget)
    requested = contracts.native_rows(source, plan["input"]["banks"])
    if set(rows) != seen or len(requested) != len(seen):
        raise InputError("C04 historical row population differs")
    audit = owner.put(
        budget,
        "consumer-audits",
        dict(
            schema_version="c04-source-audit-1",
            source=source,
            consumer=plan["consumer"],
            legacy_index=index["record_hash"],
            historical_contract_audit=digest(identity["audit"]),
            arrays=array_hashes,
            original_memberships=originals,
            canonical_pcm_verified=True,
            new_embeddings=0,
        ),
    )
    return dict(
        source=source["recording_id"],
        rows=[rows[contracts.row_key(source, b, desc)] for b in requested],
        audit=audit,
        new_encodes=0,
        reused_rows=len(requested),
        validated_source=True,
    )


def saved_query(budget, owner, value, arrays=False):
    rev, saved, q, features = load_query(
        budget,
        owner,
        value["revision"],
        value["materialization"],
        derived=value["kind"] == "saved-derived",
    )
    if q["identity"]["representation"] != __import__(
        "similar_sound_search.matchers.models", fromlist=["descriptor"]
    ).descriptor(owner.root, "efficientat"):
        raise InputError("C04 saved query representation differs")
    output = dict(
        query=q,
        saved_input=value,
        revision=rev["revision_id"],
        materialization=saved["materialization_id"],
        feature_hash=q["feature_hash"],
        new_encodes=0,
    )
    return (output, features) if arrays else output


def refinement(budget, owner, plan, aggregate, query_result):
    """Import and audit existing local alternatives; never call closed C03 workers."""
    old = RetrievalContext(owner.root)
    execution, groups = read_shortlist(old, owner.protocol["execution"], arm="event-multi")
    view = RefinementContext(owner.root)
    value = view.get(owner.protocol["refinement_execution"], "executions")
    if (
        value.get("schema_version") != "c03-c04-refinement-1"
        or value["state"] != "complete"
        or len(value["groups"]) != 20
        or value["input_order"] != [g["group"] for g in groups]
        or query_result["query"]["record_hash"] != execution["identity"]["query_hash"]
    ):
        raise InputError("C04 C03 execution/query/order binding differs")
    selected = [
        owner.get(r, "group-results")["group"]
        for r in aggregate["arms"]["event-multi"]["shortlist"]
    ]
    if selected != value["input_order"]:
        raise InputError("C04 complete-population event ranks differ from C02/C03 order")
    qfeatures = saved_query(budget, owner, plan["input"]["query"], arrays=True)[1]
    variants = [e["example_id"] for e in query_result["query"]["examples"]]
    source_map = {s["recording_id"]: s for s in plan["input"]["sources"]}
    proofs = []
    for i, ref in enumerate(value["groups"]):
        g = view.get(ref, "groups")
        if (
            g["schema_version"] != "c03-c04-group-1"
            or g["rank"] != i + 1
            or g["original_rank"] != i + 1
            or g["input"] != groups[i]
            or g["ranking_changed"]
        ):
            raise InputError("C04 C03 group/original representatives changed")
        for anchor in g["anchors"]:
            for row in anchor["rows"]:
                source = source_map[row["recording_id"]]
                f = row["feature"]
                if f.get("native_bounds") != row["original_bounds"]:
                    raise InputError("C04 C03 local native membership differs")
                if "bundle" in f:
                    p = contained(owner.root / f["bundle"]["path"], view.features)
                    meta = record(p / "record.json")
                    arr, meta = load_array(p, meta["identity"], budget)
                    native = meta["identity"]["semantic"]["bounds"]
                    if (
                        meta["record_hash"] != f["bundle"]["record_hash"]
                        or native[f["row"]] != row["original_bounds"]
                        or meta["identity"]["semantic"]
                        != geometry.semantic(source, native, plan["representation"])
                    ):
                        raise InputError("C04 C03 array/native sample identity differs")
                    vector = arr[f["row"]]
                else:
                    have = cache.lookup(owner, source, plan["representation"], budget)
                    native_key = contracts.row_key(
                        source, row["original_bounds"], plan["representation"]
                    )
                    if native_key not in have:
                        raise InputError("C04 missing original C03 control/native row")
                    vector = cache.vectors(budget, owner, [have[native_key]])[0]
                per, scores = geometry.scores(
                    qfeatures, vector[None], anchor["objective"], variants
                )
                if (
                    not np.allclose(per[:, 0], row["per_example_distances"], rtol=0, atol=2e-15)
                    or abs(float(scores[0]) - row["distance"]) > 2e-15
                ):
                    raise InputError("C04 C03 original/local objective distances differ")
            bounds = [r["original_bounds"] for r in anchor["rows"]]
            chosen = geometry.choose(
                bounds, [r["distance"] for r in anchor["rows"]], anchor["input"]["original_bounds"]
            )
            if (
                anchor["selected"] != anchor["rows"][chosen]
                or anchor["original_retained_alternate"] != anchor["input"]
            ):
                raise InputError("C04 C03 selected/control/tie differs")
        proofs.append(
            dict(group=g["group"], rank=g["rank"], original=ref, anchors=len(g["anchors"]))
        )
    locator = record(view.directory / "report.json")
    path = contained(owner.root / locator["bundle"], view.reports)
    verify_bundle(owner.root, path.parent, view.reports)
    bundle = record(path)
    if bundle["record_hash"] != owner.protocol["playback_bundle"]:
        raise InputError("C04 repaired historical playback differs")
    declaration = record(owner.root / "manifests/refinement/report-repair.json")
    native = record(view.directory / "report-repair-native-qa.json")
    if native["bundle_hash"] != bundle["record_hash"] or not native["passed"]:
        raise InputError("C04 historical native report proof differs")
    return dict(
        schema_version="c04-historical-chain-1",
        c01_snapshot=owner.protocol["snapshot"],
        c02=owner.protocol["execution"],
        c03=owner.protocol["refinement_execution"],
        original_numerical_consumer=value["identity"]["consumer_code"],
        report_consumer=declaration["consumer_code"],
        c04_consumer=plan["consumer"],
        groups=proofs,
        original_c03_groups=value["groups"],
        playback=dict(
            path=(path.parent / "index.html").relative_to(owner.root).as_posix(),
            bundle_hash=bundle["record_hash"],
            items=bundle["items"],
            native_proof="historical C03 native proof; C04 revalidates media hashes only",
            browser_proof="historical C03; not a fresh C04 browser run",
        ),
    )
