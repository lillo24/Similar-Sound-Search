"""Independent PCM fixtures and disposable project roots for A02 tests."""

import json
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from similar_sound_search.resources import Budget, load_limits

REPOSITORY = Path(__file__).resolve().parents[1]


class AudioCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sss-a02-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "config").mkdir()
        (self.root / "manifests/references").mkdir(parents=True)
        shutil.copyfile(
            REPOSITORY / "config/resource_limits.json", self.root / "config/resource_limits.json"
        )
        shutil.copyfile(
            REPOSITORY / "manifests/references/loulou.json",
            self.root / "manifests/references/loulou.json",
        )
        self.limits = load_limits(self.root / "config/resource_limits.json", "smoke")

    def budget(self, **changes):
        return Budget(self.root, {**self.limits, **changes})

    def wav(self, name="fixture.wav", rate=8000, channels=2, frames=8000, values=None):
        path = self.root / "data/audio/originals" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as stream:
            stream.setparams((channels, 2, rate, frames, "NONE", "not compressed"))
            data = bytearray(frames * channels * 2)
            if values is None:
                values = {(frames // 2, channel): 16384 for channel in range(channels)}
            for (frame, channel), value in values.items():
                struct.pack_into("<h", data, 2 * (frame * channels + channel), value)
            stream.writeframes(data)
        return path

    def context(self, kind="excerpt", offset=None):
        result = {
            "schema_version": "a02-input-1",
            "kind": kind,
            "recording": {
                "recording_id": "engineering-test-recording",
                "version": "deterministic PCM fixture",
                "identity_status": "verified",
                "identity_evidence": "Independent fixture construction in tests/helpers.py",
            },
            "provenance": {"permitted_use": "Generated engineering test"},
            "original_recording_offset_seconds": offset,
        }
        if offset is not None:
            result["offset_evidence"] = "Known test construction (not evidence about Loulou)"
        return result

    def json_file(self, path, value):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path
