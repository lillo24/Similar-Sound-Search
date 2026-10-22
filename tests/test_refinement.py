"""Isolated C03 native/support/objective/reuse/ownership/accounting checks."""

import copy
import shutil
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase

from similar_sound_search.cli import parser
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.refinement import development, engine, geometry, importing, report
from similar_sound_search.refinement.context import Context, Historical
from similar_sound_search.refinement.validation import known_answer
from similar_sound_search.resources import CatalogueBudget
from similar_sound_search.search.ranking import distances
from similar_sound_search.storage import InputError, ResourceError, digest, project_lock


class RefinementCase(AudioCase):
    def setUp(self):
        super().setUp()
        for name in ("refinement", "retrieval"):
            shutil.copyfile(REPOSITORY / f"config/{name}.json", self.root / f"config/{name}.json")
            (self.root / "manifests" / name).mkdir()
            shutil.copyfile(
                REPOSITORY / f"manifests/{name}/protocol.json",
                self.root / f"manifests/{name}/protocol.json",
            )
        self.owner = Context(self.root)

    def cbudget(self):
        return CatalogueBudget(self.root, {**self.limits, "max_working_bytes": 1024**3})

    def setup_local(self):
        x = np.arange(1000, dtype=np.float32)[:, None] / 1000
        source = {
            "recording_id": "r",
            "group": "g",
            "source": {
                "canonical_pcm": {"sha256": "pcm"},
                "sha256": "bytes",
                "sample_rate_hz": 100,
                "channels": 1,
            },
        }
        bounds = [100, 340]
        vector = np.array([1, np.mean(x[100:340])], np.float32)
        query = np.array([[1, np.mean(x[50:290])]], np.float32)
        per, _ = distances(query, vector[None], "cosine")
        anchor = {
            "original_bounds": bounds,
            "per_example_distances": per[:, 0].tolist(),
            "distance": float(per[0, 0]),
            "variant_id": "q",
            "event_id": "e",
            "recording_id": "r",
            "row_id": "old",
        }
        lookup = {("r", tuple(bounds)): {"vector": vector, "reference": {"row_id": "old"}}}
        return x, source, query, anchor, lookup

    def test_independent_native_and_scalar_oracle(self):
        self.assertTrue(known_answer()["passed"])

    def test_fractional_rate_rounding_and_finer_grid(self):
        grid = geometry.positions([44100, 149940], 400000, 44100, [-125, 0, 125])
        self.assertEqual([p[0] for p in grid], [38587, 44100, 49613])
        self.assertTrue(all(b - a == 105840 for a, b in grid))

    def test_start_tail_clamp_dedup_and_short_file(self):
        self.assertEqual(geometry.positions([0, 3], 3, 10, [-500, 0, 500]), [[0, 3]])
        self.assertEqual(geometry.positions([7, 10], 10, 10, [-500, 0, 500]), [[2, 5], [7, 10]])

    def test_bad_native_or_unbounded_grid_refused(self):
        for b in ([0, 0], [-1, 2], [1, 12], [True, 3]):
            with self.assertRaises(InputError):
                geometry.positions(b, 10, 10, [0])
        for offsets in ([1], [0, 501], list(range(10))):
            with self.assertRaises(InputError):
                geometry.positions([1, 3], 10, 10, offsets)

    def test_exact_original_tie_and_deterministic_displacement(self):
        b = [[0, 2], [1, 3], [2, 4]]
        self.assertEqual(geometry.choose(b, [1, 1, 1], [1, 3]), 1)
        self.assertEqual(geometry.choose(b, [0, 1, 0], [1, 3]), 0)

    def test_missing_control_and_nonfinite_fail(self):
        for values in ([float("nan")], [float("inf")]):
            with self.assertRaises(InputError):
                geometry.choose([[0, 2]], values, [0, 2])
        with self.assertRaises(InputError):
            geometry.choose([[0, 2]], [0], [1, 3])

    def test_event_variant_fixed_before_scoring(self):
        obj = geometry.objective(
            {"variant_id": "v", "event_id": "e"}, ["v", "w"], {"e": ["v", "w"]}
        )
        self.assertEqual(obj, {"kind": "variant", "variant": "v", "event": "e"})
        with self.assertRaises(InputError):
            geometry.objective({"variant_id": "w", "event_id": "e"}, ["v", "w"], {"e": ["v"]})

    def test_mean_and_single_event_are_distinct(self):
        q = np.eye(2, dtype=np.float32)
        per, mean = geometry.scores(q, q, {"kind": "mean"}, ["a", "b"])
        _, single = geometry.scores(q, q, {"kind": "variant", "variant": "b"}, ["a", "b"])
        np.testing.assert_array_equal(mean, [0.5, 0.5])
        np.testing.assert_array_equal(single, per[1])

    def test_native_feature_semantics_ignore_labels_and_change_with_bounds(self):
        _, s, _, _, _ = self.setup_local()
        before = digest(geometry.semantic(s, [0, 2], {"dimension": 2}))
        s["title"] = "new label"
        self.assertEqual(before, digest(geometry.semantic(s, [0, 2], {"dimension": 2})))
        self.assertNotEqual(before, digest(geometry.semantic(s, [1, 3], {"dimension": 2})))

    def test_candidate_lineage_separates_conditioning_and_source(self):
        _, s, _, _, _ = self.setup_local()
        q = {"record_hash": "q", "identity": {"excluded_groups": []}, "examples": []}
        self.assertEqual(geometry.lineage(s, q)["conditioning_query"], "q")
        q["identity"]["excluded_groups"] = ["g"]
        with self.assertRaises(InputError):
            geometry.lineage(s, q)

    def test_cue_cannot_masquerade_as_candidate(self):
        _, s, _, _, _ = self.setup_local()
        q = {"record_hash": "q", "identity": {"excluded_groups": []}, "examples": []}
        with self.assertRaises(InputError):
            geometry.lineage(s, q, {"canonical_pcm": {"sha256": "pcm"}})

    def test_original_local_features_and_atomic_recovery_without_reembedding(self):
        x, s, q, a, lookup = self.setup_local()

        class Model:
            calls = 0

            def encode(self, samples, rate):
                self.calls += 1
                return np.array([1, np.mean(samples)], np.float32)

        m = Model()
        with patch.object(self.owner, "model", return_value=m):
            result = engine.local(
                self.cbudget(),
                self.owner,
                s,
                x,
                a,
                q,
                ["q"],
                {"e": ["q"]},
                {"dimension": 2},
                lookup,
            )
            calls = m.calls
            _, _, _, _, lookup = self.setup_local()
            again = engine.local(
                self.cbudget(),
                self.owner,
                s,
                x,
                a,
                q,
                ["q"],
                {"e": ["q"]},
                {"dimension": 2},
                lookup,
            )
        self.assertEqual(m.calls, calls)
        self.assertEqual(result, again)
        self.assertTrue(result["selected"]["original_mixture_verified"])
        self.assertEqual(result["original_retained_alternate"], a)
        self.assertEqual(result["selected"]["original_bounds"], [50, 290])

    def test_zero_offset_only_preserves_original_distances(self):
        x, s, q, a, lookup = self.setup_local()
        self.owner.cfg["offset_milliseconds"] = [0]
        with patch.object(self.owner, "model") as model:
            r = engine.local(
                self.cbudget(),
                self.owner,
                s,
                x,
                a,
                q,
                ["q"],
                {"e": ["q"]},
                {"dimension": 2},
                lookup,
            )
        model.assert_not_called()
        self.assertFalse(r["changed"])
        self.assertEqual(r["control"]["original_bounds"], a["original_bounds"])
        self.assertEqual(r["control"]["distance"], a["distance"])

    def test_corrupt_original_control_refused(self):
        x, s, q, a, lookup = self.setup_local()
        self.owner.cfg["offset_milliseconds"] = [0]
        a["distance"] += 0.1
        with self.assertRaises(InputError):
            engine.local(
                self.cbudget(),
                self.owner,
                s,
                x,
                a,
                q,
                ["q"],
                {"e": ["q"]},
                {"dimension": 2},
                lookup,
            )

    def test_changed_feature_blob_refused_on_recovery(self):
        x, s, q, a, lookup = self.setup_local()
        with patch.object(self.owner, "model") as model:
            model.return_value.encode.return_value = np.array([1, 1], np.float32)
            r = engine.local(
                self.cbudget(),
                self.owner,
                s,
                x,
                a,
                q,
                ["q"],
                {"e": ["q"]},
                {"dimension": 2},
                lookup,
            )
        p = self.root / r["feature_bundle"]["path"] / "features.npy"
        p.write_bytes(b"corrupt")
        _, _, _, _, lookup = self.setup_local()
        with self.assertRaises(InputError):
            engine.local(
                self.cbudget(),
                self.owner,
                s,
                x,
                a,
                q,
                ["q"],
                {"e": ["q"]},
                {"dimension": 2},
                lookup,
            )

    def test_historical_view_never_publishes(self):
        old = Historical(self.owner)
        self.assertNotEqual(old.directory, self.owner.directory)
        with self.assertRaises(InputError):
            old.publish(self.cbudget(), old.directory / "x.json", {})

    def test_owned_immutable_compact_records_and_reference_containment(self):
        ref = self.owner.put(self.cbudget(), "groups", {"state": "failed", "reason": "missing"})
        self.assertEqual(self.owner.get(ref, "groups")["state"], "failed")
        with self.assertRaises(InputError):
            self.owner.get(ref, "sources")
        with self.assertRaises(InputError):
            self.owner.publish(self.cbudget(), self.root / "data/runs/retrieval/x.json", {})
        with self.assertRaises(InputError):
            self.owner.put(self.cbudget(), "groups", {"data": "x" * 1048576})

    def test_lifetime_budget_and_retry_charges_persist(self):
        self.owner.cfg["policy"]["max_feature_windows"] = 2
        self.owner.charge(self.cbudget(), feature_windows=2)
        with self.assertRaises(ResourceError):
            self.owner.charge(self.cbudget(), feature_windows=1)
        self.assertEqual(record(self.owner.directory / "work.json")["counts"]["feature_windows"], 2)

    def test_configuration_cannot_increase_allowance(self):
        cfg = copy.deepcopy(self.owner.cfg)
        cfg["policy"]["max_workers"] = 257
        self.json_file("config/refinement.json", cfg)
        with self.assertRaises(InputError):
            Context(self.root)

    def test_writer_exclusion(self):
        with project_lock(self.root, ".c03-worker.lock"), self.assertRaises(ResourceError):
            with project_lock(self.root, ".c03-worker.lock"):
                pass

    def test_explicit_pinned_shortlist_no_arm_substitution(self):
        for arm in (None, "legacy-mean"):
            with self.assertRaises(InputError):
                importing.shortlist(self.owner, self.owner.protocol["execution"], arm)

    def test_anchored_presentation_dedup_preserves_disjoint_and_all_evidence(self):
        a = [
            {"selected": {"recording_id": "r", "original_bounds": b}}
            for b in ([0, 10], [5, 15], [10, 20], [30, 40])
        ]
        out = geometry.deduplicate(a)
        self.assertEqual(len(out), 4)
        self.assertIsNone(out[2]["presentation_duplicate_of"])
        self.assertEqual(out[1]["presentation_duplicate_of"], 0)

    def test_metrics_separate_group_event_localization_and_missing_shortlist(self):
        case = {"positives": {"g": [{"recording_id": "r", "bounds": [[0, 10], [30, 40]]}]}}
        m = development.metrics(
            case,
            [{"group": "g", "rows": [{"recording_id": "r", "original_bounds": [0, 10]}]}],
            ["g"],
            10,
        )
        self.assertEqual(m["found_events"], 1)
        self.assertEqual(m["all_event_recall"], 0.5)
        self.assertTrue(m["hit"]["1"])

    def test_report_controls_and_original_roles_escape_text(self):
        c = {"path": "media/x.wav", "duration_seconds": 2, "rate": 10, "channels": 1, "gain": 1}
        p = report.page(
            {
                "items": [
                    {"clip": c, "label": "<script>", "role": "original", "timeline": "native"}
                ],
                "summary": {},
            }
        )
        self.assertIn("&lt;script&gt;", p)
        self.assertIn('id="seek-0"', p)
        self.assertIn('controls preload="metadata"', p)
        self.assertIn("Song order is unchanged", p)

    def test_cli_requires_explicit_arm_at_execution_boundary(self):
        args = parser().parse_args(
            [
                "refinement",
                "refine",
                "--arm",
                "event-multi",
                "--execution",
                "saved.json",
                "--receipt",
                "fresh.json",
            ]
        )
        self.assertEqual(args.arm, "event-multi")
