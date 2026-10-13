"""Reviewed acquisition, explicit representation metadata and model availability."""

import hashlib
import time
from pathlib import Path

from ..catalogue.transfer import Ledger, fetch
from ..evaluation.artifacts import record, write_record
from ..preparation import versions
from ..storage import InputError, contained, digest, is_link, read_json, sha256
from .acoustic import Acoustic
from .windows import POLICY


def configuration(root):
    value = read_json(root / "config/matcher_methods.json")
    if value["schema_version"] != "a05-methods-1" or value["shortlist"] != [
        "acoustic",
        "efficientat",
    ]:
        raise InputError("A05 reviewed shortlist requires acoustic and one MN04 checkpoint")
    return value


def checkpoint_path(root):
    path = root / "data/models/efficientat/mn04_as_mAP_432.pt"
    if is_link(path):
        raise InputError("EfficientAT: linked checkpoint file refused")
    return contained(path, root / "data/models")


def acquire(budget, policy):
    cfg = configuration(budget.root)["checkpoint"]
    if cfg["asset_id"] != 84971629 or cfg["bytes"] != 4066513:
        raise InputError("EfficientAT: reviewed release asset identity/length differs")
    path = checkpoint_path(budget.root)
    reused = path.exists()
    if not reused:
        ledger = Ledger(budget.root / "data/runs/matchers", budget, policy, "a05-ledger-1")
        staging = budget.root / "data/runs/matchers/mn04-download.pt"
        url = "https://github.com/fschmid56/EfficientAT/releases/download/v0.0.1/mn04_as_mAP_432.pt"
        fetch(url, staging, ledger, 8 * 1024 * 1024, cfg["bytes"], source="efficientat")
        actual = sha256(staging, budget)
        if cfg["sha256"] and actual != cfg["sha256"]:
            raise InputError("EfficientAT acquisition: pinned checkpoint SHA256 differs")
        path.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(path)
        budget.refresh_disk()
    if path.stat().st_size != cfg["bytes"]:
        raise InputError("EfficientAT: checkpoint length differs")
    actual = sha256(path, budget)
    if cfg["sha256"] and actual != cfg["sha256"]:
        raise InputError("EfficientAT reuse: corrupt checkpoint SHA256")
    write_record(
        budget.root / "manifests/matchers/checkpoint.json",
        {
            "source": cfg,
            "sha256": actual,
            "bytes": path.stat().st_size,
            "checksum_provenance": (
                "captured from bounded official release acquisition; upstream release "
                "supplies no digest"
            ),
        },
        budget,
    )
    return {
        "status": "ok",
        "sha256": actual,
        "bytes": path.stat().st_size,
        "reused": reused,
        "inference": "not run",
    }


def descriptor(root, method):
    if method not in configuration(root)["shortlist"]:
        raise InputError("A05 method outside frozen shortlist")
    files = ["acoustic.py"] + (
        ["efficientat.py", "efficientat_model.py"] if method == "efficientat" else []
    )
    code = {
        name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
        for name in files
    }
    common = {
        "version": "a05-representation-1",
        "method": method,
        "code": code,
        "tools": versions(),
        "grid": POLICY,
        "device": "cpu",
        "precision": "float32",
        "channel_policy": "arithmetic mean",
        "resampling": "resample_poly Kaiser5 constant-zero; elapsed-time scale 1",
        "admissible_seconds": [0.0001, 30],
        "truncation": "none; whole selected input",
        "score_direction": "lower_better",
        "normalization_fit": "none; fixed declared scales; no held-out fit",
    }
    if method == "acoustic":
        return {
            **common,
            "input_rate": 24000,
            "dimension": 56,
            "distance": "euclidean",
            "feature_layer": (
                "13 cepstral mean/std + 5 spectral mean/std + 16 relative RMS bins + "
                "4 envelope descriptors"
            ),
            "frontend": (
                "600 symmetric-Hann samples, FFT1024, hop240 plus unique tail; 40 L1 "
                "HTK triangles 40..12000Hz; natural-log normalized power, orthonormal "
                "DCT-II; fixed feature scales"
            ),
            "pooling": "mean/std plus relative envelope; explicit level descriptors",
            "padding": "zero pad only inputs shorter than 600 samples",
        }
    cfg = configuration(root)["checkpoint"]
    if not isinstance(cfg["sha256"], str) or len(cfg["sha256"]) != 64:
        raise InputError("EfficientAT: capture and pin official checkpoint SHA256 before inference")
    return {
        **common,
        "input_rate": 32000,
        "dimension": 384,
        "distance": "cosine",
        "checkpoint": cfg,
        "optional_tools": {"torch": "2.6.0+cpu"},
        "feature_layer": "last convolution before classifier; spatial mean",
        "pooling": "frequency/time average, no logits",
        "frontend": (
            "native preemphasis .97; symmetric Hann800 FFT1024 hop320 centered "
            "reflect; Kaldi128 mel 0..15000Hz; log(power+1e-5), (x+4.5)/5"
        ),
        "padding": "zero pad only inputs shorter than 1024 samples; no 10-second extension",
        "augmentation": "disabled; eval/inference_mode; deterministic CPU",
    }


def adapter(budget, method, desc):
    started = time.perf_counter()
    if method == "acoustic":
        obj = Acoustic()
    else:
        path = checkpoint_path(budget.root)
        if not path.is_file() or sha256(path, budget) != desc["checkpoint"]["sha256"]:
            raise InputError("EfficientAT weights missing/corrupt; explicit acquisition required")
        from .efficientat import EfficientAT

        obj = EfficientAT(path)
    return obj, time.perf_counter() - started


def shortlist(budget, protocol, suite):
    cfg = configuration(budget.root)
    if len(cfg["shortlist"]) > budget.limits["max_model_candidates"]:
        raise InputError("A05 candidate count exceeds tier cap")
    value = {
        "schema_version": "a05-shortlist-1",
        "protocol_hash": protocol["record_hash"],
        "suite_hash": suite["record_hash"],
        "methods": {m: descriptor(budget.root, m) for m in cfg["shortlist"]},
        "exclusions": cfg["exclusions"],
        "frozen_before_model_rankings": True,
    }
    path = budget.root / "manifests/matchers/shortlist.json"
    if path.exists():
        old = record(path)
        if digest(value) != old["record_hash"]:
            raise InputError(
                "A05 frozen shortlist/config/code differs; preserve evidence, no score-driven sweep"
            )
        return old
    write_record(path, value, budget)
    return record(path)
