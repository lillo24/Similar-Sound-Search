"""Offline independent A04 rank, interval, renderer, split and contract answers."""

import shutil
import struct
from unittest.mock import patch

import numpy as np
import soundfile as sf
from helpers import REPOSITORY, AudioCase

from similar_sound_search.catalogue.ingestion import (
    ingest,
    local_descriptor,
    validate_local_ready,
)
from similar_sound_search.catalogue.job import load_policy as catalogue_policy
from similar_sound_search.catalogue.transfer import Ledger, public_url
from similar_sound_search.evaluation.artifacts import (
    charge_generation,
    load_asset,
    publish,
    record,
    write_record,
)
from similar_sound_search.evaluation.job import load_policy, run
from similar_sound_search.evaluation.protocol import freeze, validate_splits
from similar_sound_search.evaluation.published import unique_pairs
from similar_sound_search.evaluation.rendering import (
    FRAMES,
    MIX_FRAMES,
    RATE,
    mix,
    presets,
    render_tone,
)
from similar_sound_search.evaluation.scoring import (
    event_matches,
    known_answers,
    ranked,
    score,
    signed_rank,
)
from similar_sound_search.evaluation.suite import build, validate
from similar_sound_search.inputs import decode
from similar_sound_search.resources import CatalogueBudget
from similar_sound_search.storage import InputError, ResourceError, digest, sha256


class EvaluationBase(AudioCase):
    def setUp(self):
        super().setUp()
        for name in ("evaluation.json", "published_benchmark.json"):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        self.policy = load_policy(self.root)
        self.directory = self.root / "data/runs/evaluation"

    def ebudget(self):
        return CatalogueBudget(self.root, {**self.limits, "max_seconds": 120})


class EvaluationCase(EvaluationBase):
    def test_aiff_independent_big_endian_pcm_and_preparation(self):
        # A hand-written FORM/COMM/SSND fixture, independent of libsndfile's writer.
        path = self.root / "data/audio/engineering/test.aiff"
        path.parent.mkdir(parents=True)
        pcm = struct.pack(">hhhh", 0, 16384, -16384, 8192)
        comm = struct.pack(">hIh", 1, 4, 16) + bytes.fromhex("400bfa00000000000000")  # 8000 Hz
        body = b"AIFFCOMM" + struct.pack(">I", len(comm)) + comm
        body += b"SSND" + struct.pack(">I", len(pcm) + 8) + b"\0" * 8 + pcm
        path.write_bytes(b"FORM" + struct.pack(">I", len(body)) + body)
        samples, metadata = decode(path, self.ebudget())
        self.assertEqual((metadata["sample_count"], metadata["sample_rate_hz"]), (4, 8000))
        np.testing.assert_array_equal(samples[:, 0], [0, 0.5, -0.5, 0.25])
        from similar_sound_search.preparation import prepare

        result = prepare(path, self.ebudget(), 16000, "preserve")
        self.assertEqual(result["record"]["artifact"]["sample_count"], 8)
        self.assertEqual(result["record"]["source"]["sha256"], metadata["sha256"])

    def test_aiff_float_and_unsupported_compression(self):
        path = self.root / "test.aif"
        sf.write(str(path), [0.1, 0.2], 8000, format="AIFF", subtype="FLOAT")
        self.assertEqual(decode(path, self.ebudget())[1]["subtype"], "FLOAT")
        sf.write(str(path), [0.1, 0.2], 8000, format="AIFF", subtype="ULAW")
        with self.assertRaisesRegex(InputError, "unsupported encoding"):
            decode(path, self.ebudget())

    def test_aiff_header_resource_and_mismatched_container(self):
        path = self.root / "test.aiff"
        sf.write(str(path), np.ones(8000), 8000, format="AIFF", subtype="PCM_16")
        with self.assertRaises(ResourceError):
            decode(path, self.budget(max_duration_seconds=0.1))
        sf.write(str(path), np.ones(8), 8000, format="WAV", subtype="PCM_16")
        with self.assertRaises(InputError):
            decode(path, self.ebudget())

    def test_pinned_transport_does_not_weaken_archive_rule(self):
        url = "https://raw.githubusercontent.com/ben-hayes/timbre-dissimilarity-metrics/262ca43c2105483eac03c775cd1adba6273a9e6b/timbremetrics/sounds/Grey1977/BN.aiff"
        self.assertEqual(public_url(url, source="timbre_github"), url)
        for changed in (
            url.replace("262ca43c2105483eac03c775cd1adba6273a9e6b", "main"),
            url.replace("raw.githubusercontent.com", "github.com"),
            url + "?token=secret",
            url.replace("/BN.aiff", "/../BN.aiff"),
            url.replace("https:", "http:"),
        ):
            with self.assertRaises(InputError):
                public_url(changed, source="timbre_github")
        with self.assertRaises(InputError):
            public_url(url)
        self.assertEqual(
            public_url("https://archive.org/download/item/track.mp3"),
            "https://archive.org/download/item/track.mp3",
        )

    def test_rating_masks_zeros_missing_and_diagonal(self):
        matrix = [[900, 0, 2], [0, 900, 3], [0, 0, 900]]
        mask = np.triu(np.ones((3, 3), dtype=bool), 1)
        self.assertEqual(
            unique_pairs(matrix, mask, "upper_triangle"), [[0, 1, 0.0], [0, 2, 2.0], [1, 2, 3.0]]
        )
        mask[0, 2] = False
        matrix[0][2] = float("nan")
        self.assertEqual(len(unique_pairs(matrix, mask, "upper_triangle")), 2)
        mask[0, 2] = True
        with self.assertRaises(InputError):
            unique_pairs(matrix, mask, "upper_triangle")

    def test_full_matrix_duplicates_and_conflicts(self):
        matrix = [[0, 1, 2], [1, 0, 3], [2, 3, 0]]
        mask = ~np.eye(3, dtype=bool)
        self.assertEqual(len(unique_pairs(matrix, mask, "symmetric")), 3)
        matrix[1][0] = 9
        with self.assertRaisesRegex(InputError, "incompatible"):
            unique_pairs(matrix, mask, "symmetric")

    def test_signed_nontrivial_permutations_and_ties(self):
        a = [30, 10, 40, 20]
        self.assertAlmostEqual(signed_rank(a, [3, 1, 4, 2])["rho"], 1)
        self.assertAlmostEqual(signed_rank(a, [2, 4, 1, 3])["rho"], -1)
        self.assertAlmostEqual(signed_rank(a, [2, 4, 1, 3], "higher_better")["rho"], 1)
        # Average ranks [1.5,1.5,3] and [1,2.5,2.5]: covariance ratio 0.5.
        self.assertAlmostEqual(signed_rank([1, 1, 2], [1, 2, 2])["rho"], 0.5)

    def test_undefined_and_invalid_correlation(self):
        self.assertIsNone(signed_rank([1, 2], [1, 2])["rho"])
        self.assertIsNone(signed_rank([1, 2, 3], [5, 5, 5])["rho"])
        self.assertIsNone(signed_rank([2, 2, 2], [1, 2, 3])["rho"])
        for scores in ([1, 2, float("nan")], [1, 2], [1, 2, float("inf")]):
            with self.assertRaises(InputError):
                signed_rank([1, 2, 3], scores)

    def test_varied_balanced_deterministic_renderer(self):
        identities = presets(42104)
        self.assertEqual(len(identities), 16)
        self.assertEqual(len({p["family"] for p in identities}), 8)
        waveforms = []
        for mechanism in ("harmonic", "pluck", "fm", "noise"):
            p = next(p for p in identities if p["mechanism"] == mechanism)
            a, detail = render_tone(p, 1, 2, 19)
            b, _ = render_tone(p, 1, 2, 19)
            np.testing.assert_array_equal(a, b)
            self.assertEqual((len(a), detail["events"][-1]["end_frame"]), (FRAMES, FRAMES))
            self.assertTrue(np.isfinite(a).all())
            self.assertAlmostEqual(float(np.sqrt(np.mean(a * a))), 0.08)
            self.assertLess(np.max(np.abs(a)), 0.9)
            waveforms.append(a)
        for i, a in enumerate(waveforms):
            for b in waveforms[:i]:
                self.assertFalse(np.array_equal(a, b))

    def test_mixture_active_ratio_boundaries_and_common_gain(self):
        target = np.ones(2400) * 0.2
        background = np.ones(MIX_FRAMES) * 0.1
        for db in (-12, 0, 12):
            output, details = mix(target, background, [0, MIX_FRAMES - 2400], db)
            self.assertEqual(details["insertions"], [[0, 2400], [MIX_FRAMES - 2400, MIX_FRAMES]])
            ratio = (output[0] / details["common_gain"] - 0.1) / 0.1
            self.assertAlmostEqual(20 * np.log10(ratio), db)
            self.assertLessEqual(float(np.max(np.abs(output))), 0.90000001)
            self.assertAlmostEqual(output[3000], 0.1 * details["common_gain"])
        absent, details = mix(target, background, [], None)
        np.testing.assert_array_equal(absent, background)
        self.assertIsNone(details["achieved_tbr_db"])
        for positions in ([-1], [MIX_FRAMES - 10]):
            with self.assertRaises(InputError):
                mix(target, background, positions, 0)

    def test_generation_identity_reuse_change_and_corruption(self):
        budget = self.ebudget()
        recipe = {"frames": 800, "rate": 8000, "seed": 1}

        def render():
            return np.ones(800) * 0.1, {"families": ["test"], "split": "development"}

        value, reused = publish(recipe, render, budget, self.policy, self.directory)
        self.assertFalse(reused)
        counter = record(self.directory / "construction.json")["bytes"]
        self.assertTrue(publish(recipe, render, budget, self.policy, self.directory)[1])
        self.assertEqual(record(self.directory / "construction.json")["bytes"], counter)
        changed, _ = publish({**recipe, "seed": 2}, render, budget, self.policy, self.directory)
        self.assertNotEqual(value["asset_id"], changed["asset_id"])
        (self.root / value["local_path"]).write_bytes(b"corrupt")
        with self.assertRaises(InputError):
            publish(recipe, render, budget, self.policy, self.directory)

    def test_output_identity_and_tool_change_invalidation(self):
        recipe = {"frames": 800, "rate": 8000}
        value, _ = publish(
            recipe, lambda: (np.ones(800) * 0.1, {}), self.ebudget(), self.policy, self.directory
        )
        with patch(
            "similar_sound_search.evaluation.artifacts.versions", return_value={"changed": True}
        ):
            with self.assertRaisesRegex(InputError, "version changed"):
                load_asset(self.root, value["asset_id"], self.ebudget())

    def test_durable_generation_and_worker_reservations(self):
        budget = self.ebudget()
        policy = {**self.policy, "max_generation_items": 1}
        charge_generation(self.directory, budget, policy, 1000, 1)
        with self.assertRaises(ResourceError):
            charge_generation(self.directory, self.ebudget(), policy, 1, 1)
        ledger = Ledger(self.directory, self.ebudget(), self.policy, "a04-ledger-1")
        ledger.begin_worker(10)
        second = Ledger(self.directory, self.ebudget(), self.policy, "a04-ledger-1")
        self.assertEqual(second.value["charged_worker_seconds"], 10)
        with self.assertRaises(InputError):
            Ledger(self.directory, self.ebudget(), self.policy)  # A03 cannot open A04 accounting.

    def test_evaluation_manifests_in_managed_disk(self):
        budget = self.ebudget()
        before = budget.managed_bytes()
        write_record(self.root / "manifests/evaluation/test.json", {"x": "value"}, budget)
        self.assertGreater(budget.managed_bytes(), before)
        self.assertEqual(budget.managed_bytes(), self.ebudget().managed_bytes())

    def test_split_ancestry_rejects_target_and_accompaniment_leaks(self):
        protocol = freeze(self.ebudget(), self.policy)
        families = protocol["families"]
        dev = next(k for k, v in families.items() if v == "development")
        held = next(k for k, v in families.items() if v == "held_out")
        value = {"asset_id": "mixture", "split": "development", "families": [dev, held]}
        with self.assertRaisesRegex(InputError, "split leakage"):
            validate_splits(protocol, [value])
        self.assertEqual(
            len({p["family"] for p in protocol["presets"] if p["split"] == "held_out"}), 4
        )

    def test_pilot_repeat_and_frozen_policy(self):
        first = build(self.ebudget(), self.policy, self.directory, pilot=True)
        second = build(self.ebudget(), self.policy, self.directory, pilot=True)
        self.assertEqual((first["assets"], second["reused"]), (12, 12))
        with self.assertRaisesRegex(InputError, "frozen resource policy"):
            freeze(self.ebudget(), {**self.policy, "max_job_seconds": 2500})

    def test_worker_timeout_is_charged_and_explicit(self):
        request = {"root": str(self.root), "limits": self.limits}
        result = run(
            request,
            lambda r: {"status": "failed", "error_type": "ResourceError", "error": "timeout"},
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["ledger"]["pending_worker_seconds"], 0)
        self.assertGreaterEqual(result["ledger"]["charged_worker_seconds"], 0)

    def test_catalogue_consumer_is_read_only_and_requires_private_readiness(self):
        budget = self.ebudget()
        directory = self.root / "data/runs/catalogue/consumer-test"
        output = self.root / "manifests/private/catalogue/consumer-test"
        policy = catalogue_policy(REPOSITORY / "config/catalogue.json")
        ledger = Ledger(directory, budget, policy)
        path = self.wav(frames=8000, rate=8000)
        result = ingest(
            local_descriptor(path, self.context("full_track", 0)),
            directory,
            ledger,
            output,
            local_input=path,
        )
        value = record(output / "entries" / (result["entry_id"] + ".json"))
        before = sha256(ledger.path, budget)
        samples, _ = validate_local_ready(value, budget, "consumer-test")
        self.assertGreater(len(samples), 0)
        self.assertEqual(sha256(ledger.path, budget), before)
        private = directory / "entries" / (result["entry_id"] + ".json")
        private.unlink()
        with self.assertRaisesRegex(InputError, "private local registration missing"):
            validate_local_ready(value, budget, "consumer-test")

    def test_mixture_audio_audit_detects_wrong_insertion_gain(self):
        from similar_sound_search.evaluation.suite import _audit_mixture

        budget = self.ebudget()
        data = np.ones(FRAMES) * 0.1
        recipe = {"frames": FRAMES, "rate": RATE}
        target, _ = publish(recipe, lambda: (data, {}), budget, self.policy, self.directory)
        background = np.resize(data, MIX_FRAMES)
        samples, details = mix(data, background, [0], 0)
        value = {
            **details,
            "split": "development",
            "identity": {
                "recipe": {
                    "background": {"kind": "procedural_repeat", "asset_id": target["asset_id"]},
                    "target_asset": target["asset_id"],
                    "positions": [0],
                    "target_to_background_db": 0,
                }
            },
        }
        _audit_mixture(samples.astype(np.float32), value, {}, budget)
        damaged = samples.astype(np.float32)
        damaged[0] += 0.05
        with self.assertRaisesRegex(InputError, "waveform/gain/insertion"):
            _audit_mixture(damaged, value, {}, budget)


class ScoringCase(AudioCase):
    def setUp(self):
        super().setUp()
        self.assets = {
            k: {"audio": {"sample_count": 100, "sample_rate_hz": 10}, "split": "development"}
            for k in ("a", "b")
        }
        self.protocol = {
            "record_hash": "protocol",
            "k": [1, 5, 10],
            "matching": {"minimum_iou": 0.5},
        }
        self.target = {"asset_id": "a", "start_frame": 10, "end_frame": 30}
        self.query = {
            "query_id": "q",
            "split": "development",
            "condition": "mixture",
            "task": "mixture",
            "candidate_assets": ["a", "b"],
            "targets": [self.target],
        }
        self.suite = {"queries": [self.query], "record_hash": "suite"}
        config = {"test": True}
        self.prediction = {
            "schema_version": "a04-predictions-1",
            "protocol_hash": "protocol",
            "suite_hash": "suite",
            "split": "development",
            "coordinate_basis": "decoded_available_file",
            "score_direction": "higher_better",
            "run_id": "unit",
            "method_id": "independent-truth",
            "configuration": config,
            "config_hash": digest(config),
            "evidence_kind": "harness_oracle",
            "cost": {
                "wall_seconds": 0,
                "processed_audio_seconds": 0,
                "storage_bytes": 0,
                "peak_working_bytes_estimate": 0,
            },
            "queries": [],
        }

    def output(self, candidate, refined=None):
        self.prediction["queries"] = [
            {
                "query_id": "q",
                "candidate": candidate,
                "refined": candidate if refined is None else refined,
            }
        ]
        return score(self.prediction, self.protocol, self.suite, self.assets)

    def metric(self, result, k="1", stage="candidate"):
        return result["conditions"]["mixture"]["stages"][stage]["at_k"][k]

    def test_exact_and_boundary_offset_errors(self):
        result = self.output([{**self.target, "start_frame": 12, "end_frame": 32, "score": 1}])
        metrics = self.metric(result)
        self.assertEqual(metrics["recovered_targets"], 1)
        self.assertAlmostEqual(metrics["mean_absolute_boundary_error_seconds"], 0.2)
        self.assertAlmostEqual(metrics["conditional_localisation"][0]["iou"], 18 / 22)

    def test_duplicate_overlapping_hits_one_event(self):
        values = [
            {**self.target, "score": 1},
            {**self.target, "score": 1},
            {**self.target, "start_frame": 11, "score": 0.5},
        ]
        result = self.output(values)
        self.assertEqual(self.metric(result, "10")["recovered_targets"], 1)
        self.assertEqual(len(ranked(values, "higher_better", self.assets)), 2)
        self.assertEqual(len(event_matches(values, [self.target])), 1)

    def test_one_broad_prediction_cannot_cover_multiple_events(self):
        self.query["targets"] = [self.target, {**self.target, "start_frame": 30, "end_frame": 50}]
        result = self.output([{**self.target, "end_frame": 50, "score": 1}])
        self.assertEqual(self.metric(result)["recovered_targets"], 1)
        self.assertEqual(self.metric(result)["target_denominator"], 2)
        self.assertEqual(self.metric(result)["hit_rate"], 1)
        self.assertEqual(self.metric(result)["target_coverage"], 0.5)

    def test_prefix_omission_wrong_asset_and_shorter_than_k(self):
        result = self.output(
            [{**self.target, "asset_id": "b", "score": 2}, {**self.target, "score": 1}]
        )
        self.assertEqual(self.metric(result)["recovered_targets"], 0)
        self.assertEqual(self.metric(result, "10")["recovered_targets"], 1)
        self.assertEqual(self.metric(result)["missed_targets"], 1)
        self.assertIsNone(self.metric(result)["mean_absolute_boundary_error_seconds"])

    def test_candidate_and_refined_lists_are_separate(self):
        result = self.output([{**self.target, "score": 1}], [])
        self.assertEqual(self.metric(result)["recovered_targets"], 1)
        self.assertEqual(self.metric(result, stage="refined")["recovered_targets"], 0)
        with self.assertRaisesRegex(InputError, "not contained"):
            self.output(
                [{**self.target, "asset_id": "b", "score": 1}], [{**self.target, "score": 1}]
            )

    def test_missing_outputs_remain_in_denominators(self):
        result = score(self.prediction, self.protocol, self.suite, self.assets)
        self.assertEqual(result["missing_queries"], ["q"])
        self.assertEqual(self.metric(result)["target_denominator"], 1)
        self.assertEqual(self.metric(result)["hit_rate"], 0)

    def test_absence_is_not_forced_top_k_presence(self):
        self.query["targets"] = []
        result = self.output([{**self.target, "score": 99}])
        stage = result["conditions"]["mixture"]["stages"]["candidate"]
        self.assertEqual(stage["absent_top_scores"], [99])
        self.assertIsNone(stage["false_accepts"])
        self.assertIsNone(self.metric(result)["hit_rate"])

    def test_invalid_scores_ids_bounds_duplicates_and_stale_contract(self):
        for changes in (
            {"score": float("nan")},
            {"score": float("inf")},
            {"asset_id": "unknown"},
            {"end_frame": 101},
            {"start_frame": -1},
            {"start_frame": 1.5},
        ):
            with self.assertRaises(InputError):
                self.output([{**self.target, "score": 1, **changes}])
        with self.assertRaisesRegex(InputError, "conflicting"):
            self.output([{**self.target, "score": 1}, {**self.target, "score": 2}])
        self.prediction["protocol_hash"] = "old"
        with self.assertRaisesRegex(InputError, "stale"):
            self.output([])

    def test_tie_order_is_stable_for_both_directions(self):
        values = [{**self.target, "asset_id": "b", "score": 1}, {**self.target, "score": 1}]
        for direction in ("higher_better", "lower_better"):
            self.assertEqual(ranked(values, direction, self.assets)[0]["asset_id"], "a")

    def test_held_out_model_gate_and_cross_split(self):
        self.query["split"] = "held_out"
        self.prediction.update(split="held_out", evidence_kind="matcher")
        with self.assertRaisesRegex(InputError, "reserved for A06"):
            score(self.prediction, self.protocol, self.suite, self.assets, "held_out")


class SuiteIntegrationCase(EvaluationBase):
    # One end-to-end full procedural run, separate from the small independent unit answers.
    def test_full_suite_audit_and_known_answer_command(self):
        budget = self.ebudget()
        result = build(budget, self.policy, self.directory)
        self.assertEqual((result["assets"], result["queries"]), (208, 160))
        checked = validate(self.ebudget(), "all")
        self.assertEqual(checked["assets"], {"development": 104, "held_out": 104})
        self.assertEqual(known_answers(self.ebudget())["runs"]["oracle"]["recovered_at_10"], 88)
