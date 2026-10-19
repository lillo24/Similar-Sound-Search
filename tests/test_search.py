"""Offline A06 boundaries with independent arrays/PCM; no model or held-out inference."""

import copy
import shutil
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase
from scipy.io.wavfile import write as write_wav

from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.evaluation.protocol import comparison_pair
from similar_sound_search.inputs import decode
from similar_sound_search.matchers.models import descriptor
from similar_sound_search.records import map_time
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.search import final as final_check
from similar_sound_search.search import index, query, ranking, sources
from similar_sound_search.search.contracts import (
    configuration,
    grid,
    load_array,
    recipe_code,
    save_array,
    union_frames,
)
from similar_sound_search.search.final import validate_guard
from similar_sound_search.search.job import charge, run
from similar_sound_search.search.pitch import estimate, penalty
from similar_sound_search.search.ranking import distances, excluded_source, rank, sort_key
from similar_sound_search.search.report import (
    build,
    byte_range,
    clip,
    link,
    page,
    pcm16,
    verify_bundle,
)
from similar_sound_search.storage import InputError, ResourceError, digest


class SearchCase(AudioCase):
    def setUp(self):
        super().setUp()
        for name in ("search.json", "matcher_methods.json"):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        self.cfg = configuration(self.root)
        self.desc = descriptor(self.root, "acoustic")

    def sbudget(self):
        return CatalogueBudget(
            self.root, load_limits(self.root / "config/resource_limits.json", "starter")
        )

    def frozen(self, budget, method="acoustic"):
        return {}, {}, {}, {}, self.desc

    def engineering_spec(self):
        rate = 8000
        t = np.arange(rate * 4) / rate
        samples = np.stack(
            [0.1 * np.sin(2 * np.pi * 220 * t), 0.07 * np.sin(2 * np.pi * 220 * t)], axis=1
        ).astype(np.float32)
        path = self.root / "data/audio/engineering/known.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(path, rate, samples)
        context = self.context("excerpt", 10)
        context["provenance"]["permitted_use"] = "Generated A06 engineering fixture"
        self.json_file("config/local/known-context.json", context)
        spec = self.json_file(
            "config/local/engineering.json",
            {
                "schema_version": "a06-engineering-1",
                "sources": [
                    {
                        "path": "data/audio/engineering/known.wav",
                        "context": "config/local/known-context.json",
                    }
                ],
            },
        )
        return path, samples, spec

    def build_index(self):
        path, samples, spec = self.engineering_spec()
        request = {"method": "acoustic", "engineering": str(spec), "cursor": 0}
        with patch.object(index, "frozen", self.frozen):
            first = index.step(request, self.sbudget())
            self.assertEqual(first["state"], "in_progress")
            done = index.step({**request, "cursor": 1}, self.sbudget())
        return path, samples, self.root / done["index"]

    def query_input(self, original, multiple=False):
        first = {
            "path": str(original),
            "start": "1",
            "end": "2",
            "context": "config/local/known-context.json",
        }
        second = {**first, "start": "2", "end": "3"}
        return self.json_file(
            "config/local/query.json",
            {
                "schema_version": "a06-query-input-1",
                "label": "Known query",
                "examples": [first, second, first] if multiple else [first],
            },
        )

    def test_native_grid_rounding_and_unique_tail(self):
        self.assertEqual(grid(192000, 24000, self.cfg)[-1], (134400, 192000))
        self.assertEqual(grid(44100 * 3 + 7, 44100, self.cfg)[-1], (26467, 132307))
        tiny = grid(3, 11027, self.cfg)
        self.assertEqual(tiny, [(0, 3)])
        bounds = grid(11027 * 5, 11027, self.cfg)
        self.assertEqual(bounds[1][0], 2757)
        self.assertEqual(bounds[0][1], 26465)
        self.assertEqual(len(bounds), len(set(bounds)))
        self.assertEqual(union_frames(bounds), 55135)

    def test_grid_invalid_and_overlapping_union_not_processed_sum(self):
        for args in ((0, 24000), (True, 24000), (1, 0)):
            with self.assertRaises(InputError):
                grid(*args, self.cfg)
        self.assertEqual(union_frames([(0, 10), (5, 15), (20, 25)]), 20)

    def test_exact_sharded_mean_matches_independent_brute_force(self):
        rng = np.random.default_rng(406)
        a = rng.normal(size=(3, 7)).astype(np.float32)
        b = rng.normal(size=(21, 7)).astype(np.float32)
        expected = np.array(
            [
                np.mean(
                    [
                        1
                        - np.dot(x.astype(float), y)
                        / np.linalg.norm(x.astype(float))
                        / np.linalg.norm(y)
                        for x in a
                    ]
                )
                for y in b.astype(float)
            ]
        )
        actual = np.concatenate(
            [distances(a, b[s : s + 4], "cosine")[1] for s in range(0, len(b), 4)]
        )
        np.testing.assert_allclose(actual, expected, atol=1e-14)
        np.testing.assert_allclose(distances(a[::-1], b, "cosine")[1], expected, atol=1e-14)
        self.assertEqual(actual.argsort().tolist(), expected.argsort().tolist())

    def test_distance_invalid_and_euclidean_answer(self):
        per, agg = distances([[0, 0], [0, 4]], [[3, 0]], "euclidean")
        np.testing.assert_allclose(per, [[3], [5]])
        self.assertEqual(agg.tolist(), [4])
        for a, b, kind in (
            ([[0, 0]], [[1, 0]], "cosine"),
            ([[float("nan")]], [[1]], "cosine"),
            ([[1]], [[1, 2]], "cosine"),
        ):
            with self.assertRaises(InputError):
                distances(a, b, kind)

    def test_query_examples_deduplicate_and_order_invariant(self):
        path, _, _ = self.engineering_spec()
        spec = self.query_input(path, True)
        with (
            patch.object(query, "frozen", self.frozen),
            patch.object(query, "parents", return_value=[]),
        ):
            first = query.prepare_query(self.sbudget(), spec, "acoustic")
            self.assertEqual(first["examples"], 2)
            value = record(self.root / first["query"])
            changed = self.json_file(
                "config/local/reversed.json",
                {
                    "schema_version": "a06-query-input-1",
                    "examples": list(
                        reversed(
                            __import__("json").loads(spec.read_text(encoding="utf-8"))["examples"]
                        )
                    ),
                },
            )
            second = query.prepare_query(self.sbudget(), changed, "acoustic")
        self.assertTrue(second["reused"])
        self.assertEqual(first["query_id"], second["query_id"])
        self.assertEqual(
            map_time(value["examples"][0]["prepared"], 0.1)["recording_seconds"],
            map_time(value["examples"][0]["prepared"], 0.1)["source_seconds"] + 10,
        )

    def test_query_overlong_refuses_before_preparation(self):
        path = self.wav(rate=8000, channels=1, frames=31 * 8000)
        spec = self.json_file(
            "config/local/long.json",
            {"schema_version": "a06-query-input-1", "examples": [{"path": str(path)}]},
        )
        with (
            patch.object(query, "frozen", self.frozen),
            self.assertRaisesRegex(InputError, "exceeds 30"),
        ):
            query.prepare_query(self.sbudget(), spec, "acoustic")

    def test_duplicate_parent_exclusion_and_explicit_diagnostic(self):
        q = {
            "identity": {"excluded_groups": ["known-reencoding"]},
            "examples": [
                {
                    "prepared": {
                        "source": {"sha256": "original"},
                        "technical_metadata": {"canonical_pcm": {"sha256": "samples"}},
                    }
                }
            ],
        }
        s = {
            "group": "other",
            "source": {"sha256": "original", "canonical_pcm": {"sha256": "changed"}},
        }
        self.assertTrue(excluded_source(s, q))
        s["source"]["sha256"] = "reencoded"
        s["source"]["canonical_pcm"]["sha256"] = "samples"
        self.assertTrue(excluded_source(s, q))
        s["source"]["canonical_pcm"]["sha256"] = "different"
        s["group"] = "known-reencoding"
        self.assertTrue(excluded_source(s, q))
        self.assertFalse(excluded_source(s, q, True))
        s["group"] = "same-artist-different-recording"
        self.assertFalse(excluded_source(s, q))

    def test_query_parent_groups_follow_pcm_reencodings_without_artist_exclusion(self):
        records = [
            {
                "entry_id": "copy",
                "source_asset": {"sha256": "different", "canonical_pcm": {"sha256": "same-pcm"}},
                "analysis_derivative": {"sha256": "other"},
            },
            {
                "entry_id": "other-song-same-artist",
                "source_asset": {"sha256": "other", "canonical_pcm": {"sha256": "other-pcm"}},
                "analysis_derivative": {"sha256": "other"},
            },
        ]
        groups = {
            "entry_groups": {"copy": "family-of-original", "other-song-same-artist": "unrelated"}
        }
        prepared = {
            "source": {"sha256": "original"},
            "preparation_identity": {"input_sha256": "crop"},
        }
        with patch.object(sources, "catalogue", return_value=(records, groups)):
            self.assertEqual(
                query.parents(self.root, prepared, {"sha256": "same-pcm"}), ["family-of-original"]
            )

    def test_array_source_binding_missing_corrupt_and_path_containment(self):
        budget = self.sbudget()
        identity = {"dimension": 2, "source": "immutable"}
        directory = self.root / "data/features/test"
        save_array(directory, identity, np.array([[1, 2]], np.float32), budget)
        target = directory / digest(identity)
        array, _ = load_array(target, identity, budget)
        np.testing.assert_array_equal(array, [[1, 2]])
        with self.assertRaises(InputError):
            load_array(target, {**identity, "source": "changed"}, budget)
        (target / "features.npy").write_bytes(b"corrupt")
        with self.assertRaises(InputError):
            load_array(target, identity, budget)
        with self.assertRaises(InputError):
            save_array(
                self.root.parent / "escape", identity, np.array([[1, 2]], np.float32), budget
            )

    def test_index_complete_reuse_does_not_reembed(self):
        _, _, index_path = self.build_index()
        v = record(index_path)
        self.assertEqual(v["coverage"]["recordings"], 1)
        self.assertEqual(v["coverage"]["indexed_unique_seconds"], 4)
        before = record(self.root / "data/runs/search/work.json")["counts"]["indexed_windows"]
        with (
            patch.object(index, "frozen", self.frozen),
            patch.object(index, "adapter", side_effect=AssertionError("reembedding")),
        ):
            spec = self.root / "config/local/engineering.json"
            index.step(
                {"cursor": 0, "method": "acoustic", "engineering": str(spec)}, self.sbudget()
            )
        after = record(self.root / "data/runs/search/work.json")["counts"]["indexed_windows"]
        self.assertEqual(before, after)

    def test_index_interruption_preserves_shard_and_resumes(self):
        _, _, spec = self.engineering_spec()
        cfg = copy.deepcopy(self.cfg)
        cfg["windows_per_shard"] = 2
        self.json_file("config/search.json", cfg)
        req = {"cursor": 0, "method": "acoustic", "engineering": str(spec)}
        with patch.object(index, "frozen", self.frozen):
            first = index.step(req, self.sbudget())
            self.assertEqual(first["cursor"], 0)
            with patch.object(index, "save_array", side_effect=OSError("interrupted write")):
                with self.assertRaises(OSError):
                    index.step(req, self.sbudget())
            final = first
            for _ in range(10):
                final = index.step({**req, "cursor": final["cursor"]}, self.sbudget())
                if final.get("state") == "complete":
                    break
        self.assertEqual(final["state"], "complete")
        counts = record(self.root / "data/runs/search/work.json")["counts"]
        self.assertGreater(
            counts["indexed_windows"], record(self.root / final["index"])["coverage"]["windows"]
        )

    def test_partial_refusal_and_truth_metadata_not_in_feature_identity(self):
        _, _, path = self.build_index()
        value = record(path)
        value["state"] = "partial"
        write_record(path, value, self.sbudget())
        with patch.object(index, "frozen", self.frozen):
            with self.assertRaisesRegex(InputError, "partial"):
                index.open_index(self.sbudget(), path)
            index.open_index(self.sbudget(), path, True)
        source = record(next((path.parent / "entries").glob("*.json")))["source"]
        altered = copy.deepcopy(source)
        altered.update(title="truth target secret", artist="different")
        self.assertEqual(
            index.shard_identity(source, [(0, 3)], self.desc, self.cfg),
            index.shard_identity(altered, [(0, 3)], self.desc, self.cfg),
        )

    def test_index_original_change_and_shard_corruption_refuse(self):
        original, _, path = self.build_index()
        source = record(next((path.parent / "entries").glob("*.json")))["source"]
        original.write_bytes(original.read_bytes() + b"changed")
        with self.assertRaisesRegex(InputError, "sha256"):
            sources.load(self.sbudget(), source)

    def test_actual_small_acoustic_query_rank_report_and_exclusion(self):
        original, _, index_path = self.build_index()
        spec = self.query_input(original)
        with (
            patch.object(query, "frozen", self.frozen),
            patch.object(query, "parents", return_value=[]),
        ):
            prepared = query.prepare_query(self.sbudget(), spec, "acoustic")
        request = {
            "index": str(index_path),
            "query": str(self.root / prepared["query"]),
            "pitch_weight": 0,
        }
        with patch.object(index, "frozen", self.frozen):
            discoveries = rank(request, self.sbudget())
            diagnostic = rank({**request, "include_self": True}, self.sbudget())
            index.step(
                {
                    "method": "acoustic",
                    "cursor": 0,
                    "engineering": str(self.root / "config/local/engineering.json"),
                },
                self.sbudget(),
            )
            index.step(
                {
                    "method": "acoustic",
                    "cursor": 1,
                    "engineering": str(self.root / "config/local/engineering.json"),
                },
                self.sbudget(),
            )
            repeated = rank({**request, "include_self": True}, self.sbudget())
        self.assertEqual(repeated["result"], diagnostic["result"])
        self.assertTrue(repeated["reused"])
        self.assertEqual(discoveries["candidates"], 0)
        self.assertEqual(diagnostic["candidates"], 1)
        delivered = build(self.sbudget(), self.root / diagnostic["result"])
        allowed = verify_bundle(self.root, self.root / delivered["report"])
        self.assertEqual(len(allowed), 3)
        self.assertEqual(delivered["clips"], 2)

    def test_pitch_known_notes_abstains_on_noise_chord_silence_and_off(self):
        rate = 24000
        t = np.arange(rate) / rate
        for hz in (110, 220, 440):
            value = estimate((0.1 * np.sin(2 * np.pi * hz * t)).astype(np.float32), rate)
            self.assertIsNotNone(value["hz"])
            self.assertLess(abs(12 * np.log2(value["hz"] / hz)), 0.3)
        for samples in (
            np.zeros(rate, np.float32),
            np.random.default_rng(6).normal(0, 0.1, rate).astype(np.float32),
            (0.1 * np.sin(2 * np.pi * 220 * t) + 0.1 * np.sin(2 * np.pi * 330 * t)).astype(
                np.float32
            ),
        ):
            self.assertIsNone(estimate(samples, rate)["hz"])
        self.assertEqual(penalty([{"hz": 220}], {"hz": 440}, 0), 0)
        self.assertEqual(penalty([{"hz": None}], {"hz": 440}, 0.05), 0)
        self.assertEqual(penalty([{"hz": 220}], {"hz": 440}, 0.05), 0.05)

    def test_pcm16_conversion_no_overflow_and_sample_exact_crop(self):
        values = np.array([[1.2, -1.2], [0.5, -0.5], [0, 0]], np.float32)
        ints, gain = pcm16(values)
        self.assertLess(gain, 1)
        self.assertEqual(ints[0].tolist(), [32767, -32767])
        original, samples, _ = self.engineering_spec()
        _, meta = decode(original, self.sbudget())
        source = {"source": meta}
        directory = self.root / "reports/local/a06/test/media"
        receipt = clip(self.sbudget(), directory, source, samples, 300, 803)
        x, current = decode(directory / receipt["path"].split("/")[-1], self.sbudget())
        expected = (
            np.rint(samples[300:803].astype(float) * 32768).astype(np.int16).astype(np.float32)
            / 32768
        )
        np.testing.assert_array_equal(x, expected)
        self.assertEqual(current["channels"], 2)
        self.assertEqual(receipt["clip_zero_source_seconds"], 0.0375)
        (directory / receipt["path"].split("/")[-1]).write_bytes(b"bad")
        with self.assertRaises(InputError):
            clip(self.sbudget(), directory, source, samples, 300, 803)

    def test_report_titles_urls_safe_and_missing_bundle_visible(self):
        item = {
            "role": "query",
            "source": {
                "source": {"sample_rate_hz": 1},
                "title": "<script>alert(1)</script>",
                "artist": "<img onerror=x>",
                "basis": "excerpt",
                "offset": None,
                "source_url": "javascript:bad",
            },
            "start_frame": 0,
            "end_frame": 2,
            "clip": {
                "source_start_frame": 0,
                "source_end_frame": 2,
                "path": "media/test.wav",
                "channels": 2,
                "gain": 1,
                "clip_zero_source_seconds": 0,
                "duration_seconds": 2,
            },
        }
        rendered = page({"label": "<bad>", "items": [item]})
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertIn("excerpt-relative", rendered)
        self.assertNotIn("javascript:bad", rendered)
        self.assertIn("Media missing or stale", rendered)
        self.assertEqual(link("file:///C:/secret", "bad"), "")
        with self.assertRaises(InputError):
            verify_bundle(self.root, self.root.parent / "outside")

    def test_media_ranges_support_bounded_wav_seek_without_arbitrary_paths(self):
        self.assertEqual(byte_range(None, 100), (0, 99, False))
        self.assertEqual(byte_range("bytes=20-29", 100), (20, 29, True))
        self.assertEqual(byte_range("bytes=40-", 100), (40, 99, True))
        self.assertEqual(byte_range("bytes=-10", 100), (90, 99, True))
        self.assertEqual(byte_range("bytes=40-200", 100), (40, 99, True))
        for value in (
            "bytes=100-",
            "bytes=-0",
            "bytes=30-20",
            "bytes=1-2,3-4",
            "bytes=-",
            "bytes=../../-file",
            "bytes=" + "9" * 65 + "-",
        ):
            with self.assertRaises(InputError):
                byte_range(value, 100)

    def test_budget_retains_failed_work_and_lowered_caps(self):
        charge(self.sbudget(), final_attempts=1, indexed_windows=10)
        with self.assertRaises(ResourceError):
            charge(self.sbudget(), final_attempts=1)
        cfg = copy.deepcopy(self.cfg)
        cfg["policy"]["max_indexed_windows"] = 10
        self.json_file("config/search.json", cfg)
        with self.assertRaises(ResourceError):
            charge(self.sbudget(), indexed_windows=1)
        cfg["policy"]["max_indexed_windows"] = 60000
        self.json_file("config/search.json", cfg)
        with self.assertRaises(ResourceError):
            charge(self.sbudget(), indexed_windows=1)

    def test_worker_failure_charged_and_no_job_names(self):
        request = {
            "root": str(self.root),
            "limits": self.sbudget().limits,
            "search_action": "index",
        }
        result = run(request, lambda _: {"status": "failed", "error": "technical interruption"})
        self.assertEqual(result["status"], "failed")
        self.assertGreater(result["ledger"]["charged_worker_seconds"], 0)
        self.assertEqual(result["work"]["counts"]["workers"], 1)

    def test_four_record_ranking_workers_preserve_exact_result_and_reuse(self):
        _, _, path = self.build_index()
        manifest = record(path)
        original_key = next(iter(manifest["entries"]))
        entry = record(path.parent / "entries" / (original_key + ".json"))
        keys = [f"test-entry-{n}" for n in range(6)]
        for key in keys:
            write_record(path.parent / "entries" / (key + ".json"), entry, self.sbudget())
        manifest.update(
            entries={k: "complete" for k in keys},
            expected_recordings=6,
            expected_original_seconds=24,
        )
        fake_query = {
            "query_id": "test-query",
            "identity": {"excluded_groups": []},
            "examples": [{"audio": {"duration_seconds": 2.4}, "pitch": {"hz": None}}],
        }
        request = {"index": str(path), "query": "test", "include_self": True, "cursor": 0}
        with (
            patch.object(
                ranking, "open_index", return_value=(path.parent, manifest, self.desc, self.cfg)
            ),
            patch.object(
                ranking, "load_query", return_value=(fake_query, np.ones((1, 56), np.float32))
            ),
        ):
            first = rank(request, self.sbudget())
            self.assertEqual(first["cursor"], 4)
            self.assertEqual(first["state"], "in_progress")
            last = rank({**request, "cursor": first["cursor"]}, self.sbudget())
            first_again = rank(request, self.sbudget())
            repeated = rank({**request, "cursor": first_again["cursor"]}, self.sbudget())
        self.assertEqual(last["candidates"], 1)
        self.assertEqual(last["result"], repeated["result"])
        self.assertTrue(repeated["reused"])
        self.assertEqual(
            record(self.root / last["result"])["candidates"][0]["recording_id"], keys[0]
        )

    def test_execution_repair_binds_original_sources_and_rejects_drift(self):
        destination = self.root / "manifests/search"
        destination.mkdir(parents=True)
        for name in ("final-check.json", "execution-repair.json"):
            shutil.copyfile(REPOSITORY / "manifests/search" / name, destination / name)
        declared = record(destination / "final-check.json")
        repair = record(destination / "execution-repair.json")
        # B01 adds consumer modules: the A06 guard must accept only its historical
        # executing map. Its protected function proofs still use the actual code.
        with patch(
            "similar_sound_search.search.contracts.code_identity", return_value=repair["after"]
        ):
            self.assertEqual(recipe_code(self.root), declared["binding"]["code"])
        with self.assertRaisesRegex(InputError, "unaudited"):
            recipe_code(self.root)
        repair["after"]["search/ranking.py"] = "invalid executing source hash"
        write_record(destination / "execution-repair.json", repair, self.sbudget())
        with self.assertRaisesRegex(InputError, "unaudited"):
            recipe_code(self.root)

    def test_stable_ties_do_not_use_titles(self):
        hits = [
            {
                "score": 0.1,
                "recording_id": r,
                "start_frame": t,
                "end_frame": t + 1,
                "title": "truth",
            }
            for r, t in (("b", 0), ("a", 1), ("a", 0))
        ]
        self.assertEqual(
            [(v["recording_id"], v["start_frame"]) for v in sorted(hits, key=sort_key)],
            [("a", 0), ("a", 1), ("b", 0)],
        )

    def test_final_guard_requires_original_choice_shortlist_grid_and_run(self):
        choice = record(REPOSITORY / "manifests/matchers/choice.json")
        shortlist = record(REPOSITORY / "manifests/matchers/shortlist.json")
        protocol, suite = comparison_pair(REPOSITORY)
        from similar_sound_search.matchers.windows import POLICY

        binding = {
            "choice_hash": choice["record_hash"],
            "protocol_hash": protocol["record_hash"],
            "suite_hash": suite["record_hash"],
            "config_hash": choice["config_hash"],
            "method_id": choice["method_id"],
            "configuration": choice["configuration"],
            "shortlist_hash": shortlist["record_hash"],
            "checkpoint": choice["configuration"]["checkpoint"],
            "query_count": 80,
            "accounting_owner": "data/runs/search",
            "grid": POLICY,
            "split": "held_out",
            "pitch_weight": 0,
            "refinement": "empty",
            "attempt": 1,
            "code": {"declared": "code"},
            "environment": {"declared": "versions"},
        }
        declaration = {
            "schema_version": "a06-final-1",
            "stage": "A06",
            "selected_on": "development",
            "declared_before_inference": True,
            "binding": binding,
            "a05_choice": choice,
            "a05_shortlist": shortlist,
            "run_id": "a06-final-" + digest(binding),
        }
        declaration["record_hash"] = digest(declaration)
        pred = {**binding, "run_id": declaration["run_id"]}
        validate_guard(declaration, protocol, pred)
        for altered in (
            {"stage": "A06"},
            {**declaration, "stage": "A05"},
            {**declaration, "a05_choice": {**choice, "stage": "A06"}},
        ):
            with self.assertRaises(InputError):
                validate_guard(altered, protocol, pred)
        changed = copy.deepcopy(declaration)
        changed["binding"]["pitch_weight"] = 0.01
        changed["record_hash"] = digest({k: v for k, v in changed.items() if k != "record_hash"})
        with self.assertRaises(InputError):
            validate_guard(changed, protocol, pred)

    def test_final_coordinator_resumes_technical_failure_without_new_attempt(self):
        protocol, suite = comparison_pair(REPOSITORY)
        suite = {
            **suite,
            "queries": [
                {
                    "split": "held_out",
                    "query_id": "test-only",
                    "query_asset_id": "a",
                    "candidate_assets": ["b"],
                }
            ],
        }
        meta = {
            "sample_count": 57600,
            "sample_rate_hz": 24000,
            "duration_seconds": 2.4,
            "sha256": "test-bytes",
            "canonical_pcm": {"sha256": "test-pcm"},
        }
        assets = {key: {"asset_id": key, "audio": meta, "split": "held_out"} for key in ("a", "b")}
        desc = descriptor(REPOSITORY, "efficientat")
        declaration = {"record_hash": "test-declaration", "run_id": "test-only-not-a-final-score"}

        class Fake:
            def encode(self, samples, rate):
                return np.ones(384, dtype=np.float32)

        charge(self.sbudget(), final_attempts=1)
        with (
            patch.object(
                final_check, "declaration_for", return_value=(declaration, protocol, suite, desc)
            ),
            patch.object(final_check, "assets_for", return_value=assets),
            patch.object(
                final_check,
                "load_asset",
                side_effect=lambda _, key, b: (np.zeros((57600, 1), np.float32), assets[key]),
            ),
            patch.object(final_check, "adapter", return_value=(Fake(), 0)),
        ):
            with patch.object(
                final_check, "save_array", side_effect=OSError("technical publication stop")
            ):
                with self.assertRaises(OSError):
                    final_check.run_step(self.sbudget())
            complete = final_check.run_step(self.sbudget())
            with patch.object(
                final_check, "adapter", side_effect=AssertionError("repeat inference")
            ):
                reused = final_check.run_step(self.sbudget())
        self.assertEqual(complete["state"], "complete")
        self.assertEqual(reused["queries"], 1)
        self.assertEqual(
            record(self.root / "data/runs/search/work.json")["counts"]["final_attempts"], 1
        )
        self.assertEqual(
            record(self.root / "data/runs/search/work.json")["counts"]["final_windows"], 3
        )
        self.assertTrue((self.root / "data/runs/search/final/predictions.json").is_file())
        self.assertFalse((self.root / "data/runs/search/final/scores.json").exists())
