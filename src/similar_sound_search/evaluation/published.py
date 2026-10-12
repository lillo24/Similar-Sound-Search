"""Pinned human-study inspection/import; unresolved rights/mappings stay quarantined."""

import hashlib
from pathlib import Path

import numpy as np

from ..catalogue.transfer import fetch
from ..inputs import decode
from ..storage import InputError, contained, digest, read_json, sha256
from .artifacts import record, write_record


def unique_pairs(matrix, mask, convention):
    """Return unique observed pairs; explicit masks distinguish genuine zero from missing.

    Upper-triangle storage placeholders and the diagonal are never observations. A full
    matrix requires symmetric validity and equal values; conflicting halves fail loudly.
    """
    matrix = np.asarray(matrix, dtype=float)
    mask = np.asarray(mask)
    if (
        matrix.ndim != 2
        or matrix.shape[0] != matrix.shape[1]
        or mask.shape != matrix.shape
        or mask.dtype != bool
        or convention not in {"upper_triangle", "symmetric"}
    ):
        raise InputError("ratings: expected square matrix, boolean mask and explicit convention")
    pairs = []
    for i in range(len(matrix)):
        for j in range(i + 1, len(matrix)):
            if convention == "symmetric" and (
                mask[i, j] != mask[j, i] or mask[i, j] and matrix[i, j] != matrix[j, i]
            ):
                raise InputError(f"ratings {i},{j}: incompatible full-matrix triangles")
            if mask[i, j]:
                if not np.isfinite(matrix[i, j]):
                    raise InputError(f"ratings {i},{j}: observed value must be finite")
                pairs.append([i, j, float(matrix[i, j])])
    return pairs


def inspect_dataset(budget, ledger):
    source = read_json(budget.root / "config/published_benchmark.json")
    if source["dataset"] != "Grey1977" or source["revision"] != (
        "262ca43c2105483eac03c775cd1adba6273a9e6b"
    ):
        raise InputError("published source: adapter only supports reviewed pinned Grey1977")
    # No flag can bypass the unresolved original mapping/rights. A new reviewed adapter
    # and protocol revision are required to enable model scoring.
    if source["scoring_eligible"] is not False:
        raise InputError("Grey1977: rights/original mapping unresolved; cannot enable scoring")
    directory = contained(budget.root / "data/runs/evaluation/published", budget.root)
    destination = contained(budget.root / "data/audio/evaluation/published/Grey1977", budget.root)
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    stimuli = {}
    for entry in source["files"]:
        name = Path(entry["path"]).name
        path = destination / name
        if not path.exists():
            staging = directory / name
            url = (
                "https://raw.githubusercontent.com/"
                + source["repository"]
                + "/"
                + source["revision"]
                + "/"
                + entry["path"]
            )
            fetch(url, staging, ledger, 1024 * 1024, entry["bytes"], source="timbre_github")
            _check_blob(staging, entry, budget)
            staging.rename(path)
            budget.refresh_disk()
        _check_blob(path, entry, budget)
        files.append({**entry, "sha256": sha256(path, budget)})
        if name.endswith(".aiff"):
            _, metadata = decode(path, budget)
            if metadata["measurement"]["silent"]:
                raise InputError(f"published {name}: silent stimulus")
            stimuli[name] = {
                "stimulus_id": "Grey1977:" + name.removesuffix(".aiff"),
                "audio": metadata,
                "local_path": path.relative_to(budget.root).as_posix(),
                "data_role": "published_human_rated_quarantine",
                "preprocessing": "native complete sequential decode; no crop/resample/gain",
                "source_family": "grey-orchestral-" + name[0],
                "original_recording_offset_seconds": None,
            }
    matrix = np.loadtxt(destination / "Grey1977_dissimilarity_matrix.txt")
    if matrix.shape != (16, 16) or len(stimuli) != 16:
        raise InputError("Grey1977: expected 16 aligned stimuli and 16x16 matrix")
    if np.any(np.tril(matrix) != 0):
        raise InputError("Grey1977: expected zero diagonal/lower storage placeholders")
    mask = np.triu(np.ones(matrix.shape, dtype=bool), 1)
    pairs = unique_pairs(matrix, mask, source["storage"])
    order = source["order"]
    if order != sorted(stimuli):
        raise InputError("Grey1977: pinned explicit loader order differs from downloaded files")
    private = {
        "schema_version": "a04-human-1",
        "source": source,
        "files": files,
        "order": [stimuli[name] for name in order],
        "raw_matrix": matrix.tolist(),
        "valid_pair_mask": mask.tolist(),
        "pairs": pairs,
        "availability": "downloaded_validated_quarantined",
        "scoring_eligible": False,
    }
    write_record(directory / "dataset.json", private, budget)
    summary = {
        "schema_version": "a04-human-summary-1",
        "dataset": "Grey1977",
        "source": source,
        "files": files,
        "sounds": 16,
        "observed_unique_pairs": len(pairs),
        "usable_scoring_pairs": 0,
        "availability": private["availability"],
        "scoring_eligible": False,
        "native_seconds": sum(x["audio"]["duration_seconds"] for x in stimuli.values()),
        "reasons": [source["rights_status"], source["mapping_status"]],
        "raw_data_record_hash": digest(private),
    }
    write_record(budget.root / "manifests/evaluation/published.json", summary, budget)
    return {"status": "ok", "assessment": "partial", **summary}


def _check_blob(path, entry, budget):
    budget.input_file(path)
    if path.stat().st_size != entry["bytes"]:
        raise InputError(f"published {path.name}: pinned byte count changed")
    raw = path.read_bytes()  # preflight <=1 MiB selected individual files
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if actual != entry["git_blob_sha1"]:
        raise InputError(f"published {path.name}: pinned Git blob checksum changed")


def validate_downloads(budget):
    value = record(budget.root / "data/runs/evaluation/published/dataset.json")
    for file in value["files"]:
        path = budget.root / "data/audio/evaluation/published/Grey1977" / Path(file["path"]).name
        _check_blob(path, file, budget)
        if sha256(path, budget) != file["sha256"]:
            raise InputError(f"published {path.name}: SHA256 differs from import")
        if path.suffix == ".aiff":
            _, metadata = decode(path, budget)
            expected = next(x for x in value["order"] if Path(x["local_path"]).name == path.name)
            if metadata != expected["audio"]:
                raise InputError(f"published {path.name}: decoder identity/sample metadata differs")
    return {"sounds": len(value["order"]), "scoring_eligible": False}
