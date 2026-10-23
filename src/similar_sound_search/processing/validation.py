"""Independent scalar/native answers, generated original fixtures and explicit registration."""

import math

import numpy as np
import soundfile as sf

from ..inputs import decode, probe
from ..search.contracts import grid
from ..search.ranking import distances
from ..storage import InputError, contained, digest


def known_answer():
    q = np.asarray([[1, 2, 3], [3, 1, -1]], dtype=np.float32)
    c = np.asarray([[2, 1, 0], [1, -2, 1]], dtype=np.float32)
    scalar = [
        [
            1
            - sum(float(a) * float(b) for a, b in zip(x, y, strict=True))
            / math.sqrt(sum(float(a) ** 2 for a in x) * sum(float(b) ** 2 for b in y))
            for y in c
        ]
        for x in q
    ]
    per, _ = distances(q, c, "cosine")
    if not np.allclose(per, scalar, rtol=0, atol=2e-15):
        raise InputError("C04 independent scalar cosine oracle failed")
    actual = grid(145, 11, dict(window_milliseconds=2400, hop_milliseconds=1200))
    expected = [(x, x + 27) for x in (0, 13, 26, 39, 52, 65, 78, 91, 104, 117, 118)]
    if actual != expected:
        raise InputError("C04 independent native ceil/hop/end oracle failed")
    return dict(status="ok", passed=True, scalar_pairs=4, native_intervals=len(expected))


def register_sources(budget, owner, value):
    if (
        value.get("schema_version") != "c04-local-import-1"
        or not 1 <= len(value.get("files", [])) <= 8
    ):
        raise InputError("C04 import: explicit 1..8 local sources required")
    result = []
    for item in value["files"]:
        if set(item) != {"path", "id", "group", "title", "rights"} or not item["rights"]:
            raise InputError("C04 import: path/id/group/title/rights evidence required")
        path = contained(owner.root / item["path"], owner.root / "data/audio")
        info = probe(path, budget)
        owner.charge(budget, read_audio_seconds=info.frames / info.samplerate)
        _, meta = decode(path, budget)
        source = dict(
            recording_id=item["id"],
            record_hash=digest(item),
            kind="engineering",
            group=item["group"],
            source={**meta, "local_path": path.relative_to(owner.root).as_posix()},
            title=item["title"],
            artist="Explicit local import",
            rights=item["rights"],
            data_role="processing-local-outside-frozen-discovery",
            provider="local",
            provider_recording_id=None,
            known_family_id=None,
            source_url=None,
            source_page=None,
            basis="file",
            offset=None,
            offset_evidence="available file; master alignment unverified",
        )
        ref = owner.put(
            budget, "source-revisions", dict(schema_version="c04-source-revision-1", source=source)
        )
        result.append(dict(source=source, revision=ref))
    return dict(status="ok", sources=result)


def fixtures(budget, owner):
    rate, frames = 24000, 144000
    t = np.arange(frames, dtype=np.float64) / rate
    specs = []
    for label, hz in (("a", 220), ("b", 440), ("b2", 493), ("c", 880), ("q1", 330), ("q2", 550)):
        path = owner.audio / "fixtures" / (label + ".wav")
        if path.exists():
            raise InputError(
                "C04 declared fixtures already exist; use their immutable registrations"
            )
        owner.charge(budget, preparation_bytes=frames * 4 + 4096)
        budget.reserve(frames * 4 + 65536, frames * 32)
        path.parent.mkdir(parents=True, exist_ok=True)
        samples = (
            0.2 * np.sin(2 * np.pi * hz * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t) ** 2)
            + 0.03 * np.sin(2 * np.pi * (hz * 1.51) * t)
        ).astype(np.float32)
        sf.write(path, samples, rate, subtype="FLOAT")
        specs.append(
            dict(
                path=path.relative_to(owner.root).as_posix(),
                id="c04-" + label,
                group="c04-" + label,
                title="C04 generated " + label,
                rights="Project-generated C04 engineering WAV; no discovery or human labels",
            )
        )
    value = register_sources(budget, owner, dict(schema_version="c04-local-import-1", files=specs))
    ref = owner.put(
        budget, "fixtures", dict(schema_version="c04-fixtures-1", sources=value["sources"])
    )
    return dict(status="ok", fixtures=ref, sources=len(specs), outside_discovery=True)


def clean_check(budget, owner, job_path):
    """Independently encode native rows, scalar-score and compare complete group outputs."""
    from ..matchers.acoustic import checked
    from ..search import sources
    from ..search.contracts import save_array
    from . import api, cache, contracts, engine, job

    job_ref = api.reference(owner, __import__("pathlib").Path(job_path), "jobs")
    state = api.status(owner.root, job_ref)
    if state["state"] != "complete":
        raise InputError("C04 clean check requires a complete explicit fixture job")
    manifest = owner.get(job_ref, "jobs")
    plan = api.load_plan(owner, manifest["plan"])
    spec = plan["input"]
    if spec["historical"] or len(spec["sources"]) > 3 or spec["query"]["kind"] != "native":
        raise InputError("C04 clean comparison is limited to declared small native fixtures")
    owner.charge(budget, query_jobs=1)
    desc = plan["representation"]
    arrays = {}
    new = 0
    for source in [*spec["sources"], spec["query"]["source"]]:
        rid = source["recording_id"]
        if rid in arrays:
            continue
        bounds = (
            contracts.native_rows(source, spec["banks"])
            if source in spec["sources"]
            else sorted(set(map(tuple, spec["query"]["bounds"])))
        )
        if rid == spec["query"]["source"]["recording_id"]:
            bounds = sorted(set(bounds) | set(map(tuple, spec["query"]["bounds"])))
        samples = sources.load(budget, source, context=owner)
        owner.charge(
            budget,
            feature_windows=len(bounds),
            processed_window_seconds=sum(b - a for a, b in bounds)
            / source["source"]["sample_rate_hz"],
            feature_bytes=len(bounds) * desc["dimension"] * 4 + 65536,
        )
        model = owner.model(budget, desc)
        matrix = np.stack(
            [
                checked(
                    model.encode(samples[a:b], source["source"]["sample_rate_hz"]),
                    desc["dimension"],
                )
                for a, b in bounds
            ]
        )
        identity = dict(
            version="c04-independent-clean-1",
            job=job_ref,
            dimension=desc["dimension"],
            source=contracts.source_key(source),
            bounds=[list(b) for b in bounds],
        )
        receipt = save_array(owner.features / "clean", identity, matrix, budget)
        arrays[rid] = dict(bounds=bounds, matrix=matrix, receipt=receipt)
        new += len(bounds)
        have = cache.lookup(owner, source, desc, budget)
        for i, b in enumerate(bounds):
            key = contracts.row_key(source, b, desc)
            if key not in have or have[key]["vector_sha256"] != cache.vector_hash(matrix[i]):
                raise InputError("C04 clean rebuild native membership/feature bytes differ: " + key)
    _, progress = job.progress(owner, job_ref)
    query_value = job.collect(owner, progress, plan, "query")["query"]
    current = job.collect(owner, progress, plan, "score")
    qr = arrays[spec["query"]["source"]["recording_id"]]
    query_matrix = np.stack(
        [
            qr["matrix"][qr["bounds"].index(b)]
            for b in sorted(set(map(tuple, spec["query"]["bounds"])))
        ]
    )
    max_error = 0.0
    scalar_pairs = 0
    independent = {}
    for source in spec["sources"]:
        rid = source["recording_id"]
        a = arrays[rid]
        per = np.asarray(
            [
                [
                    1
                    - sum(float(x) * float(y) for x, y in zip(q, c, strict=True))
                    / math.sqrt(sum(float(x) ** 2 for x in q) * sum(float(y) ** 2 for y in c))
                    for c in a["matrix"]
                ]
                for q in query_matrix
            ]
        )
        scalar_pairs += per.size
        means = np.mean(per, axis=0)
        raw = engine.load_scores(owner, current[rid])
        rebuilt = []
        for index, b in enumerate(spec["banks"]):
            native = grid(
                source["source"]["sample_count"], source["source"]["sample_rate_hz"], b["grid"]
            )
            ids = [a["bounds"].index(tuple(v)) for v in native]

            def row(i):
                bounds = list(a["bounds"][i])
                return dict(
                    key=contracts.row_key(source, bounds, desc),
                    bounds=bounds,
                    per=per[:, i].tolist(),
                    mean=float(means[i]),
                )

            best = min(ids, key=lambda i: (float(means[i]), *a["bounds"][i]))
            supports = []
            for k in range(len(query_matrix)):
                order = sorted(ids, key=lambda i: (float(per[k, i]), *a["bounds"][i]))
                supports.append([row(i) for i in order[:16]])
            rebuilt.append(dict(count=len(ids), baseline=row(best), supports=supports))
            for old, fresh in zip(
                [
                    raw["banks"][index]["baseline"],
                    *[r for rs in raw["banks"][index]["supports"] for r in rs],
                ],
                [row(best), *[r for rs in supports for r in rs]],
                strict=True,
            ):
                if old["key"] != fresh["key"] or old["bounds"] != fresh["bounds"]:
                    raise InputError("C04 scalar clean support/tie/native selection differs")
                error = max(abs(x - y) for x, y in zip(old["per"], fresh["per"], strict=True))
                max_error = max(max_error, error)
                if error > 2e-15:
                    raise InputError("C04 scalar clean distances differ")
        independent[rid] = {**raw, "banks": rebuilt}
    features = job.collect(owner, progress, plan, "features")
    clean_result = engine.aggregate(budget, owner, plan, features, query_value, independent)
    incremental = api.result(owner.root, state["result"])
    for arm, values in clean_result["arms"].items():
        original = incremental["arms"][arm]
        left = [owner.get(r, "group-results") for r in values["complete_groups"]]
        right = [owner.get(r, "group-results") for r in original["complete_groups"]]
        if [v["group"] for v in left] != [v["group"] for v in right]:
            raise InputError("C04 clean complete-group ranking differs")

        # Native supports, exclusions, shortlist/display membership and credit ranks
        # are exact; scalar distances have only the documented float64 tolerance.
        def equivalent(a, b):
            if isinstance(a, dict) and isinstance(b, dict):
                keys = set(a) - {"record_hash"}
                return keys == set(b) - {"record_hash"} and all(
                    equivalent(a[k], b[k]) for k in keys
                )
            if isinstance(a, list) and isinstance(b, list):
                return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b, strict=True))
            if isinstance(a, float) and isinstance(b, float):
                return abs(a - b) <= 2e-15
            return a == b

        if not equivalent(left, right):
            raise InputError("C04 clean complete group summaries/native maps differ")
        if values["eligible_groups"] != original["eligible_groups"]:
            raise InputError("C04 clean eligibility differs")
    if clean_result["excluded_groups"] != incremental["excluded_groups"]:
        raise InputError("C04 clean exclusions differ")
    evidence = dict(
        schema_version="c04-clean-comparison-1",
        job=job_ref,
        result=state["result"],
        new_clean_encodes=new,
        exact_feature_bytes=True,
        exact_native_membership=True,
        scalar_pairs=scalar_pairs,
        max_scalar_error=max_error,
        complete_groups=True,
        shortlist_and_display=True,
        exclusions=True,
        passed=True,
    )
    ref = owner.put(budget, "clean-comparisons", evidence)
    return dict(status="ok", state="complete", comparison=ref, **evidence)
