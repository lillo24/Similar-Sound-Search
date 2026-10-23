"""Native waveform previews and PCM16 clips, keyed by media semantics, never UI paint."""

import hashlib

import numpy as np

from ..evaluation.artifacts import record
from ..inputs import decode
from ..queries import assets
from ..search import sources
from ..search.report import clip, pcm16
from ..storage import InputError, contained, digest
from .queries import QueryOwner


def overview(budget, owner, key):
    identity, _, samples = assets.read_asset(budget, QueryOwner(owner), key, with_samples=True)
    stride = max(1, (len(samples) + 1023) // 1024)
    envelope = [
        [float(samples[i : i + stride].min()), float(samples[i : i + stride].max())]
        for i in range(0, len(samples), stride)
    ]
    owner.charge(budget, preparation_bytes=len(envelope) * 32 + 4096)
    return owner.put(
        budget,
        "waveforms",
        dict(
            schema_version="d01-waveform-1",
            asset_id=key,
            source_pcm=identity["audio"]["canonical_pcm"],
            rate=identity["audio"]["sample_rate_hz"],
            frames=len(samples),
            stride=stride,
            envelope=envelope,
            timing="Reduced preview only; native integer half-open frames are authoritative",
        ),
    )


def source_for_asset(owner, key):
    view = QueryOwner(owner)
    identity = record(assets.asset_path(view, key))["identity"]
    bound = assets.read_binding(view, key)
    return dict(
        kind="reference",
        recording_id=key,
        group=key,
        source={**identity["audio"], "local_path": bound["path"]},
    )


def cached_clip(budget, owner, source, bounds, samples=None):
    a, b = bounds
    meta = source["source"]
    if (
        any(isinstance(v, bool) or not isinstance(v, int) for v in bounds)
        or not 0 <= a < b <= meta["sample_count"]
        or (b - a) / meta["sample_rate_hz"] > 30
    ):
        raise InputError("D01 playback: exact native interval must fit thirty seconds")
    key = digest(
        dict(
            version="d01-original-pcm16-1",
            audio=meta["sha256"],
            pcm=meta["canonical_pcm"],
            bounds=bounds,
        )
    )
    locator = owner.directory / "media-keys" / (key + ".json")
    if locator.exists():
        ref = record(locator)["media"]
        validate(owner, ref["record_hash"])
        return ref
    if samples is None:
        shared = getattr(owner, "media_samples", None)
        sample_key = digest(dict(bytes=meta["sha256"], pcm=meta["canonical_pcm"]))
        if shared is not None and shared[0] == sample_key:
            samples = shared[1]
        elif source["kind"] == "reference":
            _, _, samples = assets.read_asset(
                budget, QueryOwner(owner), source["recording_id"], with_samples=True
            )
        else:
            samples = sources.load(budget, source, context=owner)
        # One exact successful decode, one retained source, this bounded worker only.
        owner.media_samples = (sample_key, samples)
    # The shared writer owns the unchanged PCM16 conversion and native verification.
    # Its direct receipt writes are prepaid including atomic temporary overhead here.
    owner.charge(budget, metadata_bytes=16384)
    result = clip(budget, owner.audio / "media", source, samples, a, b, context=owner)
    path = owner.audio / result["path"]
    owner.charge(budget, read_audio_seconds=(b - a) / meta["sample_rate_hz"])
    actual, audio = decode(path, budget)
    expected, gain = pcm16(samples[a:b])
    if (
        not np.array_equal(actual, expected.astype(np.float32) / 32768)
        or audio["sample_count"] != b - a
        or gain != result["gain"]
        or audio["channels"] != meta["channels"]
        or audio["sample_rate_hz"] != meta["sample_rate_hz"]
    ):
        raise InputError("D01 native sample verification failed")
    ref = owner.put(
        budget,
        "media",
        dict(
            schema_version="d01-media-1",
            semantic_key=key,
            original=source,
            bounds=bounds,
            clip=result,
            local_path=path.relative_to(owner.root).as_posix(),
            sha256=result["sha256"],
            bytes=path.stat().st_size,
            native_samples_verified=True,
        ),
    )
    owner.publish(budget, locator, dict(media=ref), immutable=True)
    return ref


def validate(owner, key):
    path = owner.directory / "media" / (key + ".json")
    value = record(path)
    if value["record_hash"] != key:
        raise InputError("D01 media identity differs")
    target = contained(owner.root / value["local_path"], owner.audio / "media")
    # Clip-sized reads only. No decode/inference, ledger writes or original-song reads.
    if not target.is_file() or target.stat().st_size != value["bytes"]:
        raise InputError("D01 media missing/changed; explicitly revalidate the saved result")
    h = hashlib.sha256()
    with target.open("rb") as stream:
        for block in iter(lambda: stream.read(131072), b""):
            h.update(block)
    if h.hexdigest() != value["sha256"]:
        raise InputError("D01 media corrupt; retain failure and revalidate explicitly")
    return target, value


def cards(budget, owner, result, start=0, count=2):
    """Two distinct songs per bounded unit; complete groups remain untouched."""
    old_sources = {s["recording_id"]: s for s in result["population"]}
    refs = result["arms"][result["selected_arm"]]["display"][start : start + count]
    output = []
    for rank, ref in enumerate(refs, start + 1):
        group = owner.get(ref, "group-results")
        first_source = old_sources[group["passages"][0]["representative"]["recording_id"]]
        passages = []
        # Retained alternative passages are explicit references; first is the default player.
        for number, p in enumerate(group["passages"]):
            row = p["representative"]
            source = old_sources[row["recording_id"]]
            item = dict(
                row=row,
                scored_bounds=p["scored_bounds"],
                context_bounds=row["original_context"],
                additional=number > 0,
            )
            if number == 0:
                item["scored"] = cached_clip(budget, owner, source, p["scored_bounds"])
                item["context"] = cached_clip(budget, owner, source, row["original_context"])
            passages.append(item)
        output.append(
            dict(
                rank=rank,
                group=group["group"],
                group_ref=ref,
                score=group["score"],
                title=first_source["title"],
                artist=first_source["artist"],
                passages=passages,
                score_direction="lower distance is better"
                if result["selected_arm"] == "legacy-mean"
                else "higher rank-fusion credit is better",
                query_hash=result["query_hash"],
                population=result["snapshot"]["record_hash"],
                arm=result["selected_arm"],
            )
        )
    return output
