"""Independent PCM boundaries and exact A02 event mappings without delivery-ledger use."""

import copy
import shutil
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase
from scipy.io.wavfile import write as write_wav

from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.events import artifacts, selection
from similar_sound_search.events.context import Context
from similar_sound_search.events.detector import propose
from similar_sound_search.events.fixtures import boundary_cases
from similar_sound_search.events.metrics import boundaries
from similar_sound_search.events.report import build as event_report
from similar_sound_search.inputs import decode
from similar_sound_search.preparation import crop_frames, prepare
from similar_sound_search.records import map_time
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.search.report import clip, verify_bundle
from similar_sound_search.storage import InputError, digest, sha256


class EventCase(AudioCase):
    def setUp(self):
        super().setUp()
        shutil.copyfile(REPOSITORY / "config/events.json", self.root / "config/events.json")
        self.owner = Context(self.root)
        self.cfg = self.owner.cfg

    def sbudget(self):
        return CatalogueBudget(
            self.root, load_limits(self.root / "config/resource_limits.json", "starter")
        )

    def fixture(self, name):
        return next(v for v in boundary_cases() if v["case"] == name)

    def detection(self, name):
        v = self.fixture(name)
        return propose(v["samples"], v["rate"], 0, len(v["samples"]), self.cfg)

    def source(self):
        v = self.fixture("stereo_cancellation")
        path = self.root / "data/audio/originals/tone.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(path, v["rate"], v["samples"])
        self.json_file("config/local/context.json", self.context("excerpt", 218))
        spec = self.json_file(
            "config/local/source.json",
            {
                "schema_version": "b01-source-1",
                "path": path.relative_to(self.root).as_posix(),
                "context": "config/local/context.json",
                "region": {"start_frame": 0, "end_frame": len(v["samples"])},
            },
        )
        return path, spec

    def test_isolated_attack_release_and_stereo_cancellation(self):
        mono = self.detection("isolated")
        stereo = self.detection("stereo_cancellation")
        self.assertEqual(
            [(v["start_frame"], v["end_frame"]) for v in mono["events"]],
            [(v["start_frame"], v["end_frame"]) for v in stereo["events"]],
        )
        event = mono["events"][0]
        self.assertLessEqual(event["start_frame"], 1600)
        self.assertGreaterEqual(event["start_frame"], 1200)
        self.assertGreaterEqual(event["end_frame"], 10080)  # retain >=96% of known release
        self.assertLessEqual(event["end_frame"], 10640)

    def test_release_overlap_is_not_cut_at_next_onset(self):
        events = self.detection("overlap_release")["events"]
        self.assertGreaterEqual(len(events), 2)
        self.assertGreater(events[0]["end_frame"], events[1]["start_frame"])
        self.assertIn("overlapping_activity_unresolved", events[0]["flags"])

    def test_slow_vibrato_noise_silence_and_determinism(self):
        self.assertEqual(self.detection("silence")["state"], "empty")
        for name in ("slow_attack", "vibrato", "noise", "close_notes", "short_transient"):
            value = self.detection(name)
            self.assertEqual(value, self.detection(name))
            self.assertTrue(value["events"])
            self.assertLessEqual(len(value["events"]), 32)
        sustained = self.detection("censored_sustain")
        self.assertTrue(any("release_not_observed" in e["flags"] for e in sustained["events"]))

    def test_duration_cap_and_authorized_region(self):
        x = np.full((8000 * 10, 2), 0.2, np.float32)
        events = propose(x, 8000, 800, 8000 * 10, self.cfg)["events"]
        self.assertEqual(events[0]["end_frame"] - events[0]["start_frame"], 64000)
        self.assertIn("duration_cap_censored", events[0]["flags"])
        self.assertTrue(all(800 <= e["start_frame"] < e["end_frame"] <= 80000 for e in events))

    def test_quiet_isolated_attack_is_not_removed_by_later_loud_sound(self):
        quiet = self.fixture("isolated")["samples"] * 0.01
        loud = np.roll(self.fixture("short_transient")["samples"], 15000, axis=0)
        value = propose(quiet + loud, 8000, 0, len(quiet), self.cfg)
        self.assertTrue(any(e["start_frame"] <= 1600 < e["end_frame"] for e in value["events"]))

    def test_exact_frame_conversion_for_nonterminating_seconds(self):
        for rate in (8000, 11027, 44100, 48000):
            for first, last in ((1, 19), (12345, 23157), (0, 1)):
                a, b = selection.frame_seconds(first, last, rate)
                self.assertEqual(crop_frames(a, b, last + 10, rate), (first, last))

    def test_explicit_manual_native_crop_and_excerpt_mapping(self):
        _, spec = self.source()
        result = artifacts.generate(self.sbudget(), spec, self.owner)
        proposal = self.root / result["proposal"]
        selected = selection.select(self.sbudget(), proposal, self.owner, intervals=[[1600, 10400]])
        output = selection.extract(self.sbudget(), self.root / selected["selection"], self.owner)
        event = record(self.root / output["extraction"])["events"][0]
        self.assertEqual(event["prepared"]["artifact"]["sample_count"], 8800)
        self.assertEqual(event["prepared"]["artifact"]["channels"], 2)
        self.assertAlmostEqual(map_time(event["prepared"], 0.1)["source_seconds"], 0.3)
        self.assertEqual(map_time(event["prepared"], 0.1)["recording_seconds"], 218.3)
        with self.assertRaisesRegex(InputError, "unsupported duration"):
            selection.select(self.sbudget(), proposal, self.owner, intervals=[[1600, 1601]])

    def test_composed_parent_mapping_and_unknown_offset(self):
        path, _ = self.source()
        parent = prepare(
            path, self.sbudget(), 8000, "preserve", ".1", "2.5", self.context("excerpt")
        )
        self.json_file(
            "config/local/composed.json",
            {
                "schema_version": "b01-source-1",
                "path": parent["record"]["artifact"]["local_path"],
                "parent_record": parent["bundle"] + "/record.json",
                "region": {"start_frame": 0, "end_frame": 19200},
            },
        )
        proposals = artifacts.generate(
            self.sbudget(), self.root / "config/local/composed.json", self.owner
        )
        selected = selection.select(
            self.sbudget(), self.root / proposals["proposal"], self.owner, intervals=[[800, 9600]]
        )
        output = selection.extract(self.sbudget(), self.root / selected["selection"], self.owner)
        rec = record(self.root / output["extraction"])["events"][0]["prepared"]
        self.assertAlmostEqual(map_time(rec, 0)["source_seconds"], 0.2)
        self.assertIsNone(map_time(rec, 0)["recording_seconds"])

    def test_selection_order_stale_configuration_and_source(self):
        path, spec = self.source()
        result = artifacts.generate(self.sbudget(), spec, self.owner)
        p = self.root / result["proposal"]
        a = selection.select(self.sbudget(), p, self.owner, intervals=[[1600, 7000], [7000, 10400]])
        b = selection.select(self.sbudget(), p, self.owner, intervals=[[7000, 10400], [1600, 7000]])
        self.assertEqual(a["selection"], b["selection"])
        changed = copy.deepcopy(self.owner.cfg)
        changed["edge_energy_ratio"] = 0.04
        with patch.object(self.owner, "cfg", changed), self.assertRaisesRegex(InputError, "stale"):
            artifacts.validate(self.sbudget(), p, self.owner)
        path.write_bytes(b"corrupted")
        with self.assertRaisesRegex(InputError, "original bytes"):
            artifacts.validate(self.sbudget(), p, self.owner)

    def test_event_report_resumes_wav_only_copy_with_conversion_receipt(self):
        original, spec = self.source()
        props = artifacts.generate(self.sbudget(), spec, self.owner)
        selected = selection.select(
            self.sbudget(), self.root / props["proposal"], self.owner, intervals=[[1600, 10400]]
        )
        extracted = selection.extract(self.sbudget(), self.root / selected["selection"], self.owner)
        samples, metadata = decode(original, self.sbudget())
        paths = {}
        copied = None
        for name in ("single", "multiple"):
            directory = self.owner.reports / name
            media = clip(
                self.sbudget(),
                directory / "media",
                {"source": metadata},
                samples,
                1600,
                10400,
                self.owner,
            )
            (directory / "index.html").write_text("Separate search scores", encoding="utf-8")
            write_record(
                directory / "bundle.json",
                {
                    "html_sha256": sha256(directory / "index.html", self.sbudget()),
                    "items": [{"clip": media}],
                },
                self.sbudget(),
            )
            paths[name + "_report"] = (directory / "index.html").relative_to(self.root).as_posix()
            copied = directory / media["path"]
        extraction = record(self.root / extracted["extraction"])
        identity = {"extraction_hash": extraction["record_hash"], **paths}
        target = self.owner.reports / ("events-" + digest(identity)) / "media" / copied.name
        target.parent.mkdir(parents=True)
        shutil.copyfile(copied, target)  # controlled interrupted WAV-only copy
        result = event_report(
            self.sbudget(),
            {
                "schema_version": "b01-report-input-1",
                "extraction": extracted["extraction"],
                **paths,
            },
            self.owner,
        )
        allowed = verify_bundle(self.root, self.root / result["report"], self.owner.reports)
        self.assertIn("/media/" + copied.name, allowed)
        self.assertTrue(target.with_suffix(".json").is_file())

    def test_one_to_one_sample_answers_do_not_match_one_span_twice(self):
        truth = [{"start_frame": 100, "end_frame": 1100}, {"start_frame": 600, "end_frame": 1600}]
        props = [{**truth[0], "onset_frame": 100, "flags": []}]
        answer = boundaries(
            props, truth, 1000, {"onset_tolerance_seconds": 0.08, "offset_tolerance_seconds": 0.12}
        )
        self.assertEqual((answer["matched"], answer["missed_events"]), (1, 1))
        self.assertEqual(answer["pairs"][0]["attack_coverage"], 1)
