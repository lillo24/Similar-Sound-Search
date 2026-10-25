"""Freeze D03's actual ordered publication into an independently versioned review."""

import re
import wave

from .common import ReviewError, seal, sha, verified

JOB = "06a4ee15a6956b3b55c8bf9a018b65ecc32f3bb81f4d902d14ee1b7a6a19dd1e"
RESULT = "2319b2130074a3d6a0eee93b3e1debfdb01637f22803c3dc8b2fd42851bb7374"
REFERENCE_SHA = "2fc1256b1ac35134cfaef177aaf032277a0e375c676e50d391a1e3b22046ae30"
REFERENCE_WAV = "390f8584e5cf2713bdd38b588571627eb8f6bd5d8aea0495662645bb666094ad"
DEFAULTS = dict(audio="original", arm="legacy-mean", pitch="off")


def require(condition, message):
    if not condition:
        raise ReviewError(message)


def interval(bounds, rate):
    def stamp(frame):
        ms = round(frame * 1000 / rate)
        return f"{ms // 60000:02}:{ms // 1000 % 60:02}.{ms % 1000:03}"

    return "–".join(stamp(f) for f in bounds)


def audio_header(path, media):
    require(path.stat().st_size == media["bytes"], "Saved clip size differs")
    require(sha(path) == media["sha256"], "Saved clip bytes differ")
    with wave.open(str(path), "rb") as stream:
        actual = dict(
            sample_rate_hz=stream.getframerate(),
            channels=stream.getnchannels(),
            frames=stream.getnframes(),
            sample_width=stream.getsampwidth(),
        )
        require(stream.getcomptype() == "NONE", "Expected original PCM WAV")
    require(actual == {k: media[k] for k in actual}, "Saved WAV native header differs")
    return actual


def media_descriptor(path, saved, bounds, recording, rate):
    require(saved["bounds"] == bounds, "Scored/context native frames differ")
    require(saved["original"]["recording_id"] == recording, "Media recording differs")
    require(saved["native_samples_verified"] is True, "D03 native proof missing")
    clip = saved["clip"]
    require(
        clip["source_start_frame"] == bounds[0]
        and clip["source_end_frame"] == bounds[1]
        and clip["rate"] == rate
        and clip["frames"] == bounds[1] - bounds[0],
        "Clip/native representative differs",
    )
    require(
        saved["sha256"] == clip["sha256"] and clip["samples_verified"] is True,
        "Retained native clip proof differs",
    )
    value = dict(
        media_id=saved["record_hash"],
        sha256=saved["sha256"],
        bytes=saved["bytes"],
        frames=clip["frames"],
        sample_rate_hz=rate,
        channels=clip["channels"],
        sample_width=2,
        gain=clip["gain"],
        source_frames=bounds,
        native_proof="retained D03 independent audit",
    )
    audio_header(path, value)
    return value


def freeze(handoff, result, query, resolve_media, reference, package):
    """resolve_media uses installed api.result_media: result ID, never job ID."""
    require(result["job_id"] == JOB and result["record_hash"] == RESULT, "Wrong D03 publication")
    require(result["state"] == "complete", "Review needs the completed saved publication")
    require(result["selected_arm"] == result["policy"] == "legacy-mean", "Wrong review arm")
    require(result["defaults"] == DEFAULTS, "Original/legacy/pitch-off defaults differ")
    require(result["query_hash"] == query["query"]["record_hash"], "Query binding differs")
    require(
        result["selection"]["revision"] == handoff["query"]["revision"]
        and result["selection"]["materialization"] == handoff["query"]["materialization"],
        "Saved reference revision/materialization differs",
    )
    require(len(result["cards"]) == len(handoff["cards"]) == 10, "Expected ten original cards")
    require(result["population_count"] == result["complete_groups"] == 72, "Population differs")
    cards = []
    copies = {}
    for rank, (card, old) in enumerate(zip(result["cards"], handoff["cards"], strict=True), 1):
        for key in ("rank", "group", "title", "artist", "score"):
            require(card[key] == old[key], "D03 handoff card differs: " + key)
        require(card["rank"] == rank, "Saved rank/order differs")
        require(
            card["query_hash"] == result["query_hash"]
            and card["arm"] == result["selected_arm"]
            and card["population"] == result["snapshot"]["record_hash"]
            and card["group_ref"] == result["arms"]["legacy-mean"]["display"][rank - 1],
            "Card query/arm/population/order binding differs",
        )
        p = card["passages"][0]
        row = p["row"]
        require(p["additional"] is False, "Alternative passage substituted")
        require(row["recording_id"] == old["recording_id"], "Recording identity differs")
        require(row["group"] == card["group"], "Group/representative differs")
        require(row["rate"] == old["sample_rate_hz"], "Native rate differs")
        require(
            row["original_bounds"] == p["scored_bounds"]
            and row["original_context"] == p["context_bounds"],
            "Representative frames differ",
        )
        media = {}
        for role in ("scored", "context"):
            bounds = p[role + "_bounds"]
            require(bounds == old[role + "_frames"], "Native handoff frames differ")
            mid = p[role]["record_hash"]
            require(old[role + "_url"] == f"/result-media/{RESULT}/{mid}", "Foreign media binding")
            path, saved = resolve_media(RESULT, mid)
            media[role] = media_descriptor(path, saved, bounds, row["recording_id"], row["rate"])
            copies[media[role]["sha256"]] = path
        cards.append(
            dict(
                review_id=f"D04-{rank:02}",
                rank=rank,
                title=card["title"],
                artist=card["artist"],
                group=card["group"],
                recording_id=row["recording_id"],
                score=card["score"],
                group_result_hash=card["group_ref"]["record_hash"],
                native_representative=row,
                scored_interval=interval(p["scored_bounds"], row["rate"]),
                context_interval=interval(p["context_bounds"], row["rate"]),
                media=media,
            )
        )
    require(
        len({c["group"] for c in cards}) == len({c["recording_id"] for c in cards}) == 10,
        "Candidate groups/recordings are not distinct",
    )
    examples = query["query"]["identity"]["consumer"]["examples"]
    require(
        len(examples) == 1
        and examples[0]["event"] == [9613800, 10584000]
        and examples[0]["context"] == [9569700, 10628100],
        "Reference selection differs",
    )
    require(
        query["query"]["examples"][0]["prepared"]["technical_metadata"]["sha256"] == REFERENCE_SHA,
        "Query's supplied MP3 identity differs",
    )
    population = [
        dict(
            recording_id=s["recording_id"],
            group=s["group"],
            source_sha256=s["source"]["sha256"],
            canonical_pcm=s["source"]["canonical_pcm"],
        )
        for s in result["population"]
    ]
    value = seal(
        dict(
            schema_version="d04-review-1",
            review_version="d04-v1",
            package=package,
            job_id=JOB,
            result_id=RESULT,
            query_hash=result["query_hash"],
            query_record_hash=query["record_hash"],
            query_feature_hash=result["saved_query_feature_hash"],
            revision=handoff["query"]["revision"],
            materialization=handoff["query"]["materialization"],
            population_hash=result["snapshot"]["record_hash"],
            population=population,
            selected_arm="legacy-mean",
            defaults=DEFAULTS,
            producing_consumer=result["consumer"],
            reference=reference,
            cards=cards,
            uncertainties=[
                "recording identity",
                "marked version/master alignment",
                "intended layer",
                "rights",
                "human relevance",
            ],
        )
    )
    validate(value)
    return value, copies


def validate(value):
    verified(value)
    require(value["schema_version"] == "d04-review-1", "Unsupported review schema")
    require(
        value["defaults"] == DEFAULTS and value["selected_arm"] == "legacy-mean",
        "Review policy differs",
    )
    require(value["job_id"] == JOB and value["result_id"] == RESULT, "Foreign review publication")
    cards = value["cards"]
    require(len(cards) == 10, "Ten saved candidates required")
    require(
        [c["review_id"] for c in cards] == [f"D04-{i:02}" for i in range(1, 11)],
        "Review item order/IDs differ",
    )
    require([c["rank"] for c in cards] == list(range(1, 11)), "Review ranks differ")
    require(
        len({c["group"] for c in cards}) == len({c["recording_id"] for c in cards}) == 10,
        "Duplicate group/recording",
    )
    for item in media_items(value).values():
        require(re.fullmatch("[a-f0-9]{64}", item["sha256"]) is not None, "Bad media checksum")
        require(0 < item["bytes"] <= 16 * 1024 * 1024, "Clip exceeds finite media bound")
        require(
            item["source_frames"][1] - item["source_frames"][0] == item["frames"],
            "Clip frames differ",
        )
        require(
            all(type(f) is int for f in item["source_frames"])
            and 0 <= item["source_frames"][0] < item["source_frames"][1],
            "Bad native frames",
        )
        require(
            type(item["sample_rate_hz"]) is int
            and item["sample_rate_hz"] > 0
            and 0 < item["frames"] / item["sample_rate_hz"] <= 30,
            "Invalid clip duration",
        )
    for card in cards:
        row = card["native_representative"]
        require(
            row["group"] == card["group"] and row["recording_id"] == card["recording_id"],
            "Group/recording representative differs",
        )
        for role, bounds in (("scored", "original_bounds"), ("context", "original_context")):
            require(card["media"][role]["source_frames"] == row[bounds], "Native row/media differs")
            require(
                card[role + "_interval"] == interval(row[bounds], row["rate"]),
                "Displayed/native timestamps differ",
            )
    require(value["reference"]["media"]["sha256"] == REFERENCE_WAV, "Wrong original reference")
    return value


def media_items(value):
    result = {"reference": value["reference"]["media"]}
    for card in value["cards"]:
        for role in ("scored", "context"):
            result[card["review_id"] + "-" + role] = card["media"][role]
    return result
