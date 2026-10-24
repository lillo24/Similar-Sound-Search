"""D02 independent metric oracles, native construction audits and finite-owner faults."""

import copy
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.storage import InputError, ResourceError, digest
from sound_search_evaluation import audit, contracts, dataset, scoring
from sound_search_evaluation.budget import CatalogueBudget as FastBudget
from sound_search_evaluation.context import MIB, Context
from sound_search_evaluation.runtime import category

ROOT = Path(__file__).resolve().parents[1]


class AssessmentTests(unittest.TestCase):
    def test_fresh_directory_entry_inventory_equals_standard_actual_inventory(self):
        for name in (
            "data/old/a.bin",
            "data/new/nested/b.bin",
            "reports/local/c.bin",
            "manifests/queries/d.bin",
        ):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(name.encode() * 23)
        fast = FastBudget(self.root, self.budget.limits)
        self.assertEqual(fast.managed_bytes(), self.budget.managed_bytes())
        extra = self.root / "data/new/z.bin"
        extra.write_bytes(b"actual new file")
        fresh = FastBudget(self.root, self.budget.limits)
        self.assertEqual(fresh.managed_bytes(), fast.managed_bytes() + len(b"actual new file"))

    def test_assessment_lossless_bounded_storage_and_oversized_refusal(self):
        value = dict(
            schema_version="d02-scores-1",
            cases=[dict(notes="a" * (2 * MIB), score=0.12345678912345678)],
        )
        ref = self.owner.put(self.budget, "assessments", value)
        restored = self.owner.get(ref, "assessments")
        self.assertEqual({k: v for k, v in restored.items() if k != "record_hash"}, value)
        self.assertLess((self.root / ref["path"]).stat().st_size, MIB)
        with self.assertRaises(InputError):
            self.owner.put(
                self.budget,
                "assessments",
                dict(schema_version="d02-scores-1", notes="x" * (8 * MIB)),
            )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("config/assessment.json", "manifests/assessment/protocol.json"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.owner = Context(self.root, "test")
        self.owner.admit("test", 20 * MIB, acceptance=True)
        self.owner.job_id = "a" * 64
        limits = load_limits(ROOT / "config/resource_limits.json", "starter")
        limits["min_free_bytes"] = 1
        self.budget = CatalogueBudget(self.root, limits)

    def test_independent_pool_and_lifetime_limits(self):
        self.owner.charge(self.budget, feature_windows=1, query_jobs=1)
        self.assertEqual(self.owner.pool()["schema_version"], "d02-pool-1")
        self.assertFalse((self.root / "data/runs/application/pool.json").exists())
        with self.assertRaises(ResourceError):
            self.owner.charge(self.budget, feature_windows=4096)
        self.assertEqual(self.owner.pool()["counts"]["feature_windows"], 1)

    def test_failed_attempt_is_retained_and_job_id_is_actual(self):
        self.owner.reserve_attempt("worker")
        self.assertEqual(self.owner.pool()["attempts"]["worker"]["job_id"], self.owner.job_id)
        self.owner.terminal(
            "worker", self.owner.directory / "failure.json", dict(state="failed"), uncertain=True
        )
        self.assertEqual(self.owner.pool()["counts"]["job_seconds"], 120)
        before = self.owner.pool()
        self.owner.terminal(
            "worker", self.owner.directory / "failure.json", dict(state="failed"), uncertain=True
        )
        self.assertEqual(before, self.owner.pool())

    def test_initial_claim_refuses_unbounded_fresh_jobs_and_exact_resume_reuses(self):
        first = contracts.claim(self.owner, self.budget, "case")
        self.assertEqual(first, contracts.claim(self.owner, self.budget, "case"))
        self.owner.job_id = "b" * 64
        self.assertEqual(category(self.owner, "case"), "technical")
        with self.assertRaises(ResourceError):
            contracts.claim(self.owner, self.budget, "case")
        for i in range(4):
            self.owner.job_id = digest(i)
            contracts.claim(self.owner, self.budget, "case", "technical")
        self.owner.job_id = digest(99)
        with self.assertRaises(ResourceError):
            contracts.claim(self.owner, self.budget, "case", "technical")

    def test_protected_terminal_survives_ordinary_exhaustion(self):
        self.owner.reserve_attempt("reserved")
        n = self.owner.pool()["allocations"]["test"]["remaining"]
        self.owner.charge(self.budget, metadata_bytes=n - 16384)
        with self.assertRaises(ResourceError):
            self.owner.put(self.budget, "bad", dict(x=1))
        self.owner.terminal(
            "reserved", self.owner.directory / "terminal.json", dict(state="blocked"), elapsed=2
        )
        self.assertEqual(record(self.owner.directory / "terminal.json")["state"], "blocked")

    def test_stereo_and_short_emitted_pcm_audits_and_corruption(self):
        cfg = self.owner.protocol["splits"]["development"]
        for i in (4, 5):
            spec = cfg["sources"][i]
            samples, _ = dataset.components(cfg["families"], spec)
            path = self.owner.audio / (str(i) + ".wav")
            dataset.write_audio(self.budget, self.owner, path, samples, spec["rate"])
            answer = audit.check_audio(self.budget, self.owner, path, cfg["families"], spec)
            self.assertEqual(answer["channels"], spec["channels"])
            self.assertEqual(answer["frames"], round(spec["duration_seconds"] * spec["rate"]))
            bad = copy.deepcopy(spec)
            bad["ratio_db"] += 1
            with self.assertRaises(InputError):
                audit.check_audio(self.budget, self.owner, path, cfg["families"], bad)

    def test_independent_performances_and_genuine_duplicate(self):
        cfg = self.owner.protocol["splits"]["development"]
        a = dataset.performance(cfg["families"][0], cfg["sources"][0])
        b = dataset.performance(cfg["families"][0], cfg["sources"][1])
        self.assertFalse(np.array_equal(a, b))
        self.assertEqual(cfg["sources"][31]["duplicate_of"], 24)
        self.assertEqual(cfg["sources"][31]["group"], cfg["sources"][24]["group"])

    def test_full_prospective_matrix_and_disjoint_seeds(self):
        p = self.owner.protocol
        self.assertEqual(
            [len(p["splits"][s]["cases"]) for s in ("development", "confirmation")], [24, 16]
        )
        seeds = [
            {x["performance_seed"] for x in p["splits"][s]["sources"]}
            for s in ("development", "confirmation")
        ]
        self.assertFalse(seeds[0] & seeds[1])


def truth():
    return dict(
        primary=True,
        families=[0],
        condition="normal",
        positive_groups=["g1", "g2"],
        events=[
            dict(recording_id="s1", group="g1", bounds=[10, 20], rate=10),
            dict(recording_id="s1", group="g1", bounds=[30, 40], rate=10),
        ],
    )


def group(key="g1", bounds=(10, 20), rank=1):
    return dict(
        group=key,
        rank=rank,
        passages=[dict(asset_id="s1", start_frame=bounds[0], end_frame=bounds[1])],
    )


class ScoringOracles(unittest.TestCase):
    def test_complete_ranking_duplicate_group_rank_score_and_bounds_oracles(self):
        from unittest.mock import patch

        sources = [
            dict(recording_id=str(i), group=str(i), source=dict(sample_count=100))
            for i in range(31)
        ]
        pop = dict(record_hash="pop", sources=sources)
        values = {
            str(i): dict(
                group=str(i),
                rank=i + 1,
                score=i,
                grouping={},
                support_truncated=False,
                passages=[
                    dict(
                        scored_bounds=[10, 20],
                        representative=dict(
                            recording_id=str(i), original_bounds=[10, 20], original_context=[0, 30]
                        ),
                    )
                ],
            )
            for i in range(31)
        }

        class Owner:
            protocol = {"record_hash": "p"}
            split = "development"

            def get(self, ref, kind):
                return dict(query=dict(record_hash="q")) if kind == "queries" else values[ref]

        pred = dict(
            state="complete",
            population="pop",
            protocol="p",
            split="development",
            query={},
            query_hash="q",
            excluded_groups=[],
            arms={
                a: dict(
                    eligible_groups=31,
                    complete_groups=list(values),
                    shortlist=list(values)[:20],
                    display=list(values)[:10],
                )
                for a in scoring.ARMS
            },
        )
        # Event-multi's direction is reversed in this deliberately invalid oracle.
        with patch.object(contracts, "population", return_value=pop), self.assertRaises(InputError):
            scoring.validate_prediction(Owner(), pred)
        for a in ("group", "rank", "score", "bounds"):
            original = copy.deepcopy(values)
            if a == "group":
                values["1"]["group"] = "0"
            if a == "rank":
                values["1"]["rank"] = 1
            if a == "score":
                values["1"]["score"] = float("nan")
            if a == "bounds":
                values["1"]["passages"][0]["scored_bounds"] = [20, 10]
            with (
                self.subTest(a=a),
                patch.object(contracts, "population", return_value=pop),
                self.assertRaises(InputError),
            ):
                scoring.validate_prediction(Owner(), pred)
            values = original

    def test_group_hit_is_not_all_positive_recall_or_event_recall(self):
        result = scoring.case_metrics([group()], truth())["1"]
        self.assertTrue(result["query_hit"])
        self.assertEqual(result["all_positive_group_recall"], 0.5)
        self.assertEqual(result["event_recall"], 0.5)
        self.assertEqual(result["misses"], [1])

    def test_one_prediction_never_recovers_two_events(self):
        t = truth()
        t["events"][1]["bounds"] = [15, 25]
        self.assertEqual(
            scoring.case_metrics([group(bounds=(10, 25))], t)["10"]["matched_events"], 1
        )

    def test_coverage_and_iou_are_separate_with_misses(self):
        m = scoring.case_metrics([group(bounds=(0, 40))], truth())["10"]
        self.assertEqual(m["event_recall"], 0)
        self.assertEqual(m["truth_coverage_recall"], 0.5)
        self.assertEqual(len(m["misses"]), 2)

    def test_native_interval_malformed_reversed_and_outside_oracles(self):
        source = dict(recording_id="s1", source=dict(sample_count=100))
        for b in ([], [1], [1, 2, 3], [-1, 2], [4, 4], [5, 4], [1, 101], [True, 4], [1.0, 4]):
            with self.subTest(b=b), self.assertRaises(InputError):
                scoring.interval(source, b)

    def cases(self, before, after):
        t = truth()
        return [
            dict(
                case_id="case",
                primary=True,
                families=[0],
                condition="normal",
                arms={
                    "legacy-mean": scoring.case_metrics(before, t),
                    "event-multi": scoring.case_metrics(after, t),
                },
            )
        ]

    def test_gate_tie_does_not_promote(self):
        self.assertFalse(scoring.gate(self.cases([group()], [group()]))["passed"])

    def test_gate_strict_gain_and_validity(self):
        cs = self.cases([group("g3", (60, 70))], [group()])
        self.assertTrue(scoring.gate(cs)["passed"])
        self.assertFalse(scoring.gate(cs, False)["passed"])

    def test_gate_newly_lost_positive_group_blocks_even_aggregate_gain(self):
        cs = self.cases([group("g2", (60, 70))], [group()])
        self.assertFalse(scoring.gate(cs)["passed"])
        self.assertEqual(scoring.gate(cs)["coverage_regressions"][0]["newly_lost_groups"], ["g2"])

    def test_constant_and_random_controls_are_seeded_same_population(self):
        groups = [group("g" + str(i)) for i in range(31)]
        first = scoring.ordering_controls(groups, truth(), "case")
        self.assertEqual(first, scoring.ordering_controls(list(reversed(groups)), truth(), "case"))

    def test_missing_ranking_is_a_failure_not_empty_success(self):
        class Owner:
            protocol = {"record_hash": "p"}
            split = "development"

            def get(self, ref, kind):
                return dict(query=dict(record_hash="q"))

        # Only the metadata reader is replaced by a pure in-memory oracle. This
        # test never runs a model and supplies no real evaluation evidence.
        from unittest.mock import patch

        pop = dict(
            record_hash="pop", sources=[dict(recording_id=str(i), group=str(i)) for i in range(31)]
        )
        pred = dict(
            state="complete",
            population="pop",
            protocol="p",
            split="development",
            query={},
            query_hash="q",
            excluded_groups=[],
            arms={
                a: dict(eligible_groups=31, complete_groups=[], shortlist=[], display=[])
                for a in scoring.ARMS
            },
        )
        with patch.object(contracts, "population", return_value=pop), self.assertRaises(InputError):
            scoring.validate_prediction(Owner(), pred)


if __name__ == "__main__":
    unittest.main()
