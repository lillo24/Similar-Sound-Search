import hashlib
import struct
import time
from unittest.mock import patch

import numpy as np
import soundfile as sf
from helpers import AudioCase

from similar_sound_search.preparation import crop_frames, prepare
from similar_sound_search.records import map_time
from similar_sound_search.storage import InputError, ResourceError, read_json


class PreparationTests(AudioCase):
    def test_channel_selection_resample_count_and_event_time(self):
        path = self.wav(rate=48000, frames=96000, values={(48000, 1): 24576, (12000, 0): 16384})
        original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        result = prepare(path, self.budget(), 16000, "channel:1", "0.5", "1.5")
        record = result["record"]
        output, rate = sf.read(str(self.root / record["artifact"]["local_path"]), always_2d=True)
        self.assertEqual(rate, 16000)
        self.assertEqual(output.shape, (16000, 1))
        self.assertEqual(int(np.argmax(np.abs(output[:, 0]))), 8000)
        self.assertEqual(map_time(record, 0.5), {"source_seconds": 1, "recording_seconds": None})
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original_hash)
        self.assertEqual(record["source"]["sha256"], original_hash)

    def test_preserve_and_mean_have_independent_channel_answers(self):
        path = self.wav(frames=100, values={(10, 0): 16384, (20, 1): 8192})
        for policy, expected_channels in (("preserve", 2), ("mean", 1)):
            result = prepare(path, self.budget(), 8000, policy)
            output, _ = sf.read(
                str(self.root / result["record"]["artifact"]["local_path"]), always_2d=True
            )
            self.assertEqual(output.shape, (100, expected_channels))
            self.assertEqual(output[10, 0], 0.5 if policy == "preserve" else 0.25)
            self.assertEqual(
                output[20, expected_channels - 1], 0.25 if policy == "preserve" else 0.125
            )

    def test_crop_rounding_and_resample_ceil(self):
        self.assertEqual(crop_frames("0.00012", "0.00026", 100, 8000), (0, 3))
        path = self.wav(rate=44100, frames=1000, values={(441, 0): 16384})
        record = prepare(path, self.budget(), 16000, "channel:0")["record"]
        # ceil(1000*16000/44100) = 363, output lasts 363/16000; mapped span is 1000/44100.
        self.assertEqual(record["artifact"]["sample_count"], 363)
        self.assertAlmostEqual(
            record["timestamp_mapping"]["segments"][0]["asset_end_seconds"], 1000 / 44100
        )
        self.assertAlmostEqual(
            record["timestamp_mapping"]["unmapped_tail_seconds"], 363 / 16000 - 1000 / 44100
        )
        output, _ = sf.read(str(self.root / record["artifact"]["local_path"]))
        self.assertEqual(int(np.argmax(np.abs(output))), 160)
        self.assertAlmostEqual(map_time(record, 160 / 16000)["source_seconds"], 0.01)
        with self.assertRaisesRegex(InputError, "mapping span"):
            map_time(record, 363 / 16000)

    def test_full_track_known_excerpt_and_unknown_excerpt(self):
        full = self.wav("full.wav", rate=1000, frames=242000, values={(219000, 0): 16384})
        full_record = prepare(
            full,
            self.budget(max_duration_seconds=300),
            1000,
            "channel:0",
            "218",
            "240",
            self.context("full_track", 0),
        )["record"]
        self.assertEqual(
            map_time(full_record, 1), {"source_seconds": 219, "recording_seconds": 219}
        )
        excerpt = self.wav("excerpt.wav", rate=1000, frames=22000, values={(1000, 0): 16384})
        known = prepare(
            excerpt, self.budget(), 1000, "channel:0", context=self.context(offset=218)
        )["record"]
        unknown = prepare(excerpt, self.budget(), 1000, "channel:0", context=self.context())[
            "record"
        ]
        self.assertEqual(map_time(known, 1), {"source_seconds": 1, "recording_seconds": 219})
        self.assertEqual(map_time(unknown, 1), {"source_seconds": 1, "recording_seconds": None})
        self.assertEqual(known["artifact"]["sample_count"], 22000)
        self.assertEqual(unknown["timestamp_mapping"]["basis"], "excerpt")
        with self.assertRaisesRegex(InputError, "no clamping"):
            prepare(
                excerpt, self.budget(), 1000, "channel:0", "218", "240", self.context(offset=218)
            )

    def test_composed_maps_apply_original_offset_once(self):
        path = self.wav(rate=8000, frames=16000, values={(8000, 0): 16384})
        first = prepare(
            path, self.budget(), 16000, "channel:0", "0.5", "1.5", self.context(offset=218)
        )["record"]
        second = prepare(
            self.root / first["artifact"]["local_path"],
            self.budget(),
            8000,
            "preserve",
            "0.25",
            "0.75",
            parent_record=first,
        )["record"]
        self.assertEqual(map_time(second, 0.25), {"source_seconds": 1, "recording_seconds": 219})
        self.assertEqual(len(second["processing_history"]), 2)
        self.assertEqual(second["source"]["sha256"], first["source"]["sha256"])
        self.assertEqual(second["timestamp_mapping"]["original_recording_offset_seconds"], 218)

    def test_composed_fractional_padding_remains_unmapped(self):
        path = self.wav(rate=44100, frames=1000, values={(441, 0): 16384})
        first = prepare(path, self.budget(), 16000, "channel:0")["record"]
        second = prepare(
            self.root / first["artifact"]["local_path"],
            self.budget(),
            8000,
            "preserve",
            parent_record=first,
        )["record"]
        mapping = second["timestamp_mapping"]
        self.assertAlmostEqual(mapping["segments"][0]["asset_end_seconds"], 1000 / 44100)
        self.assertGreater(mapping["unmapped_tail_seconds"], 0)

    def test_invalid_intervals_channels_rates_and_silent_crops(self):
        path = self.wav()
        for start, end in (
            (None, "1"),
            ("0", None),
            ("-1", "1"),
            ("0", "2"),
            ("1", "0"),
            ("0", "nan"),
            ("inf", "1"),
            ("0", "0"),
        ):
            with self.subTest(start=start, end=end), self.assertRaises(InputError):
                prepare(path, self.budget(), 8000, "preserve", start, end)
        for policy in ("channel:2", "channel:-1", "channel:x", "channel:1.0", "auto"):
            with self.subTest(policy=policy), self.assertRaises(InputError):
                prepare(path, self.budget(), 8000, policy)
        for rate in (0, -8000, 1.5, True):
            with self.subTest(rate=rate), self.assertRaises(InputError):
                prepare(path, self.budget(), rate, "preserve")
        with self.assertRaisesRegex(InputError, "silent"):
            prepare(path, self.budget(), 8000, "preserve", "0", "0.1")
        opposite = self.wav("opposite.wav", values={(4000, 0): 16384, (4000, 1): -16384})
        with self.assertRaisesRegex(InputError, "silent"):
            prepare(opposite, self.budget(), 8000, "mean")

    def test_repeatable_reuse_change_invalidation_and_parameter_identity(self):
        path = self.wav()
        first = prepare(path, self.budget(), 8000, "preserve")
        repeated = prepare(path, self.budget(), 8000, "preserve")
        self.assertFalse(first["reused"])
        self.assertTrue(repeated["reused"])
        self.assertEqual(first["record"], repeated["record"])
        # Rebuilding after explicit removal reproduces bytes and key in the declared environment.
        bundle = self.root / first["bundle"]
        (bundle / "audio.wav").unlink()
        (bundle / "record.json").unlink()
        bundle.rmdir()
        rebuilt = prepare(path, self.budget(), 8000, "preserve")
        self.assertEqual(rebuilt["record"], first["record"])
        selected = prepare(path, self.budget(), 8000, "channel:0")
        self.assertNotEqual(selected["bundle"], first["bundle"])
        self.wav(values={(4000, 0): 8192, (4000, 1): 16384})
        changed = prepare(path, self.budget(), 8000, "preserve")
        self.assertNotEqual(changed["bundle"], first["bundle"])
        self.assertTrue((self.root / first["bundle"]).is_dir())

    def test_wav_bytes_reproduce_across_wall_clock_seconds(self):
        path = self.wav(frames=100)
        first = prepare(path, self.budget(), 8000, "preserve")
        bundle = self.root / first["bundle"]
        data = (bundle / "audio.wav").read_bytes()
        self.assertEqual(data[:4], b"RIFF")
        offset, chunks = 12, []
        while offset + 8 <= len(data):
            tag, size = struct.unpack_from("<4sI", data, offset)
            chunks.append(tag)
            offset += 8 + size + size % 2
        self.assertEqual(chunks, [b"fmt ", b"fact", b"data"])
        (bundle / "audio.wav").unlink()
        (bundle / "record.json").unlink()
        bundle.rmdir()
        time.sleep(1.1)  # Cross the one-second PEAK timestamp resolution of the old writer.
        second = prepare(path, self.budget(), 8000, "preserve")
        self.assertEqual((self.root / second["bundle"] / "audio.wav").read_bytes(), data)
        self.assertEqual(second["record"], first["record"])

    def test_corrupt_reuse_and_incomplete_parent_are_visible(self):
        path = self.wav()
        first = prepare(path, self.budget(), 8000, "preserve")
        audio = self.root / first["record"]["artifact"]["local_path"]
        audio.write_bytes(b"corrupt")
        with self.assertRaisesRegex(InputError, "corrupt"):
            prepare(path, self.budget(), 8000, "preserve")
        with self.assertRaisesRegex(InputError, "incomplete"):
            prepare(path, self.budget(), 8000, "preserve", parent_record={})
        record_path = self.root / first["bundle"] / "record.json"
        record = read_json(record_path)
        record["timestamp_mapping"]["original_recording_offset_seconds"] = 999
        record_path.write_text(__import__("json").dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(InputError, "integrity"):
            prepare(path, self.budget(), 8000, "preserve")

    def test_parent_rejects_changed_original_or_mismatched_artifact(self):
        path = self.wav()
        first = prepare(path, self.budget(), 8000, "preserve")["record"]
        derivative = self.root / first["artifact"]["local_path"]
        with self.assertRaisesRegex(InputError, "do not match"):
            prepare(path, self.budget(), 8000, "preserve", parent_record=first)
        self.wav(values={(4000, 0): 8192})
        with self.assertRaisesRegex(InputError, "original source changed"):
            prepare(derivative, self.budget(), 8000, "preserve", parent_record=first)

    def test_output_memory_disk_refusal_and_recovery(self):
        path = self.wav()
        for limits, message in (
            ({"max_output_bytes": 100}, "max_output_bytes"),
            ({"max_working_bytes": 1024}, "max_working_bytes"),
            ({"max_managed_bytes": 100}, "max_managed_bytes"),
            ({"min_free_bytes": 10**20}, "headroom"),
            ({"max_resample_factor": 1}, "max_resample_factor"),
        ):
            with self.subTest(limits=limits), self.assertRaisesRegex(ResourceError, message):
                prepare(path, self.budget(**limits), 16000, "preserve")
        self.assertFalse((self.root / "data/audio/prepared").exists())
        recovered = prepare(path, self.budget(), 16000, "preserve")
        self.assertEqual(recovered["status"], "ok")
        self.assertFalse(recovered["reused"])
        # A valid resampled output may exceed the input-file byte cap.
        small_input = self.budget(max_input_bytes=path.stat().st_size)
        self.assertTrue(prepare(path, small_input, 16000, "preserve")["reused"])

    def test_write_failure_cleans_only_own_staging_then_recovers(self):
        path = self.wav()
        unrelated = self.root / "data/audio/prepared/unrelated"
        unrelated.mkdir(parents=True)
        (unrelated / "preserve.txt").write_text("unrelated asset")
        with patch(
            "similar_sound_search.preparation.write_wav", side_effect=OSError("simulated full disk")
        ):
            with self.assertRaisesRegex(OSError, "full disk"):
                prepare(path, self.budget(), 8000, "preserve")
        self.assertEqual(list((self.root / "data/audio/prepared").iterdir()), [unrelated])
        self.assertEqual((unrelated / "preserve.txt").read_text(), "unrelated asset")
        self.assertEqual(prepare(path, self.budget(), 8000, "preserve")["status"], "ok")
