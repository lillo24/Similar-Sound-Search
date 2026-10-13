"""Freeze source ancestry before construction and reject split contamination."""

from collections import Counter

from ..storage import InputError, digest, read_json
from .artifacts import record, write_record
from .rendering import FRAMES, MIX_FRAMES, PHRASES, RATE, presets

SEED = 42104
INTERVAL_POLICY = {
    "version": "a05-grid-1",
    "hop_seconds": 0.25,
    "tail": "unique end-aligned",
    "duration": "complete query",
    "controlled": "complete candidate",
}


def comparison_pair(root):
    path = root / "manifests/evaluation/comparison.json"
    if not path.exists():
        return None
    bundle = record(path)
    for name in ("protocol", "suite"):
        value = bundle[name]
        if value.get("record_hash") != digest(
            {k: v for k, v in value.items() if k != "record_hash"}
        ):
            raise InputError("comparison transaction: corrupt paired " + name)
    if bundle["suite"]["protocol_hash"] != bundle["protocol"]["record_hash"]:
        raise InputError("comparison transaction: protocol/suite mismatch")
    return bundle["protocol"], bundle["suite"]


def catalogue_families(root):
    """Conservative union of A03 established duplicate groups and provider artist evidence."""
    base = root / "manifests/catalogue/starter"
    if not (base / "groups.json").exists():
        return [], {}, ["No local A03 catalogue metadata; procedural backgrounds only"]
    groups = record(base / "groups.json")["entry_groups"]
    values = [record(p) for p in sorted((base / "entries").glob("*.json"))]
    values = [v for v in values if v.get("state") == "ready"]
    parents = {v["entry_id"]: v["entry_id"] for v in values}

    def find(key):
        while parents[key] != key:
            key = parents[key]
        return key

    seen = {}
    for v in values:
        key = v["entry_id"]
        artist = v["recording"]["artist"]
        for identity in ("duplicate:" + groups[key], "artist:" + artist.casefold()):
            if identity in seen:
                a, b = sorted((find(key), find(seen[identity])))
                parents[b] = a
            else:
                seen[identity] = key
    families = {key: "catalogue:" + find(key) for key in parents}
    assignments = {f: split_for(f) for f in sorted(set(families.values()))}
    selected = []
    limitations = []
    for split in ("development", "held_out"):
        used = set()
        for v in values:
            family = families[v["entry_id"]]
            if assignments[family] != split or family in used:
                continue
            private = root / "data/runs/catalogue/starter/entries" / (v["entry_id"] + ".json")
            if not private.is_file() or any(
                not (root / v[area]["local_path"]).is_file()
                for area in ("source_asset", "analysis_derivative")
            ):
                limitations.append("Unavailable local background: " + v["entry_id"])
                continue
            selected.append(
                {
                    "entry_id": v["entry_id"],
                    "family": family,
                    "split": split,
                    "record_hash": v["record_hash"],
                    "artist": v["recording"]["artist"],
                    "original_sha256": v["source_asset"]["sha256"],
                    "prepared_record_hash": v["prepared_record_hash"],
                }
            )
            used.add(family)
            if len(used) == 2:
                break
    if not selected:
        limitations.append("No locally available real backgrounds; procedural only")
    return selected, {"entry_families": families, "assignments": assignments}, limitations


def split_for(family):
    return "development" if int(digest([SEED, family])[:8], 16) % 2 == 0 else "held_out"


def freeze(budget, policy):
    path = budget.root / "manifests/evaluation/protocol.json"
    pair = comparison_pair(budget.root)
    if path.exists() or pair:
        value = pair[0] if pair else record(path)
        if value["resource_policy"] != policy:
            raise InputError("A04 frozen resource policy differs; preserve protocol and ledger")
        if value.get("published_source_hash") != digest(
            read_json(budget.root / "config/published_benchmark.json")
        ):
            raise InputError("A04 published source changed after protocol freeze")
        return value
    backgrounds, catalogue, limitations = catalogue_families(budget.root)
    identities = presets(SEED)
    families = {v["family"]: v["split"] for v in identities}
    families.update(catalogue.get("assignments", {}))
    # Grey families group reused instruments/conditions conservatively, even though all
    # their observations remain excluded from model scoring pending rights/mapping.
    human_families = {"grey-orchestral-" + c for c in "BCE FOSTX".replace(" ", "")}
    families.update({f: split_for(f) for f in human_families})
    source = read_json(budget.root / "config/published_benchmark.json")
    human_order = ["Grey1977:" + name.removesuffix(".aiff") for name in source["order"]]
    human_links = {key: "grey-orchestral-" + key.split(":")[1][0] for key in human_order}
    human_pairs = Counter()
    for i, left in enumerate(human_order):
        for right in human_order[i + 1 :]:
            a, b = families[human_links[left]], families[human_links[right]]
            human_pairs[a if a == b else "dropped_cross_split"] += 1
    value = {
        "schema_version": "a04-protocol-1",
        "protocol_version": "2026-10-13.1",
        "comparison_interval_policy": INTERVAL_POLICY,
        "seed": SEED,
        "families": families,
        "presets": identities,
        "catalogue_links": catalogue,
        "backgrounds": backgrounds,
        "limitations": limitations,
        "published_source_hash": digest(source),
        "human_stimulus_ids": human_order,
        "human_family_links": human_links,
        "human_split_pairs_before_rights_exclusion": dict(human_pairs),
        "human_scoring_pairs_after_rights_exclusion": 0,
        "renderer": {
            "engine": "numpy-scipy-procedural-1",
            "rate": RATE,
            "channels": 1,
            "frames": FRAMES,
            "mixture_frames": MIX_FRAMES,
            "phrases": PHRASES,
            "pitches_semitones": [0, 2],
            "performances": [0, 1, 2],
            "tbr_db": [-12, 0, 12],
            "level": "render RMS .08; mixture common peak <=.9",
            "seed_policy": "SEED + 10*performance + pitch; identical across presets",
        },
        "human_datasets": {
            "Grey1977": {
                "revision": "262ca43c2105483eac03c775cd1adba6273a9e6b",
                "eligible": False,
                "mapping": "explicit lexicographic upstream loader order; "
                "original row key unverified",
                "restrictions": "no asset licence established; no model scoring or redistribution",
                "rating_direction": "higher_dissimilarity",
                "mask": "upper triangle excluding diagonal",
            }
        },
        "metrics": {
            "human": "signed Spearman on unique observed within-split pairs; average ties",
            "human_aggregate": None,
            "uncertainty": "descriptive only: tiny dependent families",
            "retrieval": "per-condition query hit and one-to-one target event coverage at K",
            "localisation": "IoU, signed/absolute endpoint errors for matched events; misses",
            "absence": "score/rank distributions only; no fitted rejection rule in A04",
        },
        "k": [1, 5, 10],
        "ranking": "score direction, then asset_id/start_frame/end_frame ascending",
        "matching": {
            "basis": "decoded_available_file",
            "minimum_iou": 0.5,
            "technical_rounding_samples": 1,
            "assignment": "maximum one-to-one event matching; one prediction per target",
            "duplicates": "identical asset/start/end collapsed before K; overlapping hits distinct",
            "short_list": "min(K, unique provided); missing outputs remain misses",
        },
        "preprocessing": "native human originals; A05 model-specific lineage required; no MP3 seek",
        "resource_policy": policy,
        "selection_rule": {
            "partition": "development only; at most three model candidates",
            "eligibility": "technical checks pass, resource limits respected, all expected "
            "query outputs supplied; empty stage lists remain misses",
            "primary": "macro mean candidate query hit rate at K=1 over the three "
            "source_consistency mixture levels",
            "secondary": "macro mean candidate query hit rate at K=5 over controlled "
            "performance and pitch conditions",
            "ties": "lower measured model wall time, then lexical method_id/config_hash",
            "human": "Grey1977 unavailable; report separately. Enabling a human metric "
            "requires a reviewed protocol revision before model comparison",
            "exclusions": "exact waveform/instance diagnostics do not select the winner; "
            "no universal accuracy threshold; no tuning on held-out model scores",
            "failure": "if no technically eligible run exists, report no selection",
        },
        "overlap_limits": "preset-family split, not unseen synthesis-engine split; "
        "catalogue artist/"
        "established duplicate union only; unknown lossy copies and pretraining overlap unknown",
    }
    write_record(path, value, budget)
    return record(path)


def validate_splits(protocol, assets):
    observed = {}
    for value in assets:
        split = value["split"]
        if split not in {"development", "held_out"}:
            raise InputError("evaluation split: invalid partition")
        for family in value["families"]:
            if protocol["families"].get(family) != split:
                raise InputError(
                    f"split leakage {value['asset_id']}: family {family} crosses roles"
                )
            if family in observed and observed[family] != split:
                raise InputError("evaluation source family occurs in both partitions")
            observed[family] = split
    return {
        "assets": dict(Counter(a["split"] for a in assets)),
        "used_families": dict(Counter(observed.values())),
    }
