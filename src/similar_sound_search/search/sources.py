"""Read-only original source validation and catalogue/engineering identity routing."""

from ..catalogue.ingestion import validate_local_original
from ..evaluation.artifacts import record
from ..inputs import decode, probe
from ..records import candidate
from ..storage import InputError, contained, read_json
from .job import read_charge


def catalogue(root):
    base = root / "manifests/catalogue/starter"
    values = [record(p) for p in sorted((base / "entries").glob("*.json"))]
    values = [
        v for v in values if v["state"] == "ready" and v["data_role"] == "real_recording_discovery"
    ]
    if not values:
        raise InputError(
            "search catalogue: no public ready recordings; restore actual local inputs"
        )
    groups = record(base / "groups.json")
    return values, groups


def public_source(value, group):
    asset = value["source_asset"]
    mapping = value["timestamp_mapping"]
    return {
        "recording_id": value["entry_id"],
        "record_hash": value["record_hash"],
        "kind": "catalogue",
        "group": group,
        "data_role": value["data_role"],
        "source": asset,
        "title": value["recording"]["title"],
        "artist": value["recording"]["artist"],
        "provider": value["provider"],
        "provider_recording_id": value["recording"]["provider_recording_id"],
        "known_family_id": value["recording"]["known_family_id"],
        "source_url": value["acquisition"]["origin_url"],
        "source_page": value["acquisition"]["source_page"],
        "rights": value["acquisition"]["rights"],
        "basis": mapping["basis"],
        "offset": mapping["original_recording_offset_seconds"],
        "offset_evidence": mapping["offset_evidence"],
    }


def load(budget, source):
    """Each bounded unit decodes one original, including reuse/clip validation."""
    read_charge(budget, source["source"])
    if source["kind"] == "catalogue":
        value = record(
            budget.root / "manifests/catalogue/starter/entries" / (source["recording_id"] + ".json")
        )
        if value["record_hash"] != source["record_hash"]:
            raise InputError("search original: public record changed; rebuild an explicit index")
        samples, meta, _ = validate_local_original(value, budget)
    else:
        path = contained(budget.root / source["source"]["local_path"], budget.root / "data/audio")
        samples, meta = decode(path, budget)
    for key in ("sha256", "canonical_pcm", "sample_count", "sample_rate_hz", "channels"):
        if meta[key] != source["source"][key]:
            raise InputError("search original: source " + key + " differs")
    return samples


def engineering(budget, spec):
    """Explicit generated diagnostic inputs never enter the discovery catalogue."""
    value = read_json(spec)
    if value.get("schema_version") != "a06-engineering-1" or not 1 <= len(value["sources"]) <= 4:
        raise InputError("engineering index: requires 1..4 explicit generated sources")
    result = []
    for item in value["sources"]:
        path = contained(budget.root / item["path"], budget.root / "data/audio/engineering")
        info = probe(path, budget)
        read_charge(budget, {"duration_seconds": info.frames / info.samplerate})
        _, meta = decode(path, budget)
        context = read_json(contained(budget.root / item["context"], budget.root))
        rec = candidate(path, meta, context, budget.root)
        if rec["source"]["provenance"]["permitted_use"] != "Generated A06 engineering fixture":
            raise InputError("engineering source: explicit generated fixture permission required")
        result.append(
            {
                "recording_id": rec["record_id"],
                "record_hash": rec["record_id"][6:],
                "kind": "engineering",
                "group": rec["record_id"],
                "data_role": "engineering",
                "source": {**meta, **rec["source"]},
                "title": "Known-target engineering fixture",
                "artist": "Generated diagnostic",
                "source_url": None,
                "source_page": None,
                "basis": rec["timestamp_mapping"]["basis"],
                "offset": rec["timestamp_mapping"]["original_recording_offset_seconds"],
                "offset_evidence": rec["timestamp_mapping"]["offset_evidence"],
                "rights": rec["source"]["provenance"],
                "provider": "local",
                "provider_recording_id": None,
                "known_family_id": None,
            }
        )
    return result
