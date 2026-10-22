"""Isolated C02 scalar, ownership, exact scan, support, corruption and accounting tests."""

import json
import shutil
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase

from similar_sound_search.cli import parser
from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.resources import CatalogueBudget
from similar_sound_search.retrieval import development, engine, fusion, history, report, validation
from similar_sound_search.retrieval.context import Context, DerivedQueryContext, QueryView
from similar_sound_search.retrieval.job import run
from similar_sound_search.search.ranking import distances
from similar_sound_search.storage import InputError, ResourceError, digest, project_lock


class RetrievalCase(AudioCase):
    def setUp(self):
        super().setUp()
        for name in ("retrieval", "indexing", "queries", "separation", "search"):
            shutil.copyfile(REPOSITORY / f"config/{name}.json", self.root / f"config/{name}.json")
        for name in ("retrieval", "indexing"):
            (self.root / "manifests" / name).mkdir()
            shutil.copyfile(
                REPOSITORY / f"manifests/{name}/protocol.json",
                self.root / f"manifests/{name}/protocol.json",
            )
        self.owner = Context(self.root)
        self.cfg = self.owner.cfg

    def sbudget(self):
        return CatalogueBudget(self.root, self.limits)

    def row(self, name, start, end, **extra):
        return {
            "row_id": name,
            "recording_id": "r",
            "original_bounds": [start, end],
            "bank_hash": "b",
            "rate": 10,
            "credit": 1.0,
            "distance": 0.0,
            "variant_id": "q",
            **extra,
        }

    def test_scalar_known_answer_and_recovery(self):
        self.assertTrue(validation.known_answer()["passed"])

    def test_unique_events_ignore_order_and_exact_duplicates(self):
        self.assertEqual(fusion.events(["b", "a", "a"]), fusion.events(["a", "b"]))

    def test_correlated_variants_have_one_event(self):
        witness = {"source_pcm": "pcm", "native_bounds": [1, 11], "rate": 10}
        grouped = fusion.events(["h", "o", "h"], {"h": witness, "o": witness})
        self.assertEqual(list(grouped.values()), [["h", "o"]])

    def test_association_requires_all_variants_and_valid_native_bounds(self):
        with self.assertRaises(InputError):
            fusion.events(["a", "b"], {"a": {}})
        for bounds in ([4, 4], [-1, 3], [False, 5]):
            with self.assertRaises(InputError):
                fusion.events(
                    ["a"], {"a": {"source_pcm": "p", "native_bounds": bounds, "rate": 10}}
                )

    def test_silence_and_nonfinite_cosine_are_explicit_errors(self):
        for x in (np.zeros((1, 2)), np.asarray([[np.nan, 1.0]])):
            with self.assertRaises(InputError):
                distances(x, np.ones((1, 2)), "cosine")

    def test_retention_cap_and_traversal_order(self):
        rows = [self.row(str(n), n, n + 10, distance=n / 100) for n in range(40)]
        self.assertEqual(fusion.retain(rows, 16), fusion.retain(list(reversed(rows)), 16))
        self.assertEqual(len(fusion.retain(rows + rows, 16)), 16)

    def test_retention_rejects_corrupt_conflicting_and_nan_rows(self):
        r = self.row("a", 0, 10)
        with self.assertRaises(InputError):
            fusion.retain([r, {**r, "distance": 1}], 16)
        with self.assertRaises(InputError):
            fusion.retain([{**r, "distance": float("nan")}], 16)

    def test_containment_and_context_are_not_scored_envelopes(self):
        a = self.row("a", 5, 15)
        b = self.row("b", 0, 20, distance=0.1)
        clusters, _ = fusion.consolidate([a, b], self.cfg)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["scored_bounds"], [5, 15])
        self.assertEqual(clusters[0]["display_envelope"], [0, 20])
        self.assertFalse(clusters[0]["envelope_is_scored"])

    def test_adjacent_and_different_recordings_never_merge(self):
        rows = [
            self.row("a", 0, 10),
            self.row("b", 10, 20),
            self.row("c", 0, 10, recording_id="other"),
        ]
        clusters, _ = fusion.consolidate(rows, self.cfg)
        self.assertEqual(len(clusters), 3)

    def test_chain_does_not_expand_anchor(self):
        rows = [self.row(str(n), v, v + 10) for n, v in enumerate([0, 5, 10])]
        clusters, info = fusion.consolidate(rows, self.cfg)
        self.assertEqual(info["clusters"], 2)
        self.assertEqual([v["scored_bounds"] for v in clusters], [[0, 10], [10, 20]])

    def test_maximum_cluster_span_and_three_passage_cap(self):
        rows = [self.row(str(n), n * 100, n * 100 + 20) for n in range(5)]
        result, info = fusion.consolidate(rows, self.cfg)
        self.assertEqual(len(result), 3)
        self.assertEqual(info["discarded_clusters"], 2)
        rows = [self.row("a", 0, 60), self.row("b", 30, 90)]
        _, info = fusion.consolidate(rows, self.cfg)
        self.assertEqual(info["clusters"], 2)

    def test_grouping_is_invariant_to_duplicates_and_traversal(self):
        rows = [self.row(str(n), v, v + 10) for n, v in enumerate([0, 5, 10, 40])]
        expected = fusion.consolidate(rows, self.cfg)
        self.assertEqual(expected, fusion.consolidate(list(reversed(rows)) + rows, self.cfg))

    def test_duplicate_bank_references_and_opportunities_do_not_multiply_credits(self):
        groups, events = validation.oracle_fixture()
        a = fusion.results(groups, events, ["legacy"], self.cfg, "event-multi")
        groups["needed"]["opportunities"]["legacy"] = 100000
        b = fusion.results(groups, events, ["legacy", "legacy"], self.cfg, "event-multi")
        self.assertEqual(
            [(r["group"], r["score"]) for r in a], [(r["group"], r["score"]) for r in b]
        )

    def test_missing_bank_is_not_zero_distance_or_negative_label(self):
        groups, events = validation.oracle_fixture()
        with self.assertRaisesRegex(InputError, "missing"):
            fusion.results(groups, events, ["legacy", "missing"], self.cfg, "event-multi")

    def test_alternative_variants_maximum_not_sum(self):
        groups, _ = validation.oracle_fixture()
        ranking = fusion.results(groups, {"one": ["a", "b"]}, ["legacy"], self.cfg, "event-multi")
        self.assertEqual(ranking[0]["score"], 1)
        self.assertEqual(sum("event_credit" in c for c in ranking[0]["contributions"]), 1)

    def test_no_eligible_groups_is_genuine_empty_state(self):
        self.assertEqual(fusion.results({}, {"q": ["q"]}, ["b"], self.cfg, "event-multi"), [])

    def test_c02_configuration_cannot_increase_allowance(self):
        p = self.root / "config/retrieval.json"
        value = json.loads(p.read_text())
        value["policy"]["max_workers"] = 257
        p.write_text(json.dumps(value))
        with self.assertRaisesRegex(InputError, "ceiling"):
            Context(self.root)

    def test_immutable_compact_refs_preserve_hash_and_reject_changed_data(self):
        ref = self.owner.put(self.sbudget(), "test", {"x": 1})
        self.assertEqual(self.owner.get(ref, "test")["x"], 1)
        with self.assertRaises(InputError):
            self.owner.get({**ref, "record_hash": "0" * 64}, "test")
        with self.assertRaises(InputError):
            self.owner.publish(self.sbudget(), self.root / ref["path"], {"x": 2}, immutable=True)

    def test_compact_record_limit_and_path_containment(self):
        with self.assertRaisesRegex(InputError, "1 MiB"):
            self.owner.put(self.sbudget(), "test", {"too_big": "x" * 1048576})
        with self.assertRaises(InputError):
            self.owner.publish(self.sbudget(), self.root / "data/runs/indexing/forbidden.json", {})

    def test_read_only_history_keeps_c01_paths_and_c02_debits(self):
        view = history.BankView(self.owner)
        self.assertEqual(view.directory, self.root / "data/runs/indexing")
        view.charge(self.sbudget(), read_audio_seconds=3)
        self.assertEqual(
            record(self.owner.directory / "work.json")["counts"]["read_audio_seconds"], 3
        )
        self.assertFalse((view.directory / "work.json").exists())
        with self.assertRaises(InputError):
            view.publish(None, None, None)

    def test_query_views_and_derivatives_use_explicit_roots(self):
        old = QueryView(self.owner)
        new = DerivedQueryContext(self.owner)
        self.assertEqual(old.directory, self.root / "data/runs/queries")
        self.assertEqual(new.directory, self.owner.directory / "query-derived")
        self.assertEqual(new.feature_root, self.owner.features / "queries")
        with self.assertRaisesRegex(InputError, "retrieval derive-query"):
            old.publish(None, None, None)
        old.charge(self.sbudget(), read_audio_seconds=5)
        self.assertFalse((old.directory / "work.json").exists())

    def test_cli_has_owned_modes_and_historical_defaults(self):
        p = parser()
        self.assertEqual(p.parse_args(["retrieval", "serve", "x"]).port, 8771)
        self.assertEqual(p.parse_args(["indexing", "serve", "x"]).port, 8770)
        self.assertEqual(p.parse_args(["queries", "serve", "x"]).port, 8769)

    def test_concurrent_worker_lock_refused(self):
        with project_lock(self.root, ".c02-worker.lock"):
            with self.assertRaises(InputError):
                with project_lock(self.root, ".c02-worker.lock"):
                    pass

    def test_failed_workers_and_restarts_retain_lifetime_counts(self):
        request = {
            "root": str(self.root),
            "limits": self.limits,
            "retrieval_action": "known-answer",
        }
        for _ in range(2):
            result = run(request, lambda req: {"status": "failed", "error": "fixture failure"})
        self.assertEqual(result["work"]["counts"]["workers"], 2)
        self.assertGreater(result["ledger"]["charged_worker_seconds"], 0)

    def test_read_reservations_survive_refusal(self):
        self.owner.charge(self.sbudget(), read_audio_seconds=119999)
        with self.assertRaises(ResourceError):
            self.owner.charge(self.sbudget(), read_audio_seconds=2)
        self.assertEqual(
            record(self.owner.directory / "work.json")["counts"]["read_audio_seconds"], 119999
        )

    def test_scored_and_passage_coverage_differ(self):
        case = {"positives": {"g": [{"recording_id": "r", "bounds": [[100, 200]]}]}}
        ranking = [{"group": "g", "passages": [{"representative": self.row("wrong", 0, 10)}]}]
        metric = development.coverage(ranking, case, 20, self.cfg)
        self.assertTrue(metric["hit_at_least_one"])
        self.assertFalse(metric["passage_hit"])
        empty = development.coverage(ranking, {"positives": {}}, 20, self.cfg)
        self.assertIsNone(empty["hit_at_least_one"])

    def test_complete_scan_preserves_mean_baseline_and_per_event_rows(self):
        source = {
            "recording_id": "r",
            "group": "g",
            "source": {
                "sample_rate_hz": 10,
                "sample_count": 100,
                "sha256": "source",
                "canonical_pcm": {"sha256": "sourcepcm"},
            },
            "offset": None,
            "offset_evidence": None,
        }
        banks = [
            {
                "value": {
                    "signals": {"r": {"original": source}},
                    "committed": [{"signal_id": "r"}],
                },
                "binding": {"historical_bank_hash": key},
            }
            for key in ("legacy", "long")
        ]
        query = {
            "identity": {"excluded_groups": []},
            "examples": [
                {
                    "audio": {"duration_seconds": 1},
                    "prepared": {
                        "source": {"sha256": "query"},
                        "technical_metadata": {"canonical_pcm": {"sha256": "querypcm"}},
                    },
                }
            ]
            * 2,
        }
        passages = [{"row_id": str(n), "original_bounds": [n * 30, n * 30 + 10]} for n in range(2)]
        with (
            patch.object(engine.sources, "load") as load,
            patch.object(
                engine.reader, "rows", return_value=(np.eye(2, dtype=np.float32), passages)
            ),
        ):
            result = engine.scan(
                self.sbudget(),
                self.owner,
                None,
                banks,
                query,
                np.eye(2, dtype=np.float32),
                "r",
                ["a", "b"],
            )
        self.assertEqual(load.call_count, 1)
        self.assertEqual(result["baseline"]["per_example_distances"], [0, 1])
        self.assertEqual(result["objectives"]["legacy:b"]["rows"][0]["original_bounds"], [30, 40])
        self.assertEqual(result["opportunities"], {"legacy": 2, "long": 2})

    def test_excluded_parent_never_scores_and_is_retained(self):
        source = {"recording_id": "r", "group": "parent", "source": {}}
        banks = [{"value": {"signals": {"r": {"original": source}}}}]
        with patch.object(engine.sources, "load"), patch.object(engine.reader, "rows") as rows:
            value = engine.scan(
                self.sbudget(),
                self.owner,
                None,
                banks,
                {"identity": {"excluded_groups": ["parent"]}},
                np.eye(1),
                "r",
                ["a"],
            )
        self.assertTrue(value["excluded"])
        rows.assert_not_called()

    def test_grouping_duplicate_sources_before_track_cut(self):
        groups, events = validation.oracle_fixture()
        ranking = fusion.results(groups, events, ["legacy"], self.cfg, "event-legacy")
        self.assertEqual(len({v["group"] for v in ranking[:20]}), 20)
        self.assertEqual(len(ranking), 33)

    def test_generated_native_recipe_and_independent_fft_inputs(self):
        preset = next(
            p for p in development.rendering.presets(42104) if p["split"] == "development"
        )
        spec = {
            "frames": 80000,
            "background_seed": 9,
            "parts": [{"preset": preset, "phrase": 0, "pitch": 0, "seed": 4, "first": 1234}],
        }
        a, b, parts = development.reconstruct(spec, 24000)
        target = np.zeros(80000)
        target[1234 : 1234 + len(parts[0][1])] = parts[0][1]
        np.testing.assert_allclose(a - b, target, atol=1e-15)

    def test_feature_recovery_does_not_reembed_and_changed_array_fails(self):
        class Model:
            calls = 0

            def encode(self, x, rate):
                self.calls += 1
                return np.asarray([1, 2], np.float32)

        model = Model()
        desc = {"dimension": 2}
        identity = {
            "dimension": 2,
            "representation": desc,
            "bounds": [[0, 10]],
            "producer": {"fixture": True},
        }

        def encoding_budget():
            return CatalogueBudget(self.root, {**self.limits, "max_working_bytes": 1024**3})

        with patch.object(self.owner, "model", return_value=model):
            a = development.encode(encoding_budget(), self.owner, identity, np.ones((10, 1)), 10)
            b = development.encode(encoding_budget(), self.owner, identity, np.ones((10, 1)), 10)
        self.assertEqual(a, b)
        self.assertEqual(model.calls, 1)
        path = self.owner.features / "development" / digest(identity) / "features.npy"
        path.write_bytes(b"corrupt")
        with self.assertRaises(InputError):
            development.encode(self.sbudget(), self.owner, identity, np.ones((10, 1)), 10)

    def test_report_page_escapes_text_and_preserves_control_roles(self):
        c = {"path": "media/x.wav", "duration_seconds": 2, "rate": 10, "channels": 1, "gain": 1}
        value = {
            "summary": {},
            "items": [
                {
                    "label": "<script>",
                    "role": "Actual scored original",
                    "timeline": "1–3",
                    "clip": c,
                    "evidence": {"scored_bounds": [10, 30]},
                }
            ],
        }
        page = report.page(value)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn('id="audio-0"', page)
        self.assertIn('id="seek-0"', page)
        self.assertIn("envelopes are separate and", page)

    def test_interrupted_scan_resumes_only_uncommitted_sources_and_charges_once(self):
        signals = {str(n): {} for n in range(5)}
        bank = {
            "value": {
                "signals": signals,
                "bank": {"identity": {"representation": {"distance": "cosine"}}},
            },
            "binding": {"historical_bank_hash": "legacy"},
        }
        query = {
            "record_hash": "query",
            "feature_hash": "feature",
            "identity": {"representation": {"distance": "cosine"}},
            "examples": [{"example_id": "a"}],
        }
        calls = []
        failed = False

        def scan(*args):
            nonlocal failed
            source = args[-2]
            calls.append(source)
            if source == "2" and not failed:
                failed = True
                raise InputError("fixture interrupted source")
            return {"source_id": source}

        request = {"receipt": str(self.root / "receipt.json")}
        with (
            patch.object(
                engine.history,
                "open_snapshot",
                return_value=({"record_hash": "snapshot"}, None, [bank]),
            ),
            patch.object(
                engine,
                "load_query",
                return_value=(
                    {"revision_id": "r"},
                    {"materialization_id": "m"},
                    query,
                    np.ones((1, 2)),
                ),
            ),
            patch.object(engine.compatibility, "audit", return_value={"fixture": True}),
            patch.object(engine, "scan", side_effect=scan),
            patch.object(
                engine, "finish", return_value={"status": "ok", "state": "complete"}
            ) as finish,
        ):
            with self.assertRaisesRegex(InputError, "interrupted"):
                engine.step(request, self.sbudget(), self.owner)
            progress = record(next((self.owner.directory / "progress").glob("*.json")))
            self.assertEqual(len(progress["sources"]), 2)
            self.assertEqual(len(progress["failed_attempts"]), 1)
            self.assertEqual(engine.step(request, self.sbudget(), self.owner)["state"], "complete")
            self.assertEqual(len(finish.call_args.args[4]), 5)
        self.assertEqual(calls, ["0", "1", "2", "2", "3", "4"])
        self.assertEqual(record(self.owner.directory / "work.json")["counts"]["query_jobs"], 3)

    def test_stale_reuse_consumer_fails_before_source_reads(self):
        ref = self.owner.put(
            self.sbudget(), "executions", {"identity": {"consumer_code": {"stale": True}}}
        )
        self.owner.publish(
            self.sbudget(), self.owner.directory / "execution.json", {"execution": ref}
        )
        with patch.object(engine.sources, "load") as load:
            with self.assertRaisesRegex(InputError, "consumer code changed"):
                engine.verify({"receipt": "unused"}, self.sbudget(), self.owner)
        load.assert_not_called()

    def test_c03_export_keeps_all_groups_before_twenty_and_ten(self):
        groups, event_map = validation.oracle_fixture()
        values = []
        for group, v in groups.items():
            values.append(
                {
                    **v,
                    "group": group,
                    "source_id": group,
                    "excluded": False,
                    "source_ref": {"fixture_source": group},
                }
            )
        winners = sorted(
            (v["baseline"] for v in groups.values()),
            key=lambda v: (
                v["timbre_distance"],
                v["recording_id"],
                v["start_frame"],
                v["end_frame"],
            ),
        )
        query = {"record_hash": "q", "identity": {"excluded_groups": []}}
        target = (
            self.root
            / "data/runs/indexing/executions"
            / (self.owner.protocol["delivery"]["baseline_execution"] + ".json")
        )
        write_record(
            target,
            {"query": {"record_hash": "q"}, "winners": winners, "excluded_groups": []},
            self.sbudget(),
        )
        result = engine.finish(
            self.sbudget(),
            self.owner,
            {"fixture": True},
            query,
            values,
            [{"binding": {"historical_bank_hash": "legacy"}}],
            event_map,
        )
        exported = self.owner.get(
            record(self.owner.directory / "execution.json")["execution"], "executions"
        )
        for arm in exported["arms"].values():
            self.assertEqual(len(arm["complete_groups"]), 33)
            self.assertEqual(len(arm["shortlist"]), 20)
            self.assertEqual(len(arm["display"]), 10)
        proof = self.owner.get(exported["baseline_winners"], "baseline-winners")
        self.assertEqual(proof["winners"], winners)
        self.assertTrue(result["baseline_equivalence"])

    def test_complete_winner_equivalence_rejects_changed_secondary_group(self):
        groups, event_map = validation.oracle_fixture()
        values = [
            {**v, "group": g, "source_id": g, "excluded": False, "source_ref": {"fixture": g}}
            for g, v in groups.items()
        ]
        query = {"record_hash": "q", "identity": {"excluded_groups": []}}
        target = (
            self.root
            / "data/runs/indexing/executions"
            / (self.owner.protocol["delivery"]["baseline_execution"] + ".json")
        )
        write_record(
            target,
            {"query": {"record_hash": "q"}, "winners": [], "excluded_groups": []},
            self.sbudget(),
        )
        with self.assertRaisesRegex(InputError, "complete baseline equivalence"):
            engine.finish(
                self.sbudget(),
                self.owner,
                {},
                query,
                values,
                [{"binding": {"historical_bank_hash": "legacy"}}],
                event_map,
            )

    def test_shortlist_api_rejects_interrupted_execution_and_corrupt_group_reference(self):
        ref = self.owner.put(
            self.sbudget(),
            "executions",
            {"schema_version": "c02-c03-shortlist-1", "state": "pending", "arms": {}},
        )
        with self.assertRaisesRegex(InputError, "complete"):
            engine.read_shortlist(self.owner, ref)
        value = {
            "schema_version": "c02-c03-shortlist-1",
            "state": "complete",
            "identity": {"policy": self.cfg},
            "arms": {
                "legacy-mean": {
                    "shortlist": [
                        {
                            "path": "data/runs/retrieval/c03-groups/missing.json",
                            "record_hash": "missing",
                        }
                    ]
                }
            },
        }
        ref = self.owner.put(self.sbudget(), "executions", value)
        with self.assertRaises(FileNotFoundError):
            engine.read_shortlist(self.owner, ref)

    def test_compact_feature_reference_recovers_exact_metadata_and_refuses_path_changes(self):
        ref = {
            "path": "data/features/retrieval/fixture",
            "metadata": {"identity": {"fixture": True}},
            "example_id": "pcm",
        }
        compact = development.compact_ref(self.sbudget(), self.owner, ref)
        self.assertNotIn("metadata", compact)
        self.assertEqual(
            development.encoding_record(self.owner, compact)["metadata"], ref["metadata"]
        )
        self.assertEqual(compact["example_id"], "pcm")
        with self.assertRaisesRegex(InputError, "path differs"):
            development.encoding_record(self.owner, {**compact, "path": "different"})

    def test_audited_metadata_repair_keeps_original_feature_producer(self):
        shutil.copyfile(
            REPOSITORY / "manifests/retrieval/metadata-integration.json",
            self.root / "manifests/retrieval/metadata-integration.json",
        )
        proof = record(self.root / "manifests/retrieval/metadata-integration.json")
        # This historical repair binds its exact C02 consumer, not whichever later
        # stage happens to run the suite. Keep the production stale-code guard intact.
        with patch(
            "similar_sound_search.search.contracts.code_identity",
            return_value=proof["consumer_code"],
        ):
            self.assertEqual(development.producing_code(self.owner), proof["before_code"])
        changed = {**proof, "consumer_code": {}}
        write_record(
            self.root / "manifests/retrieval/metadata-integration.json", changed, self.sbudget()
        )
        with self.assertRaisesRegex(InputError, "consumer boundary"):
            development.producing_code(self.owner)
