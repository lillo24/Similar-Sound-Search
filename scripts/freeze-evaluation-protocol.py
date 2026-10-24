"""One-shot prospective D02 case matrix; no audio generation or model inference."""

import json
import subprocess
from pathlib import Path

from similar_sound_search.storage import atomic_json, digest

root = Path.cwd()
target = root / "manifests/assessment/protocol.json"
if target.exists():
    raise RuntimeError("D02 protocol already exists; preserve its prospective identity")

mechanisms = ["harmonic", "pluck", "fm", "noise"]
splits = {}
for split, base, count in (("development", 1240000, 24), ("confirmation", 9240000, 16)):
    families = [
        dict(
            mechanism=m,
            spectral_slope=1.17 + i * 0.08 + (0.43 if split == "confirmation" else 0),
            fm_ratio=1.57 + i * 0.11 + (0.19 if split == "confirmation" else 0),
            cutoff_hz=1050 + i * 540 + (370 if split == "confirmation" else 0),
        )
        for i, m in enumerate(mechanisms)
    ]
    sources = []
    for i in range(32):
        family, condition = (i // 6, i % 6) if i < 24 else ((i - 24) % 4, 6)
        sources.append(
            dict(
                source_id=digest(["d02-source-1", split, i]),
                ordinal=i,
                group=digest(["d02-group-1", split, 24 if i == 31 else i]),
                family=family,
                character="positive" if i < 24 else "hard-negative",
                performance_seed=base + 1000 + i * 37,
                background_seed=base + 20000 + i * 41,
                pitch=[-5, 0, 7, -2, 4, 0, 0][condition],
                phrase=(i + 1) % 3,
                condition=condition,
                positions=[0.17, 4.93]
                if condition == 2
                else [0.0, 5.6]
                if condition == 3
                else [1.013]
                if condition == 4
                else [0.311]
                if condition == 5
                else [0.373],
                ratio_db=[9, 6, -6, 0, 3, 6, 6][condition],
                duration_seconds=1.7 if condition == 5 else 8.0,
                event_seconds=1.1 if condition == 5 else 2.4,
                rate=44100 if condition == 4 else 24000,
                channels=2 if condition == 4 else 1,
                duplicate_of=24 if i == 31 else None,
            )
        )
    sources[31]["family"] = sources[24]["family"]
    cases = []
    single_conditions = 4 if split == "development" else 2
    for i in range(count):
        singles = 4 * single_conditions
        if i < singles:
            family, condition = divmod(i, single_conditions)
            fs, kind = [family], "independent-performance"
        elif i < singles + 4:
            family = i - singles
            fs = [family, family if family < 2 else (family + 1) % 4]
            kind = "same-character-alternatives" if family < 2 else "distinct-known-events"
            condition = 4
        elif i < singles + 6:
            fs, condition, kind = [i - singles - 4], 5, "absent-target"
        else:
            fs, condition, kind = [0], 6, "exact-instance-exclusion"
        examples = []
        for j, family in enumerate(fs):
            short = split == "development" and condition == 3
            examples.append(
                dict(
                    family=family,
                    performance_seed=base + 100000 + i * 211 + j * 53,
                    background_seed=base + 300000 + i * 223 + j * 59,
                    pitch=([0, 6, -4, 2][condition] if condition < 4 else j * 7)
                    + (3 if split == "confirmation" else 0),
                    phrase=i % 3,
                    event_seconds=1.1 if short else 2.4,
                    ratio_db=-3 if condition == 2 else 0 if split == "confirmation" else 18,
                    native_rate=24000,
                    duration_seconds=3.2,
                    event=[9600, 36000 if short else 67200],
                    context=[0, 76800],
                    source_ordinal=(0 if i == count - 2 else 31)
                    if kind == "exact-instance-exclusion"
                    else None,
                )
            )
        cases.append(
            dict(
                case_id=digest(["d02-case-1", split, i]),
                ordinal=i,
                kind=kind,
                condition=condition,
                examples=examples,
                positive_characters=sorted(set(fs)) if condition < 5 else [],
                primary=condition < 5,
                scoring_unit="complete constructed motif; short-source motif has full 1.1s release",
            )
        )
    splits[split] = dict(families=families, sources=sources, cases=cases)

value = dict(
    schema_version="d02-protocol-1",
    owner="D02",
    base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    roots=[
        "data/runs/assessment",
        "data/features/assessment",
        "data/audio/assessment",
        "reports/local/d02",
        "manifests/assessment",
    ],
    pool="data/runs/assessment/pool.json",
    shared_preparation="Only new content-addressed A02 prepared files; preserve existing files",
    splits=splits,
    input_isolation="Neutral source/case IDs; family/insertion/positive truth stays "
    "outside retrieval inputs",
    construction=dict(
        primitive="evaluation.rendering.render_tone and mix; familiar procedural mechanisms",
        performance="Independent seeds, detuning +/-0.13 semitone, spectral slope +/-0.04, "
        "FM ratio +/-0.02 and cutoff +/-35Hz; multiplicative independent slow amplitude modulation",
        negative="Same mechanism, slope+1.3, FM ratio+.67, cutoff+2200Hz; "
        "proxy identity, not human irrelevance",
        absent="Query slope+2.4, FM ratio+1.7, cutoff+6000Hz; no matching preset in candidates",
        background="Independent 3rd-order 1800Hz low-pass noise RMS .04 plus "
        ".01*sin(127Hz) and .008*sin(331Hz); no shared query realization",
        stereo="Left mono mixture, right .7 mixture plus .01 independent noise; "
        "resample_poly 24k to44.1k",
        exact_controls="Declared candidate original is the query parent; "
        "its duplicate group must be excluded",
        audit="Independent algebraic mixture/level reconstruction, full PCM/hash, "
        "lag/native endpoint and silence/clipping checks",
    ),
    policies=["legacy-mean", "event-multi"],
    default=dict(audio="original", arm="legacy-mean", pitch="off"),
    revision=dict(
        allowed=False, reason="Compare shipped event-multi unchanged; no tuning dimension"
    ),
    limits=dict(
        queries=40,
        development=24,
        confirmation=16,
        sources=64,
        executions=112,
        technical_replay_executions=8,
    ),
    banks=[
        dict(window_milliseconds=2400, hop_milliseconds=600),
        dict(window_milliseconds=4800, hop_milliseconds=1000),
    ],
    metrics=dict(
        cuts=[1, 5, 10, 20],
        iou=0.5,
        truth_overlap=0.5,
        matching="one-to-one maximum cardinality then IoU; actual scored representatives only",
        primary="Macro by declared mechanism family and condition; paired cases retained",
        absent="Forced ranking validity and score/order only; no rejection threshold",
    ),
    controls=dict(
        constant="eligible group ID ascending",
        random_seed=882711,
        random="independent seeded permutation per case, same eligible population",
    ),
    decision="Complete valid compliant outputs; no macro group-hit@1 or IoU event-recall@10 loss; "
    "strict gain in at least one; no newly lost per-case positive-group coverage@20. "
    "Apply to development and confirmation separately; preserve condition regressions.",
    product_cases=dict(
        split="development",
        ordinals=[0, 16, 20],
        scope="Real import/save/submit/status/result and frozen model; both arms; "
        "included in initial development executions",
    ),
    playable_rule="Three product cases, plus first development primary baseline IoU miss "
    "at ten: first highest-ranked retained native representative for a known-positive group; "
    "if no known-positive group is ranked, first actual result. No quality-based replacement.",
    stage_metadata_mib=dict(prepare=24, development=72, confirmation=56, delivery=28, report=12),
    protected_metadata_mib=32,
    qa_managed_mib=64,
    evidence_limits="Prospective confirmation within familiar mechanisms; no human agreement, "
    "new A06 holdout, Loulou layer truth or unseen musical-source claim",
)
atomic_json(target, {**value, "record_hash": digest(value)})
policy = dict(
    job_seconds=3600,
    workers=256,
    read_audio_seconds=90000,
    feature_windows=4096,
    processed_window_seconds=20000,
    feature_bytes=32 * 1024**2,
    query_jobs=128,
    clips=64,
    clip_bytes=128 * 1024**2,
    metadata_bytes=256 * 1024**2,
    preparation_bytes=64 * 1024**2,
    import_bytes=128 * 1024**2,
    managed_output_bytes=1024**3,
)
config = dict(
    schema_version="d02-assessment-1",
    host="127.0.0.1",
    port=8775,
    protected_metadata_bytes=32 * 1024**2,
    attempt_bookkeeping_bytes=262144,
    acceptance_ordinary_bytes=112 * 1024**2,
    policy={"max_" + k: v for k, v in policy.items()},
    import_counter="Generated audio and explicit evaluation uploads share import_bytes",
)
atomic_json(root / "config/assessment.json", config)
print(json.dumps(dict(protocol=digest(value), queries=40, generated_sources=64)))
