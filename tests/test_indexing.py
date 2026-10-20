"""Offline C01 bank, crash, provenance and scalar-oracle tests in disposable roots."""

import copy
import io
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase
from scipy.io.wavfile import write as write_wav

from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.events import compatibility
from similar_sound_search.indexing import banks, build, components, development, ranking, reader
from similar_sound_search.indexing import queries as index_queries
from similar_sound_search.indexing.context import (
    Context,
    DerivedQueryContext,
    QueryView,
    configuration,
)
from similar_sound_search.indexing.job import run
from similar_sound_search.indexing.validation import geometry, known_answer
from similar_sound_search.inputs import decode
from similar_sound_search.queries import assets, features, library, materialization
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.search import query, sources
from similar_sound_search.search.contracts import load_array
from similar_sound_search.storage import InputError, ResourceError, digest, project_lock, read_json


class Model:
    def __init__(self):
        self.calls = 0

    def encode(self, samples, rate):
        self.calls += 1
        return np.asarray(
            [1 + np.mean(samples), 2 + np.max(samples), 3 + np.std(samples)], np.float32
        )


class IndexCase(AudioCase):
    def setUp(self):
        super().setUp()
        for name in ("indexing.json", "queries.json", "separation.json", "search.json"):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        path = self.root / "manifests/indexing"
        path.mkdir()
        shutil.copyfile(REPOSITORY / "manifests/indexing/protocol.json", path / "protocol.json")
        self.owner = Context(self.root)
        self.desc = {
            "method": "efficientat",
            "dimension": 3,
            "distance": "cosine",
            "fixture_only": True,
        }
        self.model = Model()
        self.owner.feature_model = (self.desc, self.model)
        guard = patch.object(compatibility, "audit", return_value={"fixture_only": True})
        guard.start()
        self.addCleanup(guard.stop)

    def sbudget(self):
        return CatalogueBudget(
            self.root, load_limits(self.root / "config/resource_limits.json", "starter")
        )

    def signal(self, name="fixture", seconds=3.1, rate=8000, group=None):
        t = np.arange(round(rate * seconds)) / rate
        samples = (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)[:, None]
        path = self.root / "data/audio/indexing/tests" / (name + ".wav")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(path, rate, samples)
        _, meta = decode(path, self.sbudget())
        audio = {**meta, "local_path": path.relative_to(self.root).as_posix()}
        source = development.public(audio, name, group or name)
        return banks.original_signal(source)

    def plan(self, signals=None, duration=1200, hop=500):
        signal = self.signal() if signals is None else None
        signals = signals or {signal["signal_id"]: signal}
        return banks.create_plan(
            self.sbudget(),
            self.owner,
            "test",
            "original",
            self.desc,
            {"window_milliseconds": duration, "hop_milliseconds": hop},
            signals,
            "engineering",
        )

    def finish(self, path):
        while build.step(self.sbudget(), self.owner, path, "full")["state"] == "in_progress":
            pass

    def test_independent_grid_distance_and_full_winner_oracles(self):
        answer = known_answer()
        self.assertTrue(answer["passed"])
        self.assertGreater(answer["independent_grid_rows"], 100)

    def test_encoded_rows_use_independently_enumerated_native_samples(self):
        signal = self.signal(rate=44100)
        samples, _ = decode(self.root / signal["audio"]["local_path"], self.sbudget())
        seen = []
        base_encode = self.model.encode

        def capture(x, rate):
            seen.append(x.copy())
            return base_encode(x, rate)

        self.model.encode = capture
        path, plan = self.plan({signal["signal_id"]: signal})
        self.finish(path)
        starts = [0, 22050, 44100, 66150, len(samples) - 52920]
        self.assertEqual(len(seen), len(starts))
        for actual, start in zip(seen, starts, strict=True):
            np.testing.assert_array_equal(actual, samples[start : start + 52920])
        unit = banks.units(plan)[0]
        array, _ = load_array(build.array_path(self.owner, unit), unit["identity"], self.sbudget())
        expected = np.asarray(
            [[1 + np.mean(x), 2 + np.max(x), 3 + np.std(x)] for x in seen], np.float32
        )
        np.testing.assert_array_equal(array, expected)

    def test_same_dimension_incompatible_representation_is_refused_before_scoring(self):
        path, _ = self.plan()
        self.finish(path)
        snapshot_path, _ = build.bank_snapshot(self.sbudget(), self.owner, path)
        q = {
            "record_hash": "q",
            "identity": {"representation": {**self.desc, "checkpoint": "other"}},
        }
        with (
            patch.object(index_queries, "load", return_value=({}, {}, q, np.ones((1, 3)))),
            patch.object(
                ranking, "distances", side_effect=AssertionError("incompatible features scored")
            ),
        ):
            with self.assertRaisesRegex(InputError, "representations differ"):
                ranking.step({"input": str(snapshot_path)}, self.sbudget(), self.owner)

    def test_compact_winner_progress_resumes_and_rejects_corruption(self):
        signals = {
            s["signal_id"]: s
            for s in [self.signal("resume-" + str(i), seconds=2.1 + i * 0.1) for i in range(5)]
        }
        path, _ = self.plan(signals)
        self.finish(path)
        bank_path, _ = build.bank_snapshot(self.sbudget(), self.owner, path)
        q = {
            "record_hash": "fixture-query",
            "identity": {"representation": self.desc, "excluded_groups": []},
            "examples": [
                {
                    "audio": {"duration_seconds": 1},
                    "prepared": {
                        "source": {"sha256": "other"},
                        "technical_metadata": {"canonical_pcm": {"sha256": "other"}},
                    },
                }
            ],
        }
        value = (
            {"revision_id": "fixture-revision"},
            {"materialization_id": "fixture-materialization"},
            q,
            np.asarray([[1, 2, 3]], np.float32),
        )
        with patch.object(index_queries, "load", return_value=value):
            first = ranking.step({"input": str(bank_path)}, self.sbudget(), self.owner)
            self.assertEqual(first["state"], "in_progress")
            progress_path = next((self.owner.directory / "rank-progress").glob("*.json"))
            progress = record(progress_path)
            self.assertEqual(len(progress["winner_references"]), 4)
            self.assertNotIn("best", progress)
            ref = next(iter(progress["winner_references"].values()))
            target = self.root / ref["path"]
            original = target.read_bytes()
            target.write_bytes(b"corrupt")
            with self.assertRaises(InputError):
                ranking.step({"input": str(bank_path)}, self.sbudget(), self.owner)
            target.write_bytes(original)
            final = ranking.step({"input": str(bank_path)}, self.sbudget(), self.owner)
        result = record(self.root / final["execution"])
        self.assertEqual(result["eligible_groups"], 5)
        self.assertEqual(len(result["winners"]), 5)
        self.assertEqual(record(self.owner.directory / "work.json")["counts"]["query_jobs"], 1)

    def test_legacy_snapshot_references_44025_rows_below_metadata_limit_without_copy(self):
        # Synthetic metadata graph: no catalogue/model/audio is consumed. This
        # isolates serialization/reference behavior from the separately tested
        # frozen compatibility proof and actual delivery equivalence.
        from similar_sound_search.search.contracts import grid

        native = self.signal()["original"]
        base = self.root / "data/indexes/a06" / compatibility.INDEX
        entries, windows = {}, 0
        budget = self.sbudget()
        cfg = {"window_milliseconds": 2400, "hop_milliseconds": 250}
        for i in range(72):
            key = f"fixture-{i:02d}"
            n = 675 if i == 0 else 657 if i < 51 else 500
            source = copy.deepcopy(native)
            source["recording_id"] = key
            a = source["source"]
            a["sample_count"] = (n - 1) * 2000 + 19200
            a["duration_seconds"] = a["sample_count"] / 8000
            bounds = [list(v) for v in grid(a["sample_count"], 8000, cfg)]
            self.assertEqual(len(bounds), n)
            keys = []
            for first in range(0, n, 512):
                identity = {
                    "fixture_only": True,
                    "source": key,
                    "bounds": bounds[first : first + 512],
                    "dimension": 3,
                }
                shard = digest(identity)
                write_record(
                    base / "shards" / shard / "record.json",
                    {
                        "identity": identity,
                        "shape": [len(identity["bounds"]), 3],
                        "dtype": "float32",
                        "sha256": "fixture-unread-array",
                        "bytes": 128 + len(identity["bounds"]) * 12,
                    },
                    budget,
                )
                keys.append(shard)
            write_record(
                base / "entries" / (key + ".json"), {"source": source, "shards": keys}, budget
            )
            entries[key] = "complete"
            windows += n
        index = {
            "entries": entries,
            "index_id": compatibility.INDEX,
            "record_hash": "synthetic-metadata-fixture",
            "state": "complete",
        }
        receipt = self.owner.directory / "compatibility/fixture.json"
        write_record(receipt, {"fixture_only": True}, budget)
        cov = {
            "windows": windows,
            "indexed_unique_seconds": 1,
            "processed_window_seconds": windows * 2.4,
        }
        with (
            patch.object(compatibility, "snapshot", return_value=(index, self.desc, cfg, {})),
            patch.object(compatibility, "validate_receipt"),
            patch.object(reader, "legacy_coverage", return_value=cov),
        ):
            value = reader.legacy(budget, self.owner, receipt)
            path = self.owner.indexes / "legacy" / (digest(value) + ".json")
            self.owner.publish(budget, path, value, immutable=True)
            expanded = reader.read_bank(budget, self.owner, path)
        self.assertEqual(sum(u["array"]["shape"][0] for u in expanded["committed"]), 44025)
        self.assertEqual(len(value["committed"]), 123)
        self.assertLess(path.stat().st_size, 1024**2)
        self.assertEqual(value["copied_features"], 0)
        self.assertTrue(
            all("identity" not in ref and "array" not in ref for ref in value["committed"])
        )

    def test_semantic_features_ignore_display_and_unrelated_producer_changes(self):
        signal = self.signal()
        first = banks.sample_identity(signal)
        renamed = copy.deepcopy(signal)
        renamed["original"]["title"] = "Renamed"
        renamed["original"]["record_hash"] = "changed public annotation"
        self.assertEqual(first, banks.sample_identity(renamed))
        renamed["audio"] = {**renamed["audio"], "sha256": "b" * 64}
        self.assertNotEqual(first, banks.sample_identity(renamed))
        path, plan = self.plan({signal["signal_id"]: signal})
        old = banks.units(plan)[0]["unit_id"]
        plan["producer"] = {"unrelated coordinator": "changed"}
        plan["label"] = "changed label"
        self.assertEqual(old, banks.units(plan)[0]["unit_id"])
        self.assertTrue(path.is_file())

    def test_short_file_support_and_actual_coverage_union(self):
        signal = self.signal(seconds=0.3)
        path, plan = self.plan({signal["signal_id"]: signal}, duration=4800, hop=1000)
        self.finish(path)
        _, snap = build.bank_snapshot(self.sbudget(), self.owner, path)
        self.assertEqual(snap["coverage"]["windows"], 1)
        self.assertAlmostEqual(snap["coverage"]["unique_seconds"], 0.3)
        row = banks.passage(plan, banks.units(plan)[0], 0)
        self.assertEqual(row["original_bounds"], [0, 2400])
        self.assertFalse(row["padding_is_support"])
        self.assertEqual(
            snap["coverage"]["sources"][signal["signal_id"]]["unindexed_original_gaps"], []
        )

    def test_partial_snapshot_cannot_hide_missing_rows(self):
        self.owner.cfg["rows_per_shard"] = 2
        # Persist the matching bounded configuration before creating a plan.
        (self.root / "config/indexing.json").write_text(
            json.dumps(self.owner.cfg), encoding="utf-8"
        )
        path, _ = self.plan()
        result = build.step(self.sbudget(), self.owner, path, "full")
        self.assertEqual(result["state"], "in_progress")
        snapshot_path, snap = build.bank_snapshot(self.sbudget(), self.owner, path)
        self.assertEqual(snap["coverage"]["state"], "partial")
        self.assertTrue(next(iter(snap["coverage"]["sources"].values()))["unindexed_original_gaps"])
        with self.assertRaisesRegex(InputError, "partial bank"):
            reader.read_bank(self.sbudget(), self.owner, snapshot_path)
        self.assertEqual(
            reader.read_bank(self.sbudget(), self.owner, snapshot_path, True)["coverage"][
                "windows"
            ],
            2,
        )

    def test_array_before_membership_recovers_without_reembedding(self):
        path, plan = self.plan()
        publish = self.owner.publish

        def interrupted(budget, target, value, immutable=False):
            if "membership" in target.parts:
                raise OSError("simulated crash after atomic array")
            return publish(budget, target, value, immutable)

        with patch.object(self.owner, "publish", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "simulated crash"):
                build.step(self.sbudget(), self.owner, path, "full")
        calls = self.model.calls
        before = record(self.owner.directory / "work.json")["counts"].copy()
        result = build.step(self.sbudget(), self.owner, path, "full")
        self.assertTrue(result["recovered_array"])
        self.assertEqual(calls, self.model.calls)
        after = record(self.owner.directory / "work.json")["counts"]
        self.assertEqual(before["feature_windows"], after["feature_windows"])
        self.assertGreater(after["read_audio_seconds"], before["read_audio_seconds"])
        self.assertEqual(len(build.progress(self.owner, plan)["attempts"]), 2)

    def test_corrupt_array_is_explicit_failure_not_recomputed(self):
        path, plan = self.plan()
        self.finish(path)
        array = build.array_path(self.owner, banks.units(plan)[0]) / "features.npy"
        array.write_bytes(b"corrupt")
        calls = self.model.calls
        with self.assertRaisesRegex(InputError, "corrupt array"):
            build.verify(self.sbudget(), self.owner, path, "full")
        self.assertEqual(calls, self.model.calls)

    def test_one_reuse_pass_preserves_rows_and_charges_validation(self):
        path, _ = self.plan()
        self.finish(path)
        calls = self.model.calls
        before = record(self.owner.directory / "work.json")["counts"]["read_audio_seconds"]
        with patch.object(banks, "code_identity", return_value={"consumer-only": "changed"}):
            result = build.step(self.sbudget(), self.owner, path, "full")
        self.assertEqual(result["new_windows"], 0)
        self.assertGreater(
            record(self.owner.directory / "work.json")["counts"]["read_audio_seconds"], before
        )
        self.assertEqual(calls, self.model.calls)
        with self.assertRaisesRegex(InputError, "already complete"):
            build.verify(self.sbudget(), self.owner, path, "full")

    def test_conflicting_producer_and_configuration_refused(self):
        path, _ = self.plan()
        with patch.object(banks, "code_identity", return_value={"changed": "producer"}):
            with self.assertRaisesRegex(InputError, "producer changed"):
                build.step(self.sbudget(), self.owner, path, "full")
        self.owner.cfg["rows_per_shard"] = 2
        with self.assertRaisesRegex(InputError, "configuration"):
            build.step(self.sbudget(), self.owner, path, "full")

    def test_concurrent_c01_writer_is_refused(self):
        with project_lock(self.root, ".c01-worker.lock"):
            with ThreadPoolExecutor(max_workers=1) as pool:

                def attempt():
                    with project_lock(self.root, ".c01-worker.lock"):
                        return "unexpected"

                with self.assertRaisesRegex(ResourceError, "concurrency"):
                    pool.submit(attempt).result()

    def test_cumulative_policy_does_not_replenish(self):
        self.owner.charge(self.sbudget(), feature_windows=25999)
        with self.assertRaises(ResourceError):
            Context(self.root).charge(self.sbudget(), feature_windows=2)
        cfg = read_json(self.root / "config/indexing.json")
        cfg["policy"]["max_feature_windows"] = 26001
        (self.root / "config/indexing.json").write_text(json.dumps(cfg), encoding="utf-8")
        with self.assertRaisesRegex(InputError, "increased ceiling"):
            configuration(self.root)

    def test_durable_worker_failure_reservations_and_owned_roots(self):
        request = {
            "root": str(self.root),
            "limits": self.sbudget().limits,
            "indexing_action": "known-answer",
        }
        result = run(request, lambda r: {"status": "failed", "error": "fixture failure"})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["work"]["counts"]["workers"], 1)
        self.assertGreater(result["ledger"]["charged_worker_seconds"], 0)
        self.assertFalse((self.root / "data/runs/queries/work.json").exists())
        with self.assertRaisesRegex(InputError, "outside owned"):
            self.owner.publish(self.sbudget(), self.root / "data/runs/queries/wrong.json", {})

    def test_cli_cannot_publish_c01_summary_over_historical_report(self):
        from similar_sound_search.cli import main

        target = self.root / "reports/local/b03/protected.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"historical report")
        with redirect_stdout(io.StringIO()):
            status = main(
                [
                    "--root",
                    str(self.root),
                    "--tier",
                    "starter",
                    "--report",
                    str(target),
                    "indexing",
                    "known-answer",
                ]
            )
        self.assertEqual(status, 1)
        self.assertEqual(target.read_bytes(), b"historical report")

    def test_guided_generic_component_rejected_from_actual_method(self):
        with self.assertRaisesRegex(InputError, "query-dependent/guided"):
            components.component_signal(
                {"identity": {"mode": "guided", "cue": {"exists": True}}},
                "extracted",
                {},
                "historical.json",
            )

    def component_fixture(self):
        signal = self.signal(seconds=8)
        self.addCleanup(patch.stopall)
        patch.object(sources, "catalogue", return_value=([], {"entry_groups": {}})).start()
        from similar_sound_search.queries.context import TransformContext
        from similar_sound_search.separation import artifacts

        spec = {
            "schema_version": "b02-process-input-1",
            "source": {"path": signal["audio"]["local_path"], "sha256": signal["audio"]["sha256"]},
            "region": [8000, 40000],
            "event": [12000, 20000],
            "label": "fixed native region",
        }
        result = artifacts.process(self.sbudget(), spec, "broad", TransformContext(self.owner))
        value = record(self.root / result["transform"])
        return signal, result, value

    def test_component_map_output_and_ancestry_are_bound(self):
        original, result, value = self.component_fixture()
        signal = components.component_signal(
            value, "harmonic", original["original"], result["transform"]
        )
        self.assertEqual(banks.original_bounds(signal, [1, 8001]), [8001, 16001])
        actual = components.load_component(self.sbudget(), self.owner, signal)
        self.assertEqual(len(actual), 32000)
        changed = copy.deepcopy(signal)
        changed["mapping"]["segments"][0]["source_start_seconds"] = 2
        with self.assertRaisesRegex(InputError, "ancestry changed"):
            components.load_component(self.sbudget(), self.owner, changed)

    def test_component_missing_clipped_and_near_silent_refused(self):
        original, result, value = self.component_fixture()
        for key, field in (("state", "near_silence"), ("overload_samples", 1), ("peak", 1.2)):
            changed = copy.deepcopy(value)
            changed["outputs"]["harmonic"][key] = field
            with self.assertRaisesRegex(InputError, "missing, clipped or near-silent"):
                components.component_signal(
                    changed, "harmonic", original["original"], result["transform"]
                )

    def test_component_declaration_keeps_actual_guided_cue_and_refuses_generic_bank(self):
        original, _, broad = self.component_fixture()
        guided = copy.deepcopy(broad)
        guided.pop("record_hash")
        guided["identity"]["mode"] = "guided"
        guided["identity"]["cue"] = {"audio": {"sha256": "c" * 64}}
        guided["transform_id"] = digest(guided["identity"])
        path = self.root / "data/runs/separation/processed" / guided["transform_id"] / "record.json"
        write_record(path, guided, self.sbudget())
        self.owner.protocol["components"]["real_regions"] = []
        self.owner.protocol["components"]["guided_refusal"] = {
            "record": path.relative_to(self.root).as_posix(),
            "record_hash": record(path)["record_hash"],
        }
        result = components.prepare(
            self.sbudget(),
            self.owner,
            self.desc,
            {},
            {"sources": [{"source": original["original"]}]},
        )
        self.assertEqual(result["guided_refusal"]["generic_bank_state"], "refused")
        self.assertEqual(result["guided_refusal"]["cue_preserved"], "c" * 64)
        self.assertEqual(len(result["plans"]), 2)

    def test_resampled_linear_map_rounds_outward_and_rejects_discontinuity(self):
        original = self.signal(seconds=8, rate=44100)
        component = self.signal(name="component", seconds=2, rate=24000)
        signal = {
            **component,
            "kind": "component",
            "original": original["original"],
            "mapping": {
                "basis": "file",
                "unmapped_tail_seconds": 0,
                "segments": [
                    {
                        "asset_start_seconds": 0,
                        "asset_end_seconds": 2,
                        "source_start_seconds": 1,
                        "source_seconds_per_asset_second": 1,
                    }
                ],
            },
        }
        self.assertEqual(banks.original_bounds(signal, [1, 2]), [44101, 44104])
        signal["mapping"]["segments"].append(signal["mapping"]["segments"][0])
        with self.assertRaisesRegex(InputError, "discontinuous"):
            banks.original_bounds(signal, [1, 2])

    def test_real_development_geometry_and_fixed_batch_with_fake_embeddings(self):
        result = development.generate(self.sbudget(), self.owner, self.desc)
        fixtures = record(self.root / result["fixtures"])
        self.assertTrue(geometry(self.sbudget(), self.owner, fixtures)["passed"])
        for relative in fixtures["plans"]:
            self.finish(self.root / relative)
        encode = development.query_feature

        def corrupt_silence(budget, owner, case, desc):
            if case["stratum"] == "silence":
                raise InputError("query bytes changed; not a valid silence control")
            return encode(budget, owner, case, desc)

        with patch.object(development, "query_feature", side_effect=corrupt_silence):
            with self.assertRaisesRegex(InputError, "bytes changed"):
                development.compare(self.sbudget(), self.owner, fixtures, self.desc)
        self.assertFalse((self.owner.directory / "development/comparison.json").exists())
        result = development.compare(self.sbudget(), self.owner, fixtures, self.desc)
        self.assertEqual(result["summary"]["2400"]["alternate_cases"], 6)
        comparison = record(self.root / result["comparison"])
        self.assertEqual(len(comparison["cases"]), 10)
        self.assertTrue(
            next(c for c in comparison["cases"] if c["case_id"] == "silence")["expected_failure"]
        )
        with self.assertRaisesRegex(InputError, "already complete"):
            development.compare(self.sbudget(), self.owner, fixtures, self.desc)
        counts = record(self.owner.directory / "work.json")["counts"]
        self.assertLess(counts["pilot_windows"], 1024)
        self.assertEqual(counts["comparison_batches"], 1)
        self.assertEqual(
            [result["summary"][str(d)]["full_event_support"] for d in (1200, 2400, 4800)],
            [[0, 10], [5, 10], [10, 10]],
        )

    def saved_query(self):
        from similar_sound_search.queries.context import Context as B03Context

        old = B03Context(self.root)
        signal = self.signal()
        for mock in (
            patch.object(sources, "catalogue", return_value=([], {"entry_groups": {}})),
            patch.object(query, "frozen", return_value=({}, {}, {}, {}, self.desc)),
            patch.object(materialization, "frozen", return_value=({}, {}, {}, {}, self.desc)),
            patch.object(features, "adapter", return_value=(self.model, 0)),
        ):
            mock.start()
            self.addCleanup(mock.stop)
        registered = assets.register(self.sbudget(), old, self.root / signal["audio"]["local_path"])
        spec = {
            "schema_version": "b03-query-input-1",
            "examples": [
                {
                    "asset_id": registered["asset_id"],
                    "event": [800, 16800],
                    "context": [0, 24000],
                    "selection": {
                        "origin": "fixed native test",
                        "version": "test-1",
                        "complete": True,
                        "uncertainty": [],
                    },
                }
            ],
        }
        result = library.save(self.sbudget(), old, spec, "Unrelated mutable label")
        revision = library.revision(old, result["revision_id"])
        materialization.materialize(self.sbudget(), old, revision)
        return old, revision

    def test_saved_query_adapter_is_read_only_and_charges_c01(self):
        old, revision = self.saved_query()
        before = {p: p.read_bytes() for p in old.directory.rglob("*") if p.is_file()}
        saved, value, array = materialization.load(self.sbudget(), QueryView(self.owner), revision)
        self.assertEqual(array.shape, (1, 3))
        self.assertEqual(value["identity"]["consumer"]["examples"], revision["recipe"]["examples"])
        self.assertEqual(
            before, {p: p.read_bytes() for p in old.directory.rglob("*") if p.is_file()}
        )
        self.assertGreater(
            record(self.owner.directory / "work.json")["counts"]["read_audio_seconds"], 0
        )
        self.assertEqual(saved["identity"]["revision_id"], revision["revision_id"])

    def test_missing_old_context_cannot_be_silently_written(self):
        old, revision = self.saved_query()
        for path in (old.directory / "contexts").glob("*.json"):
            path.unlink()
        with self.assertRaisesRegex(InputError, "context missing"):
            materialization.load(self.sbudget(), QueryView(self.owner), revision)
        self.assertFalse(list((old.directory / "contexts").glob("*.json")))

    def test_explicit_owned_derivative_uses_validated_recipe_and_feature_hook(self):
        old, revision = self.saved_query()
        before = {p: p.read_bytes() for p in old.directory.rglob("*") if p.is_file()}
        result = index_queries.derive(self.sbudget(), self.owner, revision["revision_id"])
        self.assertIn("data/runs/indexing/query-derived/", result["query"])
        view = DerivedQueryContext(self.owner)
        _, _, array = materialization.load(self.sbudget(), view, revision)
        self.assertEqual(array.shape, (1, 3))
        self.assertTrue(list((self.owner.features / "queries").glob("*/features.npy")))
        self.assertEqual(
            before, {p: p.read_bytes() for p in old.directory.rglob("*") if p.is_file()}
        )

    def test_reader_detects_row_order_drift_and_feature_identity_changes(self):
        path, _ = self.plan()
        self.finish(path)
        snapshot_path, snap = build.bank_snapshot(self.sbudget(), self.owner, path)
        bank_value = reader.read_bank(self.sbudget(), self.owner, snapshot_path)
        array, passages = reader.rows(
            self.sbudget(), self.owner, bank_value, bank_value["committed"][0]
        )
        self.assertEqual(len(array), len(passages))
        self.assertEqual(passages[0]["row"], 0)
        self.assertEqual(passages[0]["signal_bounds"], [0, 9600])
        bad = copy.deepcopy(snap)
        bad.pop("record_hash")
        ref = bad["committed"][0]
        membership = record(self.root / ref["path"])
        membership.pop("record_hash")
        membership["identity"]["bounds"].reverse()
        write_record(self.root / ref["path"], membership, self.sbudget())
        ref["record_hash"] = record(self.root / ref["path"])["record_hash"]
        bad_path = self.owner.indexes / "banks" / (digest(bad) + ".json")
        write_record(bad_path, bad, self.sbudget())
        with self.assertRaisesRegex(InputError, "row order"):
            reader.read_bank(self.sbudget(), self.owner, bad_path)

    def test_complete_exact_rank_preserves_exclusions_and_original_baseline(self):
        signals = {
            s["signal_id"]: s
            for s in (
                self.signal("a", group="duplicate"),
                self.signal("b", group="duplicate"),
                self.signal("c", group="other"),
                self.signal("d", group="excluded"),
            )
        }
        path, _ = self.plan(signals)
        self.finish(path)
        snapshot_path, _ = build.bank_snapshot(self.sbudget(), self.owner, path)
        value = reader.read_bank(self.sbudget(), self.owner, snapshot_path)
        value["schema_version"] = "c01-legacy-reference-1"
        q = {
            "record_hash": "q" * 64,
            "identity": {"excluded_groups": ["c01-family-excluded"], "representation": self.desc},
            "examples": [
                {
                    "audio": {"duration_seconds": 2},
                    "prepared": {
                        "source": {"sha256": "different"},
                        "technical_metadata": {"canonical_pcm": {"sha256": "different"}},
                    },
                }
            ],
        }
        revision = {"revision_id": self.owner.protocol["delivery"]["revision"]}
        expected = []
        for key in ("a", "c"):
            unit = next(u for u in value["committed"] if u["signal_id"] == key)
            # Scalar independent cosine, compared over every native window.
            array = np.load(self.root / unit["path"] / "features.npy", allow_pickle=False)
            scores = [
                1
                - sum(float(a) * float(b) for a, b in zip([1, 2, 3], row, strict=True))
                / (np.sqrt(14) * np.sqrt(sum(float(v) ** 2 for v in row)))
                for row in array
            ]
            best = min(
                range(len(scores)), key=lambda i: (scores[i], *unit["identity"]["bounds"][i])
            )
            a, b = unit["identity"]["bounds"][best]
            expected.append(
                {
                    "recording_id": key,
                    "group": signals[key]["original"]["group"],
                    "start_frame": a,
                    "end_frame": b,
                    "score": scores[best],
                    "timbre_distance": scores[best],
                    "per_example_distances": [scores[best]],
                    "pitch_contribution": 0,
                    "pitch": {"hz": None, "reason": "pitch preference off"},
                    "source": signals[key]["original"],
                    "duration_mismatch_seconds": [(b - a) / 8000 - 2],
                }
            )
        # Exact binary equality belongs to the protected matrix-distance baseline;
        # the independent scalar check above establishes direction with tolerance.
        from similar_sound_search.search.ranking import distances, timbre_key

        for h in expected:
            unit = next(u for u in value["committed"] if u["signal_id"] == h["recording_id"])
            array = np.load(self.root / unit["path"] / "features.npy", allow_pickle=False)
            _, scores = distances([[1, 2, 3]], array, "cosine")
            i = unit["identity"]["bounds"].index([h["start_frame"], h["end_frame"]])
            self.assertAlmostEqual(h["score"], scores[i], places=14)
            h.update(
                score=float(scores[i]),
                timbre_distance=float(scores[i]),
                per_example_distances=[float(scores[i])],
            )
        expected.sort(key=timbre_key)
        baseline_winners = self.root / "data/runs/queries/winners/test.json"
        write_record(baseline_winners, {"complete": True, "winners": expected}, self.sbudget())
        baseline_path = (
            self.root
            / "data/runs/queries/executions"
            / (self.owner.protocol["delivery"]["baseline_execution"] + ".json")
        )
        write_record(
            baseline_path,
            {
                "identity": {
                    "query_hash": q["record_hash"],
                    "winners_hash": record(baseline_winners)["record_hash"],
                },
                "winners": baseline_winners.relative_to(self.root).as_posix(),
                "excluded_groups": q["identity"]["excluded_groups"],
            },
            self.sbudget(),
        )
        with (
            patch.object(reader, "read_bank", return_value=value),
            patch.object(
                index_queries,
                "load",
                return_value=(
                    revision,
                    {"materialization_id": "m"},
                    q,
                    np.asarray([[1, 2, 3]], np.float32),
                ),
            ),
        ):
            result = ranking.step({"input": str(snapshot_path)}, self.sbudget(), self.owner)
        self.assertTrue(result["baseline_equivalence"]["passed"])
        execution = record(self.root / result["execution"])
        self.assertEqual(execution["winners"], expected)
        self.assertEqual(execution["eligible_groups"], 2)

    def test_per_bank_listener_exports_native_samples_and_verifies_new_controls(self):
        from similar_sound_search.indexing import report

        old, revision = self.saved_query()
        saved, q, features_array = materialization.load(
            self.sbudget(), QueryView(self.owner), revision
        )
        self.owner.protocol["delivery"]["revision"] = revision["revision_id"]
        signals = {
            s["signal_id"]: s
            for s in (
                self.signal("candidate-one", seconds=3),
                self.signal("candidate-two", seconds=2.7),
            )
        }
        refs = []
        for duration in (1200, 4800):
            path, _ = self.plan(signals, duration=duration)
            self.finish(path)
            bank_path, bank_snapshot = build.bank_snapshot(self.sbudget(), self.owner, path)
            refs.append(
                {
                    "record_hash": bank_snapshot["record_hash"],
                    "kind": "original",
                    "grid": {"window_milliseconds": duration, "hop_milliseconds": 500},
                }
            )
            with patch.object(
                index_queries, "load", return_value=(revision, saved, q, features_array)
            ):
                ranking.step({"input": str(bank_path)}, self.sbudget(), self.owner)
        path = self.owner.indexes / "snapshots/test.json"
        write_record(path, {"banks": refs}, self.sbudget())
        write_record(
            self.owner.directory / "snapshot.json",
            {"snapshot": path.relative_to(self.root).as_posix()},
            self.sbudget(),
        )
        write_record(
            self.owner.directory / "admission.json", {"state": "fixture-only"}, self.sbudget()
        )
        write_record(
            self.owner.directory / "development/comparison.json", {"summary": {}}, self.sbudget()
        )
        write_record(
            self.owner.directory / "support-verification.json",
            {
                "passed": True,
                "admission_unchanged": True,
                "strict_full_2400ms": {},
                "comparison_hash": record(self.owner.directory / "development/comparison.json")[
                    "record_hash"
                ],
                "decision_hash": record(self.owner.directory / "admission.json")["record_hash"],
            },
            self.sbudget(),
        )
        with patch.object(index_queries, "load", return_value=(revision, saved, q, features_array)):
            result = report.build(self.sbudget(), self.owner)
        self.assertEqual(result["items"], 6)
        self.assertTrue(report.verify_native(self.sbudget(), self.owner)["passed"])
        content = (self.root / result["report"]).read_text(encoding="utf-8")
        self.assertIn('id="audio-5"', content)
        self.assertIn('id="seek-5"', content)
        self.assertIn(
            "no presence threshold",
            record(next((self.owner.directory / "executions").glob("*.json")))["metric"],
        )
