"""One provider adapter: frozen Internet Archive release metadata and coverage selection."""

import math
import re
from collections import Counter, defaultdict, deque
from urllib.parse import quote, urlencode, urlsplit

from ..storage import InputError, bounded_json, digest, read_json, sha256
from .transfer import fetch, utc_now

LICENSE = re.compile(r"^/licenses/(by|by-sa|by-nc|by-nc-sa)/(1\.0|2\.0|2\.5|3\.0|4\.0)/?$")


def licence(url):
    if not isinstance(url, str):
        return None
    parsed = urlsplit(url)
    if parsed.hostname not in {"creativecommons.org", "www.creativecommons.org"}:
        return None
    match = LICENSE.fullmatch(parsed.path)
    return f"CC {match[1].upper()} {match[2]}" if match else None


def text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def seconds(value):
    try:
        parts = str(value).split(":")
        result = sum(float(x) * 60**i for i, x in enumerate(reversed(parts)))
        return result if math.isfinite(result) and result > 0 else None
    except ValueError:
        return None


def cached_json(url, directory, ledger):
    """Freeze successful payloads by URL; verify cache bytes on every use."""
    key = digest(url)
    path = directory / (key + ".json")
    receipt = directory / (key + ".receipt.json")
    if receipt.exists():
        evidence = read_json(receipt)
        if evidence["url"] != url or sha256(path, ledger.budget) != evidence["sha256"]:
            raise InputError(f"source snapshot cache changed: {key}; preserve and inspect")
        return read_json(path), evidence
    staging = directory / (key + ".partial")
    audit = fetch(url, staging, ledger, 1024 * 1024)
    result = read_json(staging)
    evidence = {
        "url": url,
        "sha256": sha256(staging, ledger.budget),
        "acquired_at": utc_now(),
        "bytes": audit["bytes"],
    }
    staging.replace(path)
    bounded_json(receipt, evidence, ledger.budget)
    return result, evidence


def search(directory, ledger):
    policy = ledger.policy
    query = urlencode(
        {
            "q": policy["query"],
            "fl[]": ["identifier", "licenseurl", "subject", "creator"],
            "sort[]": "identifier asc",
            "rows": policy["search_rows"],
            "page": 1,
            "output": "json",
        },
        doseq=True,
    )
    document, evidence = cached_json(
        "https://archive.org/advancedsearch.php?" + query, directory / "source", ledger
    )
    try:
        response = document["response"]
        docs = response["docs"]
        population = response["numFound"]
        if not isinstance(population, int) or not isinstance(docs, list):
            raise TypeError("invalid population")
        eligible = [
            doc["identifier"]
            for doc in docs
            if re.fullmatch(r"[A-Za-z0-9_.-]+", doc["identifier"])
            and licence(doc.get("licenseurl"))
        ]
    except (KeyError, TypeError) as exc:
        raise InputError(f"Archive search: malformed response ({exc})") from exc
    ordered = sorted(
        set(eligible), key=lambda x: digest({"selection": "a03-ia-1", "identifier": x})
    )
    return {
        "schema_version": "a03-discovery-1",
        "query": policy["query"],
        "snapshot": evidence,
        "search_population": population,
        "returned_items": len(docs),
        "eligible_licence_items": len(ordered),
        "item_ids": ordered[: policy["max_source_items"]],
        "selection_rule": (
            "SHA256 canonical {selection:a03-ia-1,identifier}, ascending; permitted CC subset"
        ),
        "population_truncated": population > len(docs),
    }


def release(item, directory, ledger):
    document, evidence = cached_json(
        "https://archive.org/metadata/" + quote(item, safe=""), directory / "source", ledger
    )
    if document.get("is_dark") or document.get("metadata", {}).get("nodownload"):
        raise InputError(f"Archive item {item}: dark/restricted download")
    metadata = document.get("metadata", {})
    files = document.get("files")
    rights_url = metadata.get("licenseurl")
    if not licence(rights_url) or not isinstance(files, list):
        raise InputError(f"Archive item {item}: no supported audio licence/file metadata")
    by_name = {f["name"]: f for f in files if isinstance(f, dict) and text(f.get("name"))}
    alternatives = defaultdict(list)
    excluded = Counter()
    policy = ledger.policy
    for file in files:
        name = file.get("name", "")
        if not name.lower().endswith(".mp3"):
            continue
        parent = file
        visited = set()
        while parent.get("original") in by_name and parent["original"] not in visited:
            visited.add(parent["original"])
            parent = by_name[parent["original"]]
        # Provider release + explicit track position is evidence stronger than title equality.
        position = text(str(parent["track"])) if parent.get("track") is not None else None
        provider_key = item + "/" + ("track:" + position if position else parent["name"])
        try:
            size = int(file["size"])
        except (KeyError, ValueError, TypeError):
            excluded["missing_file_size"] += 1
            continue
        duration = seconds(file.get("length", parent.get("length")))
        if size <= 0 or size > policy["max_audio_bytes"]:
            excluded["file_byte_limit"] += 1
            continue
        if (
            duration is None
            or not policy["min_duration_seconds"] <= duration <= policy["max_duration_seconds"]
        ):
            excluded["duration_policy"] += 1
            continue
        artist = (
            text(file.get("artist")) or text(parent.get("artist")) or text(metadata.get("creator"))
        )
        title = text(file.get("title")) or text(parent.get("title"))
        if not artist or not title or artist.lower() in {"various", "various artists"}:
            excluded["missing_track_identity"] += 1
            continue
        md5 = file.get("md5")
        if not isinstance(md5, str) or not re.fullmatch(r"[a-f0-9]{32}", md5):
            excluded["missing_provider_checksum"] += 1
            continue
        identifiers = parent.get("external-identifier", [])
        identifiers = identifiers if isinstance(identifiers, list) else [identifiers]
        known_family = next(
            (
                value
                for value in identifiers
                if isinstance(value, str) and value.startswith("urn:mb_recording_id:")
            ),
            None,
        )
        origin = "https://archive.org/download/" + quote(item, safe="") + "/" + quote(name, safe="")
        alternative = {
            "provider": "internet_archive",
            "provider_recording_id": provider_key,
            "source_item_id": item,
            "file_name": name,
            "origin_url": origin,
            "source_page": "https://archive.org/details/" + item,
            "expected_bytes": size,
            "expected_md5": md5,
            "provider_mtime": file.get("mtime"),
            "provider_original": file.get("original"),
            "provider_format": file.get("format"),
            "provider_duration_seconds": duration,
            "title": title,
            "artist": artist,
            "album": text(parent.get("album")) or text(metadata.get("title")),
            "version": "Archive file mtime=" + str(file.get("mtime")) + "; md5=" + md5,
            "genre": text(parent.get("genre")) or text(file.get("genre")) or "unspecified",
            "source_snapshot": evidence,
            "rights": {
                "audio_licence_url": rights_url,
                "audio_licence": licence(rights_url),
                "evidence_url": evidence["url"],
                "evidence_sha256": evidence["sha256"],
                "permitted_use": (
                    "Local noncommercial research; retain attribution and licence; "
                    "no audio publication"
                ),
                "attribution": (
                    f"{artist} — {title}; {metadata.get('title')}; {origin}; {rights_url}"
                ),
                "metadata_licence": (
                    "No blanket metadata licence inferred from audio or provider code licence"
                ),
            },
            "known_family_id": known_family,
            "kind": "full_track",
            "original_recording_offset_seconds": None,
            "offset_evidence": None,
            "time_evidence": (
                "Provider release-track file, not a provider preview. "
                "External master alignment/MP3 priming unverified."
            ),
        }
        alternatives[provider_key].append(alternative)
    candidates = []
    for key in sorted(alternatives):
        # Prefer the actual uploaded original, then smallest byte size, then exact filename.
        options = sorted(
            alternatives[key],
            key=lambda f: (bool(f["provider_original"]), f["expected_bytes"], f["file_name"]),
        )
        chosen = options[0]
        chosen["available_aliases"] = [
            {
                k: option[k]
                for k in ("origin_url", "expected_md5", "expected_bytes", "provider_original")
            }
            for option in options[1:]
        ]
        candidates.append(chosen)
    return {
        "item_id": item,
        "snapshot": evidence,
        "candidates": candidates,
        "exclusions": dict(excluded),
    }


def select(releases, policy):
    """Round-robin provider genre/artist, stable hash ordering; no audio similarity scores."""
    candidates = {}
    for release_record in releases:
        for candidate in release_record["candidates"]:
            key = candidate["provider_recording_id"]
            if key not in candidates:
                # Explicit provider title qualifiers are source declarations, not a
                # duration/filename guess. Preserve their unknown master offset.
                if re.search(r"\((?:snippet|preview|excerpt)\)", candidate["title"], re.I):
                    candidate = {
                        **candidate,
                        "kind": "excerpt",
                        "original_recording_offset_seconds": None,
                        "offset_evidence": None,
                        "time_evidence": (
                            "Provider track title explicitly labels a snippet/preview/excerpt; "
                            "original-master start/alignment is unknown."
                        ),
                    }
                candidates[key] = candidate
    buckets = defaultdict(lambda: defaultdict(list))
    for entry in candidates.values():
        buckets[entry["genre"].casefold()][entry["artist"].casefold()].append(entry)
    queues = {}
    for genre, artists in sorted(buckets.items()):
        queues[genre] = deque(
            (artist, deque(sorted(tracks, key=lambda e: digest(e["provider_recording_id"]))))
            for artist, tracks in sorted(artists.items())
        )
    selected = []
    per_artist = Counter()
    while any(queues.values()) and len(selected) < policy["max_requested_recordings"]:
        for genre in queues:
            if len(selected) >= policy["max_requested_recordings"]:
                break
            queue = queues[genre]
            if not queue:
                continue
            while queue and per_artist[queue[0][0]] >= policy["max_tracks_per_artist"]:
                queue.popleft()
            if not queue:
                continue
            artist, tracks = queue.popleft()
            selected.append(tracks.popleft())
            per_artist[artist] += 1
            if tracks:
                queue.append((artist, tracks))
    return {
        "schema_version": "a03-selection-1",
        "rule": (
            "Round-robin casefolded provider genre/artist; "
            "track order SHA256(provider recording ID); artist cap"
        ),
        "seed": "a03-ia-1 (hash ordering, no RNG)",
        "requested_count": policy["max_requested_recordings"],
        "eligible_recordings": len(candidates),
        "eligible_artists": len({e["artist"].casefold() for e in candidates.values()}),
        "selected_count": len(selected),
        "selected_ids": [e["provider_recording_id"] for e in selected],
        "selection_sha256": digest(selected),
        "entries": selected,
    }
