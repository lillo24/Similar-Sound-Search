"""Offline geometry, truth isolation, representation/cache and selection invariants."""

import math
import shutil
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase

from similar_sound_search.catalogue.transfer import public_url
from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.evaluation.job import load_policy
from similar_sound_search.evaluation.protocol import comparison_pair, freeze
from similar_sound_search.evaluation.scoring import event_matches, ranked
from similar_sound_search.evaluation.suite import build, load_suite
from similar_sound_search.matchers.acoustic import Acoustic, checked, distance, waveform
from similar_sound_search.matchers.cache import get, paths, put
from similar_sound_search.matchers.correction import OLD_PROTOCOL, OLD_SUITE, controls, prediction
from similar_sound_search.matchers.efficientat import EfficientAT
from similar_sound_search.matchers.job import charge, offline_network, policy, run
from similar_sound_search.matchers.models import descriptor
from similar_sound_search.matchers.runner import peak_memory, run_batch
from similar_sound_search.matchers.selection import choose, criteria
from similar_sound_search.matchers.windows import POLICY, intervals, routes
from similar_sound_search.resources import CatalogueBudget
from similar_sound_search.storage import InputError, ResourceError, digest


class MatcherCase(AudioCase):
    def setUp(self):
        super().setUp()
        for name in (
            "evaluation.json",
            "published_benchmark.json",
            "matchers.json",
            "matcher_methods.json",
        ):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        self.settings = policy(self.root)

    def mbudget(self):
        return CatalogueBudget(
            self.root, {**self.limits, "max_seconds": 120, "max_model_candidates": 3}
        )

    def route(self):
        return {
            "asset_id": "opaque",
            "sha256": "audio-bytes",
            "pcm": "decoded-pcm",
            "sample_rate_hz": 24000,
            "start_frame": 0,
            "end_frame": 57600,
        }

    def tone(self):
        return (0.1 * np.sin(2 * np.pi * 440 * np.arange(57600) / 24000)).astype(np.float32)

    def test_grid_tail_unique_boundaries_and_not_truth_aligned(self):
        grid = intervals(192000, 57600, 24000)
        self.assertEqual(len(grid), 24)
        self.assertEqual(grid[:2], [(0, 57600), (6000, 63600)])
        self.assertEqual(grid[-1], (134400, 192000))
        self.assertEqual(len(set(grid)), 24)
        self.assertEqual(intervals(177600, 57600, 24000)[-1], (120000, 177600))
        self.assertEqual(intervals(57600, 57600, 24000), [(0, 57600)])
        self.assertEqual(intervals(500, 400, 24000, True), [(0, 500)])

    def test_grid_refuses_invalid_counts(self):
        for args in ((1, 2, 24000), (1, 1, 3), (0, 1, 24000), (True, 1, 24000)):
            with self.assertRaises(InputError):
                intervals(*args)

    def test_independent_geometry_and_random_expectation(self):
        grid = [
            {"asset_id": "mix", "start_frame": s, "end_frame": e}
            for s, e in intervals(192000, 57600, 24000)
        ]
        counts = []
        hits = []
        for starts in ([0, 134400], [18000], [72000]):
            targets = [
                {"asset_id": "mix", "start_frame": s, "end_frame": s + 57600} for s in starts
            ]
            counts.append(sum(bool(event_matches([p], targets)) for p in grid))
            hits.append(bool(event_matches(grid[:1], targets)))
            self.assertTrue(event_matches(grid[:10], targets))
        self.assertEqual(counts, [8, 7, 7])
        self.assertAlmostEqual(sum(hits) / 3, 2 / 3)
        expected = sum(1 - math.comb(24 - m, 10) / math.comb(24, 10) for m in counts) / 3
        self.assertAlmostEqual(expected, 0.992028237687142, places=8)
        self.assertAlmostEqual(sum(m / 24 for m in counts) / 3, 11 / 36)

    def test_real_scorer_control_audit_uses_frozen_geometry(self):
        base = REPOSITORY / "manifests/evaluation"
        protocol = record(base / "protocol-history" / (OLD_PROTOCOL + ".json"))
        suite = record(base / "suite-history" / (OLD_SUITE + ".json"))
        assets = {k: record(base / "assets" / (k + ".json")) for k in suite["assets"]}
        result = controls(protocol, suite, assets, self.mbudget())
        values = [
            result["controls"]["constant"]["conditions"]["source_consistency:" + level]["stages"][
                "candidate"
            ]["at_k"]["1"]["hit_rate"]
            for level in ("-12", "0", "12")
        ]
        self.assertEqual(values, [1, 1, 0])
        self.assertFalse(result["model_scores_inspected"])

    def test_truth_and_names_do_not_change_routes(self):
        root = REPOSITORY / "manifests/evaluation"
        suite = record(root / "suite.json")
        assets = {k: record(root / "assets" / (k + ".json")) for k in suite["assets"]}
        original = routes(suite, assets)
        for q in suite["queries"]:
            q["targets"] = []
            q["designated_source"] = "wrong secret"
            q["condition"] = "different labels"
        for a in assets.values():
            a["families"] = ["secret"]
            a["source_id"] = "secret"
            a["local_path"] = "secret.wav"
        self.assertEqual(routes(suite, assets), original)

    def test_waveform_preserves_length_channel_mean_and_source_time(self):
        x = self.tone()
        stereo = np.stack([x, x * 3], axis=1)
        mono = waveform(stereo, 24000, 32000)
        self.assertEqual(len(mono), 76800)
        np.testing.assert_allclose(mono, waveform(x * 2, 24000, 32000), atol=1e-7)
        self.assertAlmostEqual(57600 / 24000, len(mono) / 32000)

    def test_waveform_refuses_invalid_or_overlong_inputs(self):
        for x, rate in (
            ([], 24000),
            ([np.nan], 24000),
            ([1], True),
            (np.ones((2, 9)), 24000),
            (np.ones(31 * 24000), 24000),
        ):
            with self.assertRaises(InputError):
                waveform(x, rate, 24000)

    def test_acoustic_complete_finite_deterministic_and_envelope_sensitive(self):
        obj = Acoustic()
        x = self.tone()
        a = obj.encode(x, 24000)
        self.assertEqual(a.shape, (56,))
        self.assertEqual(a.dtype, np.dtype("float32"))
        np.testing.assert_array_equal(a, obj.encode(x, 24000))
        self.assertTrue(np.isfinite(obj.encode(np.zeros(24), 24000)).all())
        self.assertGreater(
            distance(a, obj.encode(x * np.linspace(1, 0, len(x)), 24000), "euclidean"), 0
        )

    def test_fixed_scaling_has_no_held_out_fit(self):
        d = descriptor(self.root, "acoustic")
        self.assertIn("none", d["normalization_fit"])
        self.assertEqual(d["input_rate"], 24000)
        self.assertEqual(d["grid"], POLICY)

    def test_distance_independent_answers_invalid_finite_dimension(self):
        self.assertEqual(distance(np.array([0, 0]), np.array([3, 4]), "euclidean"), 5)
        self.assertEqual(distance(np.array([1.0, 0]), np.array([0.0, 1]), "cosine"), 1)
        for a, b, metric in (
            ([0], [0], "cosine"),
            ([1], [1, 2], "euclidean"),
            ([np.nan], [1], "euclidean"),
            ([1], [1], "unknown"),
        ):
            with self.assertRaises(InputError):
                distance(a, b, metric)
        with self.assertRaises(InputError):
            checked(np.ones(2), 3)
        with self.assertRaises(InputError):
            checked(np.array([np.inf]), 1)

    def test_cache_reuse_and_dependency_invalidation(self):
        b = self.mbudget()
        desc = descriptor(self.root, "acoustic")
        route = self.route()
        value, metadata = put(b, self.settings, route, desc, Acoustic(), self.tone())
        with patch.object(Acoustic, "encode", side_effect=AssertionError("should reuse")):
            cached, _ = get(b, route, desc)
        np.testing.assert_array_equal(cached, value)
        self.assertGreater(metadata["extraction_seconds"], 0)
        for key, new in [("sha256", "changed"), ("start_frame", 1), ("pcm", "changed")]:
            changed = {**route, key: new}
            self.assertIsNone(get(b, changed, desc))
        self.assertIsNone(get(b, route, {**desc, "code": {"changed": True}}))

    def test_cache_corrupt_array_metadata_and_orphan_fail(self):
        b = self.mbudget()
        d = descriptor(self.root, "acoustic")
        r = self.route()
        put(b, self.settings, r, d, Acoustic(), self.tone())
        _, _, path, manifest = paths(b, r, d)
        path.write_bytes(b"corrupt")
        with self.assertRaisesRegex(InputError, "corrupt"):
            get(b, r, d)
        manifest.unlink()
        with self.assertRaisesRegex(InputError, "orphan"):
            get(b, r, d)

    def test_failed_inference_is_not_cached_and_is_charged(self):
        b = self.mbudget()
        d = descriptor(self.root, "acoustic")
        with patch.object(Acoustic, "encode", side_effect=InputError("bad inference")):
            with self.assertRaisesRegex(InputError, "bad inference"):
                put(b, self.settings, self.route(), d, Acoustic(), self.tone())
        self.assertIsNone(get(b, self.route(), d))
        self.assertEqual(
            record(self.root / "data/runs/matchers/work.json")["counts"]["processed_windows"], 1
        )

    def test_lifetime_limits_lowering_never_replenishes(self):
        b = self.mbudget()
        p = {**self.settings, "max_model_runs": 1}
        charge(b, p, model_runs=1)
        with self.assertRaises(ResourceError):
            charge(b, self.settings, model_runs=1)

    def test_missing_weights_fail_before_optional_import(self):
        with self.assertRaisesRegex(InputError, "weights missing"):
            EfficientAT(self.root / "missing.pt")

    def test_transport_default_not_broadened_and_pinned_redirects(self):
        url = "https://github.com/fschmid56/EfficientAT/releases/download/v0.0.1/mn04_as_mAP_432.pt"
        with self.assertRaises(InputError):
            public_url(url)
        self.assertEqual(public_url(url, source="efficientat"), url)
        with self.assertRaises(InputError):
            public_url(url.replace("mn04", "mn10"), source="efficientat")
        with self.assertRaises(InputError):
            public_url("https://evil.example/file", source="efficientat")
        with self.assertRaises(InputError):
            public_url(url + "#fragment", source="efficientat")

    def test_atomic_pair_validates_both_hashes_and_stale_suite(self):
        p = {"value": 1}
        p["record_hash"] = digest(p)
        s = {"protocol_hash": p["record_hash"]}
        s["record_hash"] = digest(s)
        path = self.root / "manifests/evaluation/comparison.json"
        write_record(path, {"protocol": p, "suite": s}, self.mbudget())
        self.assertEqual(load_suite(self.mbudget()), (p, s))
        s["protocol_hash"] = "stale"
        s["record_hash"] = digest({k: v for k, v in s.items() if k != "record_hash"})
        write_record(path, {"protocol": p, "suite": s}, self.mbudget())
        with self.assertRaisesRegex(InputError, "mismatch"):
            comparison_pair(self.root)

    def test_fresh_protocol_uses_revised_rule_without_renderer_change(self):
        p = freeze(self.mbudget(), load_policy(self.root))
        self.assertIn("K=1 over", p["selection_rule"]["primary"])
        self.assertEqual(p["comparison_interval_policy"], POLICY)

    def test_held_out_refused_before_execution_or_ledger(self):
        with self.assertRaisesRegex(InputError, "refuses held-out"):
            run({"root": str(self.root), "split": "held_out"}, lambda _: self.fail("must not run"))
        self.assertFalse((self.root / "data/runs/matchers/ledger.json").exists())

    def test_prediction_stage_empty_and_stable_ties(self):
        p = {"record_hash": "p"}
        s = {"record_hash": "s"}
        value = prediction(
            p, s, "m", {}, [{"query_id": "q", "candidate": [], "refined": []}], kind="matcher"
        )
        self.assertEqual(value["queries"][0]["refined"], [])
        assets = {"z": {"audio": {"sample_count": 10}}, "a": {"audio": {"sample_count": 10}}}
        values = [{"asset_id": a, "start_frame": 0, "end_frame": 1, "score": 0} for a in ["z", "a"]]
        self.assertEqual(
            [v["asset_id"] for v in ranked(values, "lower_better", assets)], ["a", "z"]
        )

    def result(self, method, primary=0.5, secondary=0.5, seconds=1):
        groups = {}
        for name in [
            "source_consistency:-12",
            "source_consistency:0",
            "source_consistency:12",
            "performance",
            "pitch",
        ]:
            groups[name] = {
                "stages": {
                    "candidate": {
                        "at_k": {
                            "1": {"hit_rate": primary},
                            "5": {"hit_rate": secondary},
                            "10": {"hit_rate": 1},
                        }
                    }
                }
            }
        return {
            "status": "ok",
            "evidence_kind": "matcher",
            "provided_queries": 80,
            "expected_queries": 80,
            "conditions": groups,
            "model_cost": {"wall_seconds": seconds},
            "method_id": method,
            "config_hash": method,
        }

    def test_selection_primary_secondary_cost_lexical_and_none(self):
        a = self.result("a", primary=0.5, secondary=1, seconds=0.1)
        b = self.result("b", primary=0.6, secondary=0, seconds=100)
        self.assertEqual(choose([a, b])["method_id"], "b")
        b = self.result("b", primary=0.5, secondary=1, seconds=0.01)
        self.assertEqual(choose([a, b])["method_id"], "b")
        b = self.result("b", primary=0.5, secondary=1, seconds=0.1)
        self.assertEqual(choose([b, a])["method_id"], "a")
        self.assertIsNone(choose([]))
        self.assertEqual(criteria(a)["former_primary_hit_at_10"], 1)

    def test_incomplete_and_failed_runs_are_ineligible(self):
        for key, value in [
            ("status", "failed"),
            ("provided_queries", 79),
            ("evidence_kind", "harness_control"),
        ]:
            r = self.result("a")
            r[key] = value
            with self.assertRaises(InputError):
                criteria(r)

    def test_pilot_inference_truth_isolation_and_reuse(self):
        b = self.mbudget()
        build(b, load_policy(self.root), self.root / "data/runs/evaluation", pilot=True)
        p = record(self.root / "manifests/evaluation/protocol.json")
        s = record(self.root / "manifests/evaluation/pilot.json")
        assets = {
            k: record(self.root / "manifests/evaluation/assets" / (k + ".json"))
            for k in s["assets"]
        }
        frozen = {
            "record_hash": "frozen",
            "methods": {"acoustic": descriptor(self.root, "acoustic")},
        }
        result = run_batch(b, self.settings, p, s, assets, frozen, "acoustic")
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["queries"], 6)
        pred = record(self.root / "data/runs/matchers/acoustic-predictions.json")
        self.assertTrue(all(q["refined"] == [] for q in pred["queries"]))
        reused = run_batch(self.mbudget(), self.settings, p, s, assets, frozen, "acoustic")
        self.assertEqual(reused["reused_features"], 6)
        (self.root / "data/runs/matchers/acoustic-predictions.json").unlink()
        with self.assertRaises(FileNotFoundError):
            run_batch(self.mbudget(), self.settings, p, s, assets, frozen, "acoustic")

    def test_actual_memory_evidence_available(self):
        self.assertGreater(peak_memory(), 0)

    def test_offline_guard_refuses_network_and_restores_socket(self):
        import socket

        original = socket.socket.connect
        with offline_network():
            with socket.socket() as connection:
                with self.assertRaisesRegex(InputError, "network disabled"):
                    connection.connect(("127.0.0.1", 1))
        self.assertIs(socket.socket.connect, original)

    def test_bounded_coordinator_retains_failure_and_settles_time(self):
        calls = []

        def execute(request):
            calls.append(request)
            self.assertLessEqual(request["limits"]["max_seconds"], self.limits["max_seconds"])
            if len(calls) == 1:
                return {"status": "ok", "state": "in_progress"}
            return {"status": "failed", "error": "explicit model failure"}

        result = run(
            {"root": str(self.root), "split": "development", "limits": self.limits}, execute
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["ledger"]["pending_worker_seconds"], 0)

    def test_changed_checkpoint_invalidates_cached_feature(self):
        budget = self.mbudget()
        d = descriptor(self.root, "acoustic") | {"checkpoint": "original"}
        put(budget, self.settings, self.route(), d, Acoustic(), self.tone())
        self.assertIsNone(get(budget, self.route(), d | {"checkpoint": "changed"}))

    def test_feature_adapter_receives_no_routing_metadata(self):
        captured = []

        class Spy:
            def encode(self, samples, rate):
                captured.append((samples.copy(), rate))
                return np.zeros(56, dtype=np.float32)

        budget = self.mbudget()
        put(
            budget,
            self.settings,
            self.route(),
            descriptor(self.root, "acoustic"),
            Spy(),
            self.tone(),
        )
        self.assertEqual(len(captured), 1)
        np.testing.assert_array_equal(captured[0][0], self.tone())
        self.assertEqual(captured[0][1], 24000)

    def test_owned_feature_accounting_matches_full_inventory(self):
        from similar_sound_search.resources import Budget

        budget = self.mbudget()
        d = descriptor(self.root, "acoustic")
        put(budget, self.settings, self.route(), d, Acoustic(), self.tone())
        changed = self.route() | {"start_frame": 1}
        put(budget, self.settings, changed, d, Acoustic(), self.tone())
        self.assertEqual(budget.managed_bytes(), Budget(self.root, budget.limits).managed_bytes())

    def test_incomplete_published_run_cannot_be_selected(self):
        from similar_sound_search.matchers.selection import compare

        budget = self.mbudget()
        directory = self.root / "data/runs/matchers"
        write_record(
            directory / "acoustic-predictions.json", {"left_by_interruption": True}, budget
        )
        write_record(directory / "acoustic-progress.json", {"state": "in_progress"}, budget)
        stages = {"stages": {"candidate": {"at_k": {"1": {"hit_rate": 0}}}}}
        control = {
            "conditions": {"source_consistency:" + level: stages for level in ("-12", "0", "12")}
        }
        with patch(
            "similar_sound_search.matchers.selection.controls",
            return_value={"controls": {"constant": control, "random": control}},
        ):
            with patch(
                "similar_sound_search.matchers.selection.score",
                side_effect=AssertionError("must not score unsuccessful run"),
            ):
                result = compare(
                    budget,
                    {"record_hash": "p"},
                    {"record_hash": "s"},
                    {},
                    {"record_hash": "f", "methods": {"acoustic": {}}, "exclusions": {}},
                )
        self.assertIsNone(result["selected"])
        self.assertEqual(result["methods"]["acoustic"]["state"], "incomplete")
