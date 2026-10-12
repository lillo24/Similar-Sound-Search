"""Bounded sequential WAV/FLAC/MP3 decoding, PCM identity, and explicit inventory."""

import hashlib
import os
from pathlib import Path

import numpy as np
import soundfile as sf

from .records import candidate
from .storage import InputError, ResourceError, canonical, contained, is_link, sha256

SUPPORTED = {
    ".wav": {"WAV", "WAVEX", "RF64"},
    ".wave": {"WAV", "WAVEX", "RF64"},
    ".flac": {"FLAC"},
    ".mp3": {"MP3"},
}
SUBTYPES = {"PCM_U8", "PCM_S8", "PCM_16", "PCM_24", "PCM_32", "FLOAT", "DOUBLE"}
SILENCE_PEAK = 1e-12


def probe(path, budget):
    path = Path(path).absolute()
    budget.input_file(path)
    formats = SUPPORTED.get(path.suffix.lower())
    if formats is None:
        raise InputError(
            f"inspect {path}: unsupported extension; accepts PCM/float WAV, FLAC, MP3 Layer III"
        )
    try:
        info = sf.info(str(path))
    except (sf.SoundFileError, ValueError) as exc:
        raise InputError(f"decode header {path}: {exc}") from exc
    budget.check_time("decode header", path)
    accepted = {"MPEG_LAYER_III"} if info.format == "MP3" else SUBTYPES
    if info.format not in formats or info.subtype not in accepted:
        raise InputError(f"decode {path}: unsupported encoding {info.format}/{info.subtype}")
    if info.frames <= 0 or info.samplerate <= 0 or info.channels <= 0:
        raise InputError(f"decode {path}: expected positive frames, sample rate, and channels")
    budget.cap("max_duration_seconds", info.frames / info.samplerate, path)
    budget.cap("max_sample_rate_hz", info.samplerate, path)
    budget.cap("max_channels", info.channels, path)
    decoded = info.frames * info.channels * 4
    budget.cap("max_decoded_bytes", decoded, path)
    # Includes float64 measurement temporaries and at least 32 MiB library workspace.
    budget.cap("max_working_bytes", decoded * 4 + 32 * 1024 * 1024, path)
    return info


def measure(samples):
    peak = np.max(np.abs(samples), axis=0)
    # Accumulate squared blocks in float64 without a full float64 copy of the input.
    energy = np.zeros(samples.shape[1], dtype=np.float64)
    for start in range(0, len(samples), 65536):
        block = samples[start : start + 65536].astype(np.float64)
        energy += np.sum(block * block, axis=0)
    return {
        "peak_per_channel": peak.tolist(),
        "rms_per_channel": np.sqrt(energy / len(samples)).tolist(),
        "silent": bool(np.max(peak) <= SILENCE_PEAK),
        "silence_peak_threshold": SILENCE_PEAK,
    }


def pcm_identity(samples, rate):
    """sss-pcm-f32le-1: header + interleaved float32 LE, signed zero normalized.

    Header is canonical JSON {schema_version,sample_rate_hz,channels,sample_count} + LF.
    No gain, clipping, resampling, channel reduction, dithering, or perceptual matching.
    """
    header = {
        "schema_version": "sss-pcm-f32le-1",
        "sample_rate_hz": rate,
        "channels": samples.shape[1],
        "sample_count": samples.shape[0],
    }
    result = hashlib.sha256(canonical(header) + b"\n")
    for start in range(0, len(samples), 65536):
        block = samples[start : start + 65536].astype("<f4", copy=True)
        block[block == 0] = 0
        result.update(block.tobytes(order="C"))
    return {**header, "sha256": result.hexdigest()}


def decode(path, budget, extra_output_bytes=0, working_bytes=None):
    info = probe(path, budget)
    decoded = info.frames * info.channels * 4
    budget.reserve(extra_output_bytes, working_bytes or decoded * 4 + 32 * 1024 * 1024)
    before = sha256(path, budget)
    try:
        with sf.SoundFile(str(path)) as stream:
            samples = stream.read(frames=info.frames, dtype="float32", always_2d=True)
    except (sf.SoundFileError, ValueError) as exc:
        raise InputError(f"decode samples {path}: {exc}") from exc
    budget.check_time("decode samples", path)
    if samples.shape != (info.frames, info.channels) or not np.isfinite(samples).all():
        raise InputError(
            f"decode {path}: truncated or non-finite samples; expected {info.frames} frames"
        )
    after = sha256(path, budget)
    if before != after:
        raise InputError(
            f"decode {path}: source changed during inspection; retry with an immutable file"
        )
    metadata = {
        "sha256": before,
        "file_bytes": Path(path).stat().st_size,
        "format": info.format,
        "subtype": info.subtype,
        "sample_count": info.frames,
        "sample_rate_hz": info.samplerate,
        "channels": info.channels,
        "duration_seconds": info.frames / info.samplerate,
        "measurement": measure(samples),
        "canonical_pcm": pcm_identity(samples, info.samplerate),
        "decoder": {
            "library": "SoundFile",
            "soundfile": sf.__version__,
            "libsndfile": sf.__libsndfile_version__,
            "route": "full_sequential_float32",
            "time_coordinate": "decoded_available_file",
            "compressed_seek_verified": False,
            "timing_note": (
                "MP3 decoded timeline honors delay/padding metadata as interpreted by libsndfile; "
                "untagged/other encoders may retain unknown priming/padding. Use sequentially "
                "decoded analysis/playback; no sample-exact encoded-stream seek claim."
                if info.format == "MP3"
                else "Lossless sample timeline; float32 conversion defines canonical identity."
            ),
        },
    }
    budget.check_time("measurement", path)
    return samples, metadata


def inspect_file(path, budget, context=None):
    _, metadata = decode(path, budget, extra_output_bytes=65536)
    return candidate(path, metadata, context, budget.root)


def inventory(target, budget, context=None):
    """Files can be explicit external paths; recursive directories must be project-local."""
    target = Path(target).absolute()
    if is_link(target):
        raise InputError(f"inventory {target}: symlink inputs are unsupported")
    if not target.is_dir():
        paths = [target]
    else:
        base = contained(budget.root / "data/audio", budget.root)
        if not target.resolve().is_relative_to(base):
            raise InputError("directory inventory must be inside this project's data/audio")
        paths = []
        for directory, dirs, files in os.walk(target, followlinks=False):
            budget.check_time("inventory", target)
            dirs[:] = sorted(d for d in dirs if not is_link(Path(directory) / d))
            for name in sorted(files):
                path = Path(directory) / name
                if name == ".gitkeep":
                    continue
                if len(paths) >= budget.limits["max_inventory_files"]:
                    raise ResourceError(
                        f"inventory {target}: exceeds max_inventory_files; "
                        "use an explicit smaller directory"
                    )
                paths.append(path)
    entries = []
    for path in paths:
        try:
            record = inspect_file(path, budget, context)
            status = "silent" if record["technical_metadata"]["measurement"]["silent"] else "valid"
            entries.append({"status": status, "record": record})
        except ResourceError as exc:
            return {
                "status": "failed",
                "entries": entries,
                "error": str(exc),
                "resume_target": str(path),
            }
        except (InputError, OSError) as exc:
            entries.append({"status": "invalid", "path": str(path), "error": str(exc)})
    return {
        "status": "failed" if any(e["status"] == "invalid" for e in entries) else "ok",
        "entries": entries,
    }
