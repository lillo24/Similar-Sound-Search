import hashlib
import math
from unittest.mock import patch

import numpy as np
import soundfile as sf
from helpers import REPOSITORY, AudioCase

from similar_sound_search.inputs import SUBTYPES, decode, inspect_file, inventory
from similar_sound_search.records import validate_context
from similar_sound_search.storage import InputError, ResourceError, read_json


class InputTests(AudioCase):
    def test_pcm_metadata_hash_and_independent_measurements(self):
        path = self.wav(values={(4000, 0): 16384, (2000, 1): -8192})
        record = inspect_file(path, self.budget())
        metadata = record["technical_metadata"]
        self.assertEqual(metadata["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(
            (metadata["sample_count"], metadata["sample_rate_hz"], metadata["channels"]),
            (8000, 8000, 2),
        )
        self.assertEqual(metadata["duration_seconds"], 1)
        self.assertEqual(metadata["measurement"]["peak_per_channel"], [0.5, 0.25])
        self.assertAlmostEqual(metadata["measurement"]["rms_per_channel"][0], 0.5 / math.sqrt(8000))
        self.assertEqual(record["technical_metadata_status"], "verified")
        self.assertEqual(record["validation_status"], "unverified")
        self.assertEqual(record["recording"]["identity_status"], "unverified")
        self.assertIsNone(record["timestamp_mapping"]["original_recording_offset_seconds"])

    def test_flac_and_float_wav_decode(self):
        for suffix, format_name, subtype in (("flac", "FLAC", "PCM_16"), ("wav", "WAV", "FLOAT")):
            with self.subTest(format=format_name):
                path = self.root / f"input.{suffix}"
                samples = np.array([[0.5], [-0.25], [0.0]], dtype=np.float32)
                sf.write(str(path), samples, 8000, format=format_name, subtype=subtype)
                actual, metadata = decode(path, self.budget())
                np.testing.assert_array_equal(actual, samples)
                self.assertEqual(metadata["sample_count"], 3)

    def test_every_accepted_container_and_subtype_on_known_exact_samples(self):
        samples = np.array([[0.5], [-0.25], [0.0]], dtype=np.float32)
        exercised = set()
        for format_name in ("WAV", "WAVEX", "RF64", "FLAC"):
            for subtype in sorted(SUBTYPES):
                if not sf.check_format(format_name, subtype):
                    continue
                with self.subTest(format=format_name, subtype=subtype):
                    path = self.root / (
                        f"{format_name}-{subtype}.flac"
                        if format_name == "FLAC"
                        else f"{format_name}-{subtype}.wav"
                    )
                    sf.write(str(path), samples, 8000, format=format_name, subtype=subtype)
                    actual, metadata = decode(path, self.budget())
                    np.testing.assert_array_equal(actual, samples)
                    self.assertEqual(metadata["format"], format_name)
                    self.assertEqual(metadata["subtype"], subtype)
                    exercised.add((format_name, subtype))
        self.assertEqual(len(exercised), 21)

    def test_silence_is_valid_and_distinguishable(self):
        path = self.wav(values={})
        result = inventory(path, self.budget())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entries"][0]["status"], "silent")
        self.assertEqual(
            result["entries"][0]["record"]["technical_metadata"]["measurement"]["rms_per_channel"],
            [0, 0],
        )

    def test_corrupt_unsupported_missing_and_wrong_container(self):
        corrupt = self.root / "corrupt.wav"
        corrupt.write_bytes(b"RIFFinvalid")
        unsupported = self.root / "input.ogg"
        unsupported.write_bytes(b"not really an ogg")
        wrong = self.root / "wrong.flac"
        wrong.write_bytes(self.wav().read_bytes())
        for path, error in (
            (corrupt, "decode header"),
            (unsupported, "unsupported extension"),
            (wrong, "unsupported encoding"),
            (self.root / "missing.wav", "existing regular"),
        ):
            with self.subTest(path=path.name), self.assertRaisesRegex(InputError, error):
                inspect_file(path, self.budget())

    def test_nonfinite_float_samples_are_invalid(self):
        path = self.root / "nan.wav"
        sf.write(str(path), np.array([0.5, np.nan], dtype=np.float32), 8000, subtype="FLOAT")
        with self.assertRaisesRegex(InputError, "non-finite"):
            inspect_file(path, self.budget())

    def test_input_and_header_limits_precede_full_decode(self):
        path = self.wav()
        with patch("similar_sound_search.inputs.sf.info") as probe:
            with self.assertRaisesRegex(ResourceError, "max_input_bytes"):
                inspect_file(path, self.budget(max_input_bytes=10))
            probe.assert_not_called()
        for limits in (
            {"max_duration_seconds": 0.5},
            {"max_channels": 1},
            {"max_sample_rate_hz": 4000},
            {"max_decoded_bytes": 8},
            {"max_working_bytes": 1024},
        ):
            with (
                self.subTest(limits=limits),
                patch("similar_sound_search.inputs.sf.SoundFile.read") as read,
            ):
                with self.assertRaises(ResourceError):
                    inspect_file(path, self.budget(**limits))
                read.assert_not_called()

    def test_directory_inventory_reports_invalid_entries_and_bounds(self):
        valid = self.wav("a.wav")
        (valid.parent / "b.mp3").write_bytes(b"unsupported")
        result = inventory(valid.parent, self.budget())
        self.assertEqual(result["status"], "failed")
        self.assertEqual([entry["status"] for entry in result["entries"]], ["valid", "invalid"])
        with self.assertRaisesRegex(ResourceError, "max_inventory_files"):
            inventory(valid.parent, self.budget(max_inventory_files=1))
        with self.assertRaisesRegex(InputError, "data/audio"):
            inventory(self.root.parent, self.budget())
        empty = self.root / "data/audio/empty"
        empty.mkdir()
        self.assertEqual(inventory(empty, self.budget()), {"status": "ok", "entries": []})

    def test_inventory_keeps_completed_entries_on_resource_refusal(self):
        valid = self.wav("a.wav", frames=10)
        self.wav("b.wav", frames=100)
        result = inventory(valid.parent, self.budget(max_input_bytes=100))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["status"], "valid")
        self.assertIn("b.wav", result["resume_target"])

    def test_context_never_verifies_a_filename_or_requested_crop(self):
        path = self.wav("Loulou_218_240.wav", frames=176000)
        context = {
            "schema_version": "a02-input-1",
            "kind": "excerpt",
            "reference_record_id": "reference-loulou-001",
            "requested_interval": {
                "basis": "claimed_recording",
                "start_seconds": 218,
                "end_seconds": 240,
                "status": "approximate",
            },
        }
        record = inspect_file(path, self.budget(), context)
        self.assertEqual(record["source"]["duration_seconds"], 22)
        self.assertIsNone(record["verified_interval"])
        self.assertIsNone(record["timestamp_mapping"]["original_recording_offset_seconds"])
        self.assertEqual(record["timestamp_mapping"]["basis"], "excerpt")
        self.assertEqual(record["requested_interval"], context["requested_interval"])
        self.assertEqual(record["recording"]["identity_status"], "unverified")

    def test_incomplete_and_invalid_context_refused(self):
        cases = [
            {},
            {
                "schema_version": "a02-input-1",
                "kind": "excerpt",
                "original_recording_offset_seconds": 218,
            },
            {
                "schema_version": "a02-input-1",
                "kind": "excerpt",
                "recording": {"identity_status": "verified"},
            },
            {**self.context(offset=218), "original_recording_offset_seconds": float("nan")},
            self.context(kind="full_track", offset=218),
            {**self.context(), "unexpected": True},
            {**self.context(), "provenance": {"permitted_use": ""}},
        ]
        for context in cases:
            with self.subTest(context=context), self.assertRaises(InputError):
                validate_context(context)

    def test_versioned_example_remains_an_unverified_candidate(self):
        context = validate_context(read_json(REPOSITORY / "config/input_context.example.json"))
        self.assertEqual(context["kind"], "excerpt")
        self.assertEqual(context["recording"]["identity_status"], "unverified")
        self.assertIsNone(context["original_recording_offset_seconds"])
        self.assertEqual(context["requested_interval"]["start_seconds"], 218)
