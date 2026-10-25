"""Read the installed provider, verify the saved reference, copy only 21 exact clips."""

import shutil
import sys
from pathlib import Path

from . import feedback, manifest
from .common import MIB, ReviewError, output_limits, put_new, read, sha


def prepare(project, workspace, output):
    # This command is run with the existing installed interpreter under -I.
    # Import the installed provider only here, never while serving the review.
    import similar_sound_search
    from similar_sound_search.application import api
    from similar_sound_search.evaluation.artifacts import record
    from sound_search_distribution import contracts
    from sound_search_distribution.runtime import Runtime

    installed = Path(similar_sound_search.__file__).resolve()
    manifest.require(not installed.is_relative_to(project), "Use the non-editable D03 interpreter")
    runtime = Runtime(workspace)
    result = api.result(workspace, manifest.JOB, runtime=runtime)
    owner = runtime.context(workspace, manifest.JOB)
    query = owner.get(result["query"], "queries")
    d03 = read(project / "reports/D03_PACKAGE.json")
    declaration = contracts.consumer(owner)
    private = record(workspace / "private-assets.json")
    name = "b91a8bffd1e5170651feaa874190096201a2df647833d41a621a5e09ef07bf79.wav"
    choices = [n for n in private["files"] if n.endswith("/" + name)]
    route = dict(path="/private-reference/loulou.wav", available=False)
    try:
        reference_path, _ = runtime.artifact(route["path"])
        route["available"] = True
        route["sha256"] = sha(reference_path)
    except Exception as exc:
        # Explicit process boundary: retain the exact provider failure, then use
        # only the independently bound, existing byte-identical reference below.
        route["error_type"], route["error"] = type(exc).__name__, str(exc)
    bundle_directory = "6f80c1786000d30144d0a3bf3da4dc777059f6cd391c13393e2dd3f712a6c405"
    bundle_hash = "b7c1bae8c55f488883a599d4486b85d382b6d66eecabc6bbf028871e4ae48aee"
    retained = record(
        project / "reports/local/c03" / ("refinement-" + bundle_directory) / "bundle.json"
    )
    manifest.require(retained["record_hash"] == bundle_hash, "Retained reference bundle differs")
    old = retained["items"][0]
    clip = old["clip"]
    manifest.require(
        old["source_audio"]["sha256"] == manifest.REFERENCE_SHA
        and clip["sha256"] == manifest.REFERENCE_WAV
        and [clip["source_start_frame"], clip["source_end_frame"]] == [9613800, 10584000]
        and clip["rate"] == 44100
        and clip["frames"] == 970200
        and clip["gain"] == 1.0
        and clip["samples_verified"] is True,
        "Retained full-mixture reference/selection proof differs",
    )
    manifest.require(bool(choices), "Exact original reference unavailable; no substitute allowed")
    for name in choices:
        meta = private["files"][name]
        manifest.require(meta["sha256"] == manifest.REFERENCE_WAV, "Reference dependency differs")
        path = workspace / name
        manifest.require(
            path.stat().st_size == meta["bytes"] and sha(path) == meta["sha256"],
            "Retained reference copy is corrupt",
        )
    # All declared duplicates were checked. Select the exact bundle used by its proof.
    expected = "reports/local/c03/refinement-" + bundle_directory + "/" + clip["path"]
    manifest.require(expected in choices, "Bound retained reference path missing")
    reference_path = workspace / expected
    original = workspace / old["source_audio"]["local_path"]
    manifest.require(sha(original) == manifest.REFERENCE_SHA, "Supplied original MP3 bytes differ")
    reference_media = dict(
        media_id="c03-" + Path(clip["path"]).stem,
        sha256=clip["sha256"],
        bytes=reference_path.stat().st_size,
        frames=970200,
        sample_rate_hz=44100,
        channels=2,
        sample_width=2,
        gain=1.0,
        source_frames=[9613800, 10584000],
        native_proof="retained C03 sample verification; fresh D04 bytes/header only",
    )
    manifest.audio_header(reference_path, reference_media)
    reference = dict(
        title="daoud — Loulou & the loulous",
        source_sha256=manifest.REFERENCE_SHA,
        interval="03:38.000–04:00.000",
        context_frames=[9569700, 10628100],
        context_interval="03:37.000–04:01.000",
        media=reference_media,
        retained_bundle_hash=bundle_hash,
        timing="supplied available-file timeline",
    )
    package = dict(
        release="d03-1.0.0",
        core="0.3.0",
        archive_bytes=292441732,
        archive_sha256=d03["artifact"]["sha256"],
        wheel_sha256="239ce5dd302eef45b1acd296fe84906128b1727a4c941b40b1d3254eda145e0b",
        installed_consumer=declaration,
        search_scope=(
            "Loulou ran on preceding installed artifact; final artifact reopened/verified it"
        ),
    )
    review, copies = manifest.freeze(
        d03["handoff"],
        result,
        query,
        lambda rid, mid: api.result_media(workspace, rid, mid, runtime=runtime),
        reference,
        package,
    )
    copies[manifest.REFERENCE_WAV] = reference_path
    output_limits(output, sum(p.stat().st_size for p in copies.values()) + MIB, "bundle")
    public = project / "manifests/listening/d04-v1.json"
    if public.exists():
        manifest.require(read(public) == review, "Immutable review already exists with other input")
    else:
        put_new(public, review)
    bundle = output / "bundle"
    if bundle.exists():
        raise ReviewError("Review bundle exists; retain it, never silently replace its media")
    (bundle / "media").mkdir(parents=True)
    put_new(bundle / "review.json", review)
    template = feedback.blank(review)
    put_new(bundle / "feedback-template.json", template)
    template_path = project / "manifests/listening/d04-feedback-template.json"
    if not template_path.exists():
        put_new(template_path, template)
    for key, source in copies.items():
        destination = bundle / "media" / (key + ".wav")
        with source.open("rb") as src, destination.open("xb") as dst:
            shutil.copyfileobj(src, dst, 131072)
        manifest.require(sha(destination) == key, "Private review copy differs")
    put_new(output / "metadata/launch.json", dict(python=sys.executable))
    put_new(
        output / "metadata/preparation.json",
        dict(
            review_hash=review["record_hash"],
            installed_module=str(installed),
            provider="installed api.result(job_id) and api.result_media(result_id, media_id)",
            read_only_reference_route=route,
            identical_reference_copies_verified=len(choices),
            reference_resolution="exact retained C03 bundle, source SHA and native selection",
            available_media=len(copies),
            media_bytes=sum(p.stat().st_size for p in copies.values()),
            decoded_original_audio_seconds=0,
            new_inference=False,
            catalogue_encodes=0,
            scope=(
                "fresh byte/header/frame audit; retained native sample proofs, "
                "no new full-source audit"
            ),
        ),
    )
    output_limits(output)
    print(
        "Prepared",
        review["review_version"],
        review["record_hash"],
        "with",
        len(copies),
        "exact clips",
    )
