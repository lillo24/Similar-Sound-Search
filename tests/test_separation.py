"""Independent B02 signal/mapping/reuse answers; disposable roots, no model/network."""

import shutil
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase
from scipy.io.wavfile import write as write_wav

from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.events import compatibility
from similar_sound_search.inputs import decode
from similar_sound_search.matchers.models import descriptor
from similar_sound_search.preparation import prepare
from similar_sound_search.records import map_time
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.search import query
from similar_sound_search.search.contracts import recipe_code
from similar_sound_search.separation import artifacts, dsp, metrics
from similar_sound_search.separation.context import Context
from similar_sound_search.separation.job import run
from similar_sound_search.separation.report import page
from similar_sound_search.storage import InputError, ResourceError, sha256


class SeparationCase(AudioCase):
    def setUp(self):
        super().setUp()
        shutil.copyfile(REPOSITORY / "config/separation.json", self.root / "config/separation.json")
        self.owner = Context(self.root)
        self.cfg = self.owner.cfg
        self.catalogue = patch.object(
            artifacts.sources, "catalogue", return_value=([], {"entry_groups": {}})
        )
        self.catalogue.start()
        self.addCleanup(self.catalogue.stop)

    def sbudget(self):
        return CatalogueBudget(
            self.root, load_limits(self.root / "config/resource_limits.json", "starter")
        )

    def signal(self, name="signal", rate=24000):
        t = np.arange(rate * 2) / rate
        x = np.column_stack(
            (0.1 * np.sin(2 * np.pi * 440 * t), -0.1 * np.sin(2 * np.pi * 440 * t))
        ).astype(np.float32)
        path = self.root / "data/audio/originals" / (name + ".wav")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(path, rate, x)
        return path, x

    def spec(self):
        path, _ = self.signal()
        source = {
            "path": path.relative_to(self.root).as_posix(),
            "sha256": sha256(path, self.sbudget()),
        }
        return {
            "schema_version": "b02-process-input-1",
            "source": source,
            "region": [2400, 36000],
            "event": [4800, 31200],
            "cue": {**source, "bounds": [0, 24000]},
        }

    def test_identity_preserves_native_samples_and_gain(self):
        _, x = self.signal()
        y, details = dsp.process(x, 24000, "original", self.cfg)
        self.assertTrue(np.array_equal(y["original"], x))
        self.assertEqual(details, {"delay_frames": 0, "processing_gain": 1.0})

    def test_centred_impulses_and_hop_seams_no_delay(self):
        for length in (1025, 8193):
            x = np.zeros((length, 2), np.float32)
            x[[0, 255, 256, length - 1]] = np.array([0.4, -0.4])
            z, w, padded = dsp.stft(x, self.cfg)
            y = dsp.inverse(z, w, padded, length, self.cfg)
            np.testing.assert_allclose(y, x, atol=8e-8)
            self.assertEqual(np.argmax(np.abs(y[:, 0])), np.argmax(np.abs(x[:, 0])))

    def test_broad_components_keep_cancelling_stereo_and_sum(self):
        _, x = self.signal()
        out, details = dsp.process(x, 24000, "broad", self.cfg)
        np.testing.assert_allclose(out["harmonic"] + out["percussive"], x, atol=1e-7)
        self.assertGreater(np.linalg.norm(out["harmonic"]), 0.5 * np.linalg.norm(x))
        np.testing.assert_allclose(out["harmonic"][:, 0], -out["harmonic"][:, 1], atol=1e-7)
        self.assertLess(details["reconstruction_max_error"], 1e-7)

    def test_guided_depends_on_explicit_audio_cue(self):
        t = np.arange(24000) / 24000
        a = (0.1 * np.sin(2 * np.pi * 440 * t))[:, None].astype(np.float32)
        b = (0.1 * np.sin(2 * np.pi * 880 * t))[:, None].astype(np.float32)
        first, _ = dsp.process(a + b, 24000, "guided", self.cfg, a, 24000)
        second, _ = dsp.process(a + b, 24000, "guided", self.cfg, b, 24000)
        self.assertGreater(np.linalg.norm(first["extracted"] - second["extracted"]), 1)
        self.assertGreater(
            float(first["extracted"].ravel() @ a.ravel()),
            float(first["extracted"].ravel() @ b.ravel()),
        )
        np.testing.assert_allclose(first["extracted"] + first["residual"], a + b, atol=1e-7)

    def test_missing_silent_wrong_shape_and_nonfinite_are_failures(self):
        _, x = self.signal()
        with self.assertRaisesRegex(InputError, "explicit audio cue"):
            dsp.process(x, 24000, "guided", self.cfg)
        with self.assertRaisesRegex(InputError, "silent cue"):
            dsp.process(x, 24000, "guided", self.cfg, np.zeros((2400, 1)), 24000)
        for bad in (np.array([[np.nan]]), np.zeros((2, 3)), np.zeros((0, 1))):
            with self.assertRaises(InputError):
                dsp.process(bad, 24000, "broad", self.cfg)

    def test_cue_resampling_preserves_physical_frequency(self):
        t = np.arange(22050) / 22050
        x = np.sin(2 * np.pi * 440 * t)[:, None].astype(np.float32)
        y = dsp.convert_cue(x, 44100, 22050)
        self.assertEqual(y.shape, (44100, 1))
        self.assertEqual(np.argmax(np.abs(np.fft.rfft(y[:, 0]))), 440)

    def test_silence_is_explicit_low_output_not_extraction_success(self):
        x = np.zeros((2400, 1), np.float32)
        out, _ = dsp.process(x, 24000, "broad", self.cfg)
        self.assertEqual(dsp.summaries(out["harmonic"], x)["state"], "near_silence")

    def test_region_temp_and_counter_bounds(self):
        with self.assertRaises(ResourceError):
            dsp.process(np.zeros((24000 * 13, 1)), 24000, "broad", self.cfg)
        cfg = {**self.cfg, "max_temporary_bytes": 1}
        with self.assertRaises(ResourceError):
            dsp.process(np.ones((2400, 1)), 24000, "broad", cfg)
        self.owner.charge(self.sbudget(), query_jobs=16)
        with self.assertRaises(ResourceError):
            self.owner.charge(self.sbudget(), query_jobs=1)
        self.assertFalse((self.root / "data/runs/events/work.json").exists())

    def test_receipt_reuse_charges_reads_without_reprocessing(self):
        spec = self.spec()
        result = artifacts.process(self.sbudget(), spec, "broad", self.owner)
        before = record(self.owner.directory / "work.json")["counts"]
        repeated = artifacts.process(self.sbudget(), spec, "broad", self.owner)
        after = record(self.owner.directory / "work.json")["counts"]
        self.assertTrue(repeated["reused"])
        self.assertEqual(before["processing_inputs"], after["processing_inputs"])
        self.assertGreater(after["read_audio_seconds"], before["read_audio_seconds"])
        artifacts.validate(self.sbudget(), self.root / result["transform"], self.owner)

    def test_exact_excerpt_and_nonzero_crop_mapping(self):
        spec = self.spec()
        self.json_file("config/local/context.json", self.context("excerpt", 218))
        spec["source"]["context"] = "config/local/context.json"
        result = artifacts.process(self.sbudget(), spec, "original", self.owner)
        saved = record(self.root / result["transform"])
        output = saved["outputs"]["original"]
        self.assertEqual(
            map_time({"timestamp_mapping": output["mapping"]}, 0.1),
            {"source_seconds": 0.2, "recording_seconds": 218.2},
        )
        crop, _ = decode(self.root / output["path"], self.sbudget())
        _, original = self.signal()
        self.assertTrue(np.array_equal(crop, original[2400:36000]))

    def test_composed_changed_rate_parent_mapping(self):
        path, _ = self.signal(rate=44100)
        p = prepare(
            path,
            self.sbudget(),
            22050,
            "preserve",
            ".1",
            "1.9",
            context=self.context("excerpt", 218),
        )
        spec = {
            "schema_version": "b02-process-input-1",
            "source": {
                "path": p["record"]["artifact"]["local_path"],
                "sha256": p["record"]["artifact"]["sha256"],
                "parent_record": p["bundle"] + "/record.json",
            },
            "region": [2205, 22050],
            "event": [4410, 20000],
        }
        result = artifacts.process(self.sbudget(), spec, "original", self.owner)
        saved = record(self.root / result["transform"])
        mapping = saved["outputs"]["original"]["mapping"]
        self.assertAlmostEqual(map_time({"timestamp_mapping": mapping}, 0)["source_seconds"], 0.2)
        self.assertAlmostEqual(
            map_time({"timestamp_mapping": mapping}, 0)["recording_seconds"], 218.2
        )

    def test_cue_change_invalidates_cache_and_old_receipt(self):
        spec = self.spec()
        cue, _ = self.signal("cue")
        spec["cue"] = {
            "path": cue.relative_to(self.root).as_posix(),
            "sha256": sha256(cue, self.sbudget()),
            "bounds": [0, 24000],
        }
        first = artifacts.process(self.sbudget(), spec, "guided", self.owner)
        write_wav(cue, 24000, np.ones((48000, 2), np.float32) * 0.1)
        with self.assertRaisesRegex(InputError, "bytes changed"):
            artifacts.validate(self.sbudget(), self.root / first["transform"], self.owner)
        spec["cue"]["sha256"] = sha256(cue, self.sbudget())
        second = artifacts.process(self.sbudget(), spec, "guided", self.owner)
        self.assertNotEqual(first["transform"], second["transform"])

    def test_corrupt_output_and_map_fail_loud(self):
        spec = self.spec()
        result = artifacts.process(self.sbudget(), spec, "original", self.owner)
        path = self.root / result["transform"]
        value = record(path)
        value["outputs"]["original"]["mapping"]["segments"][0]["source_start_seconds"] = 0
        write_record(path, value, self.sbudget())
        with self.assertRaisesRegex(InputError, "map changed"):
            artifacts.validate(self.sbudget(), path, self.owner)
        (self.root / value["outputs"]["original"]["path"]).unlink()
        with self.assertRaises((InputError, OSError)):
            artifacts.validate(self.sbudget(), path, self.owner)

    def test_interrupted_unit_retains_charge_and_reconstructs_receipt(self):
        spec = self.spec()
        first = artifacts.process(self.sbudget(), spec, "original", self.owner)
        path = self.root / first["transform"]
        audio = record(path)["outputs"]["original"]["path"]
        before = (self.root / audio).read_bytes()
        path.unlink()  # simulate a crash after audio publication but before receipt
        second = artifacts.process(self.sbudget(), spec, "original", self.owner)
        self.assertFalse(second["reused"])
        self.assertEqual(before, (self.root / audio).read_bytes())
        self.assertEqual(
            record(self.owner.directory / "work.json")["counts"]["processing_inputs"], 2
        )

    def test_source_and_cue_parents_excluded_without_filename_inference(self):
        spec = self.spec()
        records = [
            {
                "entry_id": "parent",
                "source_asset": {
                    "sha256": spec["source"]["sha256"],
                    "canonical_pcm": {"sha256": "other"},
                },
                "analysis_derivative": {"sha256": "derivative"},
            }
        ]
        with patch.object(
            artifacts.sources,
            "catalogue",
            return_value=(records, {"entry_groups": {"parent": "known-duplicates"}}),
        ):
            result = artifacts.process(self.sbudget(), spec, "original", self.owner)
        self.assertEqual(
            record(self.root / result["transform"])["excluded_groups"], ["known-duplicates"]
        )

    def test_wrong_receipt_component_and_missing_cue_do_not_fallback(self):
        spec = self.spec()
        spec.pop("cue")
        with self.assertRaisesRegex(InputError, "explicit cue"):
            artifacts.process(self.sbudget(), spec, "guided", self.owner)
        with self.assertRaisesRegex(InputError, "receipt and component"):
            self.owner.resolve_example(self.sbudget(), {"path": "invented.wav"})

    def test_exact_target_metrics_expose_attenuation_tail_loss_and_absence(self):
        target = np.ones((24000, 1)) * 0.1
        processed = target.copy()
        processed[-4800:] *= 0.1
        value = metrics.preservation(processed, target, target, 24000)
        self.assertAlmostEqual(value["tail_projection"], 0.1)
        self.assertEqual(value["delay_frames"], 0)
        self.assertLess(value["sdr_improvement_db"], 0)
        self.assertEqual(
            metrics.preservation(processed, np.zeros_like(target), target, 24000)["state"],
            "target-absent",
        )

    def test_retained_failed_workers_and_historical_guard(self):
        limits = load_limits(self.root / "config/resource_limits.json", "starter")
        result = run(
            {"root": str(self.root), "limits": limits, "separation_action": "pilot"},
            lambda request: {"status": "failed", "error": "simulated interruption"},
        )
        self.assertEqual(result["work"]["counts"]["workers"], 1)
        self.assertGreaterEqual(result["ledger"]["charged_worker_seconds"], 0)
        compatibility.audit(REPOSITORY)
        with self.assertRaisesRegex(InputError, "unaudited"):
            recipe_code(REPOSITORY)

    def test_processed_handoff_dedup_unions_every_parent_before_reuse(self):
        for name in ("search.json", "matcher_methods.json"):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        spec = self.spec()
        a = artifacts.process(self.sbudget(), spec, "original", self.owner)
        spec = {**spec, "label": "second independently bound parent"}
        b = artifacts.process(self.sbudget(), spec, "original", self.owner)
        items = [{"b02_record": v["transform"], "component": "original"} for v in (a, b)]
        one = self.json_file(
            "config/local/query-one.json",
            {"schema_version": "a06-query-input-1", "examples": items},
        )
        two = self.json_file(
            "config/local/query-two.json",
            {"schema_version": "a06-query-input-1", "examples": [items[1], items[0], items[0]]},
        )
        resolver = self.owner.resolve_example

        def ancestry(budget, item):
            resolved, groups = resolver(budget, item)
            return resolved, groups + ["cue-parent-a" if item == items[0] else "cue-parent-b"]

        desc = descriptor(self.root, "acoustic")
        with (
            patch.object(query, "frozen", return_value=({}, {}, {}, {}, desc)),
            patch.object(self.owner, "resolve_example", side_effect=ancestry),
        ):
            first = query.prepare_query(self.sbudget(), one, "acoustic", self.owner)
            second = query.prepare_query(self.sbudget(), two, "acoustic", self.owner)
        self.assertTrue(second["reused"])
        self.assertEqual(first["query_id"], second["query_id"])
        self.assertEqual(first["examples"], 1)
        self.assertEqual(
            record(self.root / first["query"])["identity"]["excluded_groups"],
            ["cue-parent-a", "cue-parent-b"],
        )

    def test_page_truthfully_labels_derived_and_original_and_escapes_metadata(self):
        value = {
            "decision": {},
            "items": [
                {
                    "label": "Processed <script>",
                    "timeline": "available-file 10..12.4",
                    "signal_role": "Processed component · extracted",
                    "score": None,
                    "clip": {
                        "path": "media/a.wav",
                        "duration_seconds": 2.4,
                        "rate": 44100,
                        "channels": 2,
                        "gain": 1,
                    },
                }
            ],
        }
        rendered = page(value)
        self.assertIn("Processed &lt;script&gt;", rendered)
        self.assertIn("Processed component · extracted", rendered)
        self.assertIn("Candidate cards always play original mixtures", " ".join(rendered.split()))
        self.assertIn('id="seek-0"', rendered)
        self.assertIn("Media missing or stale", rendered)
