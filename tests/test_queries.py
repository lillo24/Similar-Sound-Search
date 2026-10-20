"""Independent B03 recipes, bindings, PCM reuse and preference answers; no model/network."""

import copy
import json
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase
from scipy.io.wavfile import write as write_wav

from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.events import compatibility
from similar_sound_search.inputs import decode
from similar_sound_search.preparation import prepare
from similar_sound_search.queries import (
    assets,
    commands,
    features,
    library,
    materialization,
    pitch,
)
from similar_sound_search.queries.context import Context, TransformContext
from similar_sound_search.queries.job import run
from similar_sound_search.queries.report import page
from similar_sound_search.queries.validation import known_answers
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.search import query, sources
from similar_sound_search.search.contracts import recipe_code
from similar_sound_search.separation import artifacts
from similar_sound_search.storage import InputError, ResourceError, sha256

SELECT = {
    "origin": "manual native fixture",
    "version": "test-1",
    "complete": True,
    "uncertainty": [],
}


class FixtureModel:
    def __init__(self):
        self.calls = 0

    def encode(self, samples, rate):
        self.calls += 1
        return np.array(
            [
                1 + np.sqrt(np.mean(samples.astype(float) ** 2)),
                2 + np.mean(samples),
                3 + np.max(samples),
            ],
            np.float32,
        )


class QueriesCase(AudioCase):
    def setUp(self):
        super().setUp()
        for name in ("queries.json", "separation.json", "search.json"):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        self.owner = Context(self.root)
        self.desc = {
            "method": "efficientat",
            "dimension": 3,
            "distance": "cosine",
            "fixture_only": True,
        }
        self.model = FixtureModel()
        for p in (
            patch.object(sources, "catalogue", return_value=([], {"entry_groups": {}})),
            patch.object(query, "frozen", return_value=({}, {}, {}, {}, self.desc)),
            patch.object(materialization, "frozen", return_value=({}, {}, {}, {}, self.desc)),
            patch.object(features, "adapter", return_value=(self.model, 0)),
        ):
            p.start()
            self.addCleanup(p.stop)

    def sbudget(self):
        return CatalogueBudget(
            self.root, load_limits(self.root / "config/resource_limits.json", "starter")
        )

    def signal(self, name="signal", rate=8000, samples=None, context=None):
        if samples is None:
            t = np.arange(rate * 4) / rate
            samples = np.sin(2 * np.pi * 220 * t)[:, None].astype(np.float32) * 0.1
        path = self.root / "data/audio/originals" / (name + ".wav")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(path, rate, samples)
        result = assets.register(self.sbudget(), self.owner, path, context)
        return path, result["asset_id"], samples

    def spec(self, asset_id, event=None, context=None):
        return {
            "schema_version": "b03-query-input-1",
            "examples": [
                {
                    "asset_id": asset_id,
                    "event": event or [8000, 24000],
                    "context": context or [4000, 28000],
                    "selection": SELECT,
                }
            ],
        }

    def saved(self, spec=None):
        if spec is None:
            _, asset_id, _ = self.signal()
            spec = self.spec(asset_id)
        created = library.save(self.sbudget(), self.owner, spec, "Fixture")
        return created, library.revision(self.owner, created["revision_id"])

    def test_recipe_round_trip_reorder_duplicate_and_unique_pcm(self):
        _, asset_id, _ = self.signal()
        first = self.spec(asset_id)["examples"][0]
        second = {**first, "event": [0, 8000], "context": [0, 28000]}
        a, rev = self.saved(
            {"schema_version": "b03-query-input-1", "examples": [first, second, first]}
        )
        b, _ = self.saved({"schema_version": "b03-query-input-1", "examples": [second, first]})
        self.assertEqual(a["revision_id"], b["revision_id"])
        first_result = materialization.materialize(self.sbudget(), self.owner, rev)
        _, q, rows = materialization.load(self.sbudget(), self.owner, rev)
        again = materialization.materialize(self.sbudget(), self.owner, rev)
        self.assertTrue(again["reused"])
        self.assertEqual(first_result["query_id"], again["query_id"])
        self.assertEqual(len(q["examples"]), 2)
        self.assertEqual(rows.shape, (2, 3))
        self.assertEqual(self.model.calls, 2)

    def test_native_nonzero_44100_bounds_preserve_exact_samples_and_unknown_offset(self):
        _, asset_id, original = self.signal(rate=44100)
        _, rev = self.saved(self.spec(asset_id, [44101, 88217], [22050, 110250]))
        materialization.materialize(self.sbudget(), self.owner, rev)
        _, q, _ = materialization.load(self.sbudget(), self.owner, rev)
        value = q["examples"][0]
        actual, _ = decode(self.root / value["prepared"]["artifact"]["local_path"], self.sbudget())
        np.testing.assert_array_equal(actual, original[44101:88217])
        _, _, validated_source = assets.read_asset(
            self.sbudget(), self.owner, asset_id, with_samples=True
        )
        np.testing.assert_array_equal(validated_source, original)
        self.assertIsNone(
            value["prepared"]["timestamp_mapping"]["original_recording_offset_seconds"]
        )

    def test_same_selected_pcm_from_different_parents_retains_both_exclusions(self):
        t = np.arange(16000) / 8000
        selected = (0.1 * np.sin(2 * np.pi * 220 * t))[:, None].astype(np.float32)
        a, aid, _ = self.signal(
            "a", samples=np.vstack((selected, np.ones((8000, 1), np.float32) * 0.03))
        )
        b, bid, _ = self.signal(
            "b", samples=np.vstack((np.ones((8000, 1), np.float32) * 0.02, selected))
        )
        population = []
        for key, path in (("a", a), ("b", b)):
            _, meta = decode(path, self.sbudget())
            population.append(
                {"entry_id": key, "source_asset": meta, "analysis_derivative": {"sha256": "never"}}
            )
        with patch.object(
            sources,
            "catalogue",
            return_value=(population, {"entry_groups": {"a": "parent-a", "b": "parent-b"}}),
        ):
            first = self.spec(aid, [0, 16000], [0, 24000])["examples"][0]
            second = self.spec(bid, [8000, 24000], [0, 24000])["examples"][0]
            _, rev = self.saved(
                {"schema_version": "b03-query-input-1", "examples": [first, second]}
            )
            materialization.materialize(self.sbudget(), self.owner, rev)
            _, q, array = materialization.load(self.sbudget(), self.owner, rev)
            self.assertEqual(array.shape, (1, 3))
            self.assertEqual(q["identity"]["excluded_groups"], ["parent-a", "parent-b"])
            self.assertEqual(len(q["identity"]["consumer"]["examples"]), 2)
            self.assertEqual(self.model.calls, 1)

    def test_label_and_pitch_revision_reuse_same_audio_and_features(self):
        created, rev = self.saved()
        first = materialization.materialize(self.sbudget(), self.owner, rev)
        head = record(library.name_path(self.owner, created["query_id"]))
        library.change_name(
            self.sbudget(),
            self.owner,
            created["query_id"],
            head["record_hash"],
            name="Renamed <display>",
        )
        recipe = copy.deepcopy(rev["recipe"])
        recipe["pitch"] = self.owner.cfg["pitch"]
        changed = library.save(
            self.sbudget(),
            self.owner,
            recipe,
            "Renamed <display>",
            created["query_id"],
            created["revision_id"],
        )
        newer = library.revision(self.owner, changed["revision_id"])
        second = materialization.materialize(self.sbudget(), self.owner, newer)
        self.assertNotEqual(created["revision_id"], changed["revision_id"])
        self.assertEqual(first["query_id"], second["query_id"])
        self.assertTrue(second["reused"])
        self.assertEqual(self.model.calls, 1)
        self.assertEqual(
            library.revision(self.owner, created["revision_id"])["recipe"]["pitch"]["weight"], 0
        )

    def test_show_list_and_rename_do_not_infer_or_require_media(self):
        created, rev = self.saved()
        assets_path = assets.read_binding(self.owner, rev["recipe"]["examples"][0]["asset_id"])[
            "path"
        ]
        (self.root / assets_path).unlink()
        with patch.object(features, "adapter", side_effect=AssertionError("hidden inference")):
            shown = commands.dispatch(
                {"queries_action": "show", "query_id": created["query_id"]},
                self.sbudget(),
                self.owner,
            )
            listed = commands.dispatch({"queries_action": "list"}, self.sbudget(), self.owner)
        self.assertEqual(shown["revision"]["revision_id"], created["revision_id"])
        self.assertEqual(len(listed["queries"]), 1)
        self.assertEqual(
            materialization.validate(self.sbudget(), self.owner, rev)["availability_state"],
            "missing",
        )

    def test_missing_original_cannot_hide_behind_features(self):
        created, rev = self.saved()
        materialization.materialize(self.sbudget(), self.owner, rev)
        key = rev["recipe"]["examples"][0]["asset_id"]
        bound = assets.read_binding(self.owner, key)
        (self.root / bound["path"]).unlink()
        with self.assertRaises(FileNotFoundError):
            materialization.load(self.sbudget(), self.owner, rev)
        self.assertEqual(self.model.calls, 1)

    def test_wrong_bytes_rejected_and_bad_sha_registration_fails(self):
        path, aid, _ = self.signal()
        with self.assertRaisesRegex(InputError, "SHA256"):
            assets.register(self.sbudget(), self.owner, path, expected="0" * 64)
        write_wav(path, 8000, np.ones((32000, 1), np.float32) * 0.04)
        with self.assertRaisesRegex(InputError, "changed source"):
            assets.read_asset(self.sbudget(), self.owner, aid)

    def test_export_has_no_paths_and_unresolved_import_is_inspectable(self):
        _, rev = self.saved()
        result = library.export_recipe(self.sbudget(), self.owner, rev)
        value = record(self.root / result["export"])
        text = json.dumps(value)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn("local_path", text)
        for p in (self.owner.directory / "bindings").glob("*.json"):
            p.unlink()
        answer = library.import_recipe(self.sbudget(), self.owner, value)
        self.assertEqual(answer["state"], "unresolved")
        self.assertEqual(
            library.revision(self.owner, answer["revision_id"])["recipe"], rev["recipe"]
        )

    def test_export_refuses_absolute_metadata_and_credential_fields(self):
        for value in (
            {"password": "private"},
            {"notes": "source C:\\Users\\private.wav"},
            {"notes": "/home/example/private.wav"},
        ):
            with self.assertRaises(InputError):
                library.portable(value)
        library.portable(
            {"source_url": "https://example.org/audio/track", "notes": "source/cue metadata"}
        )

    def test_changed_cue_provenance_preserves_distinct_recipe_and_reuses_equal_pcm(self):
        path, _, _ = self.signal()
        cue = path.with_name("cue-copy.wav")
        shutil.copyfile(path, cue)
        source = {
            "path": path.relative_to(self.root).as_posix(),
            "sha256": sha256(path, self.sbudget()),
        }
        spec = {
            "schema_version": "b02-process-input-1",
            "source": source,
            "region": [0, 16000],
            "event": [2000, 14000],
            "cue": {**source, "bounds": [0, 8000]},
        }
        recipes, results = [], []
        for cue_path in (path, cue):
            changed = copy.deepcopy(spec)
            changed["cue"]["path"] = cue_path.relative_to(self.root).as_posix()
            result = artifacts.process(
                self.sbudget(), changed, "guided", TransformContext(self.owner)
            )
            _, revision = self.saved(
                {
                    "schema_version": "b03-query-input-1",
                    "examples": [
                        {
                            "transform_record": result["transform"],
                            "component": "extracted",
                            "selection": SELECT,
                        }
                    ],
                }
            )
            recipes.append(revision)
            results.append(materialization.materialize(self.sbudget(), self.owner, revision))
        self.assertNotEqual(recipes[0]["revision_id"], recipes[1]["revision_id"])
        self.assertNotEqual(results[0]["query_id"], results[1]["query_id"])
        self.assertEqual(self.model.calls, 1)
        self.assertEqual(results[1]["cache"]["reused"], 1)

    def test_explicit_relocation_preserves_recipe_and_checks_hashes(self):
        path, aid, _ = self.signal()
        _, rev = self.saved(self.spec(aid))
        export = library.export_recipe(self.sbudget(), self.owner, rev)
        value = record(self.root / export["export"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(self.root / "config", root / "config")
            target = root / "data/audio/incoming/same-audio-new-name.wav"
            target.parent.mkdir(parents=True)
            shutil.copyfile(path, target)
            owner = Context(root)
            budget = CatalogueBudget(
                root, load_limits(root / "config/resource_limits.json", "starter")
            )
            result = library.import_recipe(
                budget, owner, value, {aid: {"path": target.relative_to(root).as_posix()}}
            )
            self.assertEqual(result["revision_id"], rev["revision_id"])
            restored = library.revision(owner, rev["revision_id"])
            made = materialization.materialize(budget, owner, restored)
            self.assertEqual(made["status"], "ok")
            target.write_bytes(b"same filename, wrong bytes")
            with self.assertRaises(InputError):
                library.import_recipe(
                    budget, owner, value, {aid: {"path": target.relative_to(root).as_posix()}}
                )

    def test_explicit_rebinding_keeps_old_materialization_binding_snapshot(self):
        from similar_sound_search.queries import report
        from similar_sound_search.storage import digest

        path, aid, _ = self.signal()
        _, rev = self.saved(self.spec(aid))
        first = materialization.materialize(self.sbudget(), self.owner, rev)
        old = record(self.root / first["query"])
        captured = materialization.receipt(self.owner, rev)
        exported = record(
            self.root / library.export_recipe(self.sbudget(), self.owner, rev)["export"]
        )
        alias = path.with_name("alias.wav")
        shutil.copyfile(path, alias)
        library.import_recipe(
            self.sbudget(),
            self.owner,
            exported,
            {aid: {"path": alias.relative_to(self.root).as_posix()}},
        )
        second = materialization.materialize(self.sbudget(), self.owner, rev)
        self.assertNotEqual(first["query_id"], second["query_id"])
        self.assertEqual(self.model.calls, 1)
        q, _ = query.load_query(
            self.sbudget(), self.root / first["query"], self.desc, context=self.owner
        )
        self.assertEqual(q["record_hash"], old["record_hash"])
        identity = {
            "revision_id": rev["revision_id"],
            "pitch_policy": library.OFF,
            "materialization_id": captured["materialization_id"],
            "query_hash": old["record_hash"],
        }
        execution_path = self.owner.directory / "executions/rebound-fixture.json"
        self.owner.publish(
            self.sbudget(),
            execution_path,
            {
                "schema_version": "b03-execution-1",
                "identity": identity,
                "execution_id": digest(identity),
                "state": "complete",
                "revision": rev,
                "materialization": captured,
                "candidates": [],
            },
        )
        delivered = report.build(
            self.sbudget(),
            self.owner,
            {
                "revisions": [{"revision_id": rev["revision_id"], "label": "Older execution"}],
                "executions": [execution_path.relative_to(self.root).as_posix()],
            },
        )
        bundle = record((self.root / delivered["report"]).with_name("bundle.json"))
        self.assertEqual(bundle["summaries"][0]["query_id"], first["query_id"])
        self.assertEqual(
            bundle["items"][0]["source_audio"]["local_path"], path.relative_to(self.root).as_posix()
        )

    def test_unknown_versions_types_bounds_and_extra_fields_fail(self):
        _, aid, _ = self.signal()
        bad = self.spec(aid)
        for field, value in (
            ("event", [True, 24000]),
            ("event", [0, 40000]),
            ("context", [9000, 28000]),
        ):
            item = copy.deepcopy(bad)
            item["examples"][0][field] = value
            with self.assertRaises(InputError):
                self.saved(item)
        bad["unknown"] = 1
        with self.assertRaises(InputError):
            self.saved(bad)
        _, rev = self.saved()
        recipe = copy.deepcopy(rev["recipe"])
        recipe["schema_version"] = "future"
        with self.assertRaises(InputError):
            library.validate_recipe(recipe)

    def test_overlong_original_does_not_truncate(self):
        _, aid, _ = self.signal(samples=np.ones((8000 * 32, 1), np.float32) * 0.1)
        with self.assertRaisesRegex(InputError, "thirty seconds"):
            self.saved(self.spec(aid, [0, 8000 * 31], [0, 8000 * 32]))

    def test_wrong_parent_map_rejected_after_registration(self):
        path, _, _ = self.signal()
        parent = prepare(path, self.sbudget(), 8000, "preserve", ".1", "3.5")
        parent_path = self.root / parent["bundle"] / "record.json"
        registered = assets.register(
            self.sbudget(),
            self.owner,
            self.root / parent["record"]["artifact"]["local_path"],
            parent_path=parent_path,
        )
        value = record(parent_path)
        value["timestamp_mapping"]["segments"][0]["source_start_seconds"] = 20
        write_record(parent_path, value, self.sbudget())
        with self.assertRaisesRegex(InputError, "wrong parent/map"):
            assets.read_asset(self.sbudget(), self.owner, registered["asset_id"])

    def test_corrupt_feature_and_interrupted_materialization_are_explicit(self):
        _, rev = self.saved()
        made = materialization.materialize(self.sbudget(), self.owner, rev)
        q = record(self.root / made["query"])
        (self.root / made["query"]).parent.joinpath(
            "features", q["feature_key"], "features.npy"
        ).write_bytes(b"corrupt")
        with self.assertRaisesRegex(InputError, "corrupt array"):
            materialization.load(self.sbudget(), self.owner, rev)
        self.owner.publish(
            self.sbudget(),
            materialization.state_path(self.owner, rev["revision_id"]),
            {"state": "in_progress", "revision_id": rev["revision_id"]},
        )
        with self.assertRaisesRegex(InputError, "interrupted"):
            materialization.receipt(self.owner, rev)

    def test_concurrent_revision_cas_and_display_conflicts(self):
        created, rev = self.saved()

        def update(n):
            recipe = copy.deepcopy(rev["recipe"])
            recipe["examples"][0]["event"] = [8000 + n, 24000]
            try:
                return library.save(
                    self.sbudget(),
                    self.owner,
                    recipe,
                    "Concurrent",
                    created["query_id"],
                    rev["revision_id"],
                )["status"]
            except (InputError, ResourceError):
                return "conflict"

        with ThreadPoolExecutor(2) as pool:
            answers = list(pool.map(update, (1, 2)))
        self.assertEqual(sorted(answers), ["conflict", "ok"])
        head = record(library.name_path(self.owner, created["query_id"]))
        with self.assertRaisesRegex(InputError, "conflict"):
            library.change_name(
                self.sbudget(), self.owner, created["query_id"], "0" * 64, name="stale"
            )
        selected = library.change_name(
            self.sbudget(),
            self.owner,
            created["query_id"],
            head["record_hash"],
            selected=rev["revision_id"],
        )
        self.assertEqual(selected["name"]["selected"], rev["revision_id"])

    def test_corrupt_revision_and_interrupted_partial_do_not_overwrite(self):
        _, rev = self.saved()
        target = library.revision_path(self.owner, rev["revision_id"])
        target.write_text('{"partial":', encoding="utf-8")
        with self.assertRaises(InputError):
            library.revision(self.owner, rev["revision_id"])
        with self.assertRaises(InputError):
            self.owner.publish(self.sbudget(), target, {"different": True}, immutable=True)

    def test_historical_guided_reuse_is_b03_charged_and_cue_is_not_vote(self):
        path, _, _ = self.signal()
        source = {
            "path": path.relative_to(self.root).as_posix(),
            "sha256": sha256(path, self.sbudget()),
        }
        spec = {
            "schema_version": "b02-process-input-1",
            "source": source,
            "region": [0, 16000],
            "event": [2000, 14000],
            "cue": {**source, "bounds": [0, 8000]},
        }
        result = artifacts.process(
            self.sbudget(), spec, "guided", TransformContext(self.owner, historical=True)
        )
        _, rev = self.saved(
            {
                "schema_version": "b03-query-input-1",
                "examples": [
                    {
                        "transform_record": result["transform"],
                        "component": "extracted",
                        "selection": SELECT,
                    }
                ],
            }
        )
        materialization.materialize(self.sbudget(), self.owner, rev)
        _, q, rows = materialization.load(self.sbudget(), self.owner, rev)
        self.assertEqual(rows.shape[0], 1)
        self.assertEqual(len(q["examples"]), 1)
        self.assertIsNotNone(rev["recipe"]["examples"][0]["transform"]["cue"])
        self.assertFalse((self.root / "data/runs/separation/ledger.json").exists())
        self.assertFalse((self.root / "data/runs/separation/work.json").exists())
        self.assertGreater(
            record(self.owner.directory / "work.json")["counts"]["read_audio_seconds"], 0
        )
        changed = copy.deepcopy(spec)
        changed["cue"]["bounds"] = [8000, 16000]
        newer = artifacts.process(self.sbudget(), changed, "guided", TransformContext(self.owner))
        self.assertNotEqual(result["transform"], newer["transform"])
        cue_path = self.root / "data/audio/originals/cue-missing.wav"
        shutil.copyfile(path, cue_path)
        self.assertFalse((self.root / "data/runs/separation/ledger.json").exists())

    def test_missing_historical_cue_and_wrong_component_fail(self):
        path, _, _ = self.signal()
        cue = path.with_name("cue.wav")
        shutil.copyfile(path, cue)
        spec = {
            "schema_version": "b02-process-input-1",
            "source": {
                "path": path.relative_to(self.root).as_posix(),
                "sha256": sha256(path, self.sbudget()),
            },
            "region": [0, 16000],
            "event": [0, 12000],
            "cue": {
                "path": cue.relative_to(self.root).as_posix(),
                "sha256": sha256(cue, self.sbudget()),
                "bounds": [0, 8000],
            },
        }
        result = artifacts.process(
            self.sbudget(), spec, "guided", TransformContext(self.owner, historical=True)
        )
        value = record(self.root / result["transform"])
        with self.assertRaisesRegex(InputError, "absent"):
            assets.transform_descriptor(value, "original")
        descriptor = assets.bind_transform(
            self.sbudget(), self.owner, self.root / result["transform"], "extracted"
        )
        cue.unlink()
        with self.assertRaises(InputError):
            assets.read_transform(self.sbudget(), self.owner, descriptor)

    def test_retained_failed_worker_accounting_and_zero_network(self):
        request = {
            "root": str(self.root),
            "limits": self.sbudget().limits,
            "queries_action": "show",
        }
        for _ in range(2):
            value = run(
                request, lambda _: {"status": "failed", "error": "explicit fixture failure"}
            )
            self.assertEqual(value["status"], "failed")
        counts = record(self.owner.directory / "work.json")["counts"]
        self.assertEqual(counts["workers"], 2)
        ledger = json.loads((self.owner.directory / "ledger.json").read_text(encoding="utf-8"))
        self.assertGreater(ledger["charged_worker_seconds"], 0)
        self.assertEqual(ledger["pending_worker_seconds"], 0)
        self.assertEqual(ledger["http_attempts"], 0)
        with self.assertRaises(ResourceError):
            self.owner.charge(self.sbudget(), query_jobs=17)

    def test_pitch_answers_register_mean_abstention_and_invalid_policy(self):
        result = known_answers(self.sbudget(), self.owner)
        self.assertEqual(result["eligible_coverage"], "3/3")
        self.assertEqual(len(result["abstentions"]), 4)
        self.assertEqual(result["multiple_notes"]["value"], 0.015)
        estimate = {"hz": 220, "reason": "fixture", "reliable_blocks": 2}
        other = {"hz": 880, "reason": "fixture", "reliable_blocks": 2}
        self.assertEqual(
            pitch.contribution([estimate], other, self.owner.cfg["pitch"])["value"], 0.03
        )
        for weight in (True, float("nan"), 0.051, -0.01):
            with self.assertRaises(InputError):
                pitch.contribution(
                    [estimate],
                    other,
                    {"version": "b03-pitch-1", "weight": weight, "scale_semitones": 12},
                )

    def test_all_query_abstentions_keep_timbre_order_and_cache_support_bound(self):
        missing = {"hz": None, "reason": "mixed", "reliable_blocks": 0}
        candidates = [{"hz": v, "reason": "fixture", "reliable_blocks": 2} for v in (110, 220, 440)]
        self.assertEqual(
            [
                pitch.contribution([missing], v, self.owner.cfg["pitch"])["value"]
                for v in candidates
            ],
            [0, 0, 0],
        )
        _, _, x = self.signal()
        first = pitch.cached_estimate(self.sbudget(), self.owner, x[:16000], 8000)
        second = pitch.cached_estimate(self.sbudget(), self.owner, x[:16000], 8000)
        self.assertEqual(first, second)
        self.assertNotEqual(first["provenance"], pitch.estimate_identity(x[:8000], 8000))

    def test_legacy_guard_stays_closed_and_audited_pitch_bytes_unchanged(self):
        with self.assertRaises(InputError):
            recipe_code(REPOSITORY)
        value = compatibility.audit(REPOSITORY)
        self.assertIn("search/pitch.py", value["current_consumer_code"])

    def test_report_labels_are_escaped_and_derived_original_roles_visible(self):
        value = {
            "summaries": [{"label": '<script>alert("x")</script>', "revision_id": "a" * 64}],
            "items": [],
        }
        content = page(value)
        self.assertNotIn('<script>alert("x")', content)
        self.assertIn("&lt;script&gt;", content)
        self.assertIn("pitch off", content)
        self.assertIn("master alignment", content)

    def test_complete_winners_reorders_eleventh_without_changing_timbre_passage(self):
        from similar_sound_search.queries import execution
        from similar_sound_search.search import ranking
        from similar_sound_search.storage import digest

        base = self.root / "data/indexes/a06" / compatibility.INDEX
        base.mkdir(parents=True)
        receipt_path = self.owner.directory / "compatibility" / ("a" * 64 + ".json")
        write_record(receipt_path, {"fixture": "explicit trusted-boundary stub"}, self.sbudget())
        self.owner.receipt = record(receipt_path)
        self.owner.receipt_path = receipt_path
        estimate = {"hz": 220, "reason": "fixture", "reliable_blocks": 2}
        qidentity = {"excluded_groups": [], "examples": ["fixture"]}
        q = {
            "query_id": digest(qidentity),
            "identity": qidentity,
            "record_hash": "b" * 64,
            "examples": [
                {
                    "pitch": estimate,
                    "audio": {"duration_seconds": 1},
                    "prepared": {
                        "source": {"sha256": "f" * 64},
                        "technical_metadata": {"canonical_pcm": {"sha256": "e" * 64}},
                    },
                }
            ],
        }
        manifest = {"index_id": compatibility.INDEX, "entries": {}, "state": "complete"}
        arrays = {}
        for i in range(11):
            key = f"recording-{i:02d}"
            source = {
                "recording_id": key,
                "group": key,
                "kind": "engineering",
                "source": {
                    "sha256": digest(key),
                    "canonical_pcm": {"sha256": digest([key])},
                    "sample_rate_hz": 100,
                    "duration_seconds": 2,
                },
            }
            shard = digest([i, "shard"])
            identity = {"dimension": 3, "bounds": [[0, 100], [100, 200]]}
            values = [0.0025 * i, 0.0025 * i + 0.001]
            vectors = np.array([[1 - d, np.sqrt(1 - (1 - d) ** 2), 0] for d in values], np.float32)
            arrays[shard] = vectors
            write_record(
                base / "shards" / shard / "record.json", {"identity": identity}, self.sbudget()
            )
            write_record(
                base / "entries" / (key + ".json"),
                {"source": source, "shards": [shard]},
                self.sbudget(),
            )
            manifest["entries"][key] = "complete"
        cfg = {"results": 10, "pitch_weight_max": 0.05}

        def array(directory, *_):
            return arrays[directory.name], {}

        def samples(_budget, source, **_):
            i = int(source["recording_id"].split("-")[-1])
            return np.vstack(
                (np.full((100, 1), i + 1, np.float32), np.full((100, 1), i + 101, np.float32))
            )

        def candidate_pitch(_budget, _owner, sample, _rate):
            return {
                "hz": 220 if sample[0, 0] == 11 else 440,
                "reason": "fixture",
                "reliable_blocks": 2,
            }

        made = {"identity": {"query_id": q["query_id"]}, "materialization_id": "c" * 64}
        with (
            patch.object(ranking, "open_index", return_value=(base, manifest, self.desc, cfg)),
            patch.object(
                ranking, "load_query", return_value=(q, np.array([[1, 0, 0]], np.float32))
            ),
            patch.object(ranking, "load_array", side_effect=array),
            patch.object(ranking, "coverage", return_value={"recordings": 11}),
            patch.object(execution, "open_index", return_value=(base, manifest, self.desc, cfg)),
            patch.object(execution, "load_array", side_effect=array),
            patch.object(sources, "load", side_effect=samples),
            patch.object(materialization, "receipt", return_value=made),
            patch.object(
                materialization, "load", return_value=(made, q, np.array([[1, 0, 0]], np.float32))
            ),
            patch.object(pitch, "cached_estimate", side_effect=candidate_pitch),
        ):
            request = {"index": base / "index.json", "query": "fixture", "cursor": 0}
            while True:
                result = ranking.rank(request, self.sbudget(), self.owner)
                if result.get("state") != "in_progress":
                    break
                request["cursor"] = result["cursor"]
            original = record(self.root / result["result"])
            self.assertEqual(len(original["candidates"]), 10)
            lookup = record(
                execution.lookup_path(self.owner, q["query_id"], self.owner.receipt["record_hash"])
            )
            winners_path = self.root / lookup["winners"]
            winners = record(winners_path)
            self.assertEqual(len(winners["winners"]), 11)
            revision = {"revision_id": "d" * 64, "recipe": {"pitch": self.owner.cfg["pitch"]}}
            request = {"index": base / "index.json", "receipt": receipt_path, "cursor": 0}
            for _ in range(3):
                result = execution.step(request, self.sbudget(), self.owner, revision)
            ranked = record(self.root / result["execution"])
            self.assertEqual(ranked["candidates"][0]["recording_id"], "recording-10")
            self.assertTrue(
                all(
                    v["start_frame"] == 0 and v["end_frame"] == 100
                    for v in ranked["complete_ranking"]
                )
            )
            self.assertEqual(len(ranked["complete_ranking"]), 11)
            revision = {"revision_id": "e" * 64, "recipe": {"pitch": library.OFF}}
            for _ in range(3):
                result = execution.step(request, self.sbudget(), self.owner, revision)
                request["cursor"] = result.get("cursor", 0)
            off = record(self.root / result["execution"])
            self.assertEqual(
                [v["recording_id"] for v in off["candidates"]],
                [v["recording_id"] for v in original["candidates"]],
            )
            self.assertEqual(
                [v["score"] for v in off["candidates"]],
                [v["score"] for v in original["candidates"]],
            )
            winners["winners"] = winners["winners"][:10]
            write_record(winners_path, winners, self.sbudget())
            with self.assertRaisesRegex(InputError, "top-ten reranking refused"):
                execution.validate_winners(
                    self.sbudget(), self.owner, winners_path, base / "index.json", q
                )

    def test_processed_player_maps_compose_parent_offset_and_independent_qa_rejects_shift(self):
        from similar_sound_search.queries import report, validation
        from similar_sound_search.storage import digest

        path, _, _ = self.signal(rate=44100)
        prepared = prepare(path, self.sbudget(), 22050, "preserve", ".25", "3.75")
        parent_path = prepared["bundle"] + "/record.json"
        audio_path = self.root / prepared["record"]["artifact"]["local_path"]
        spec = {
            "schema_version": "b02-process-input-1",
            "source": {
                "path": audio_path.relative_to(self.root).as_posix(),
                "sha256": sha256(audio_path, self.sbudget()),
                "parent_record": parent_path,
            },
            "region": [2205, 33075],
            "event": [4410, 26460],
        }
        processed = artifacts.process(self.sbudget(), spec, "broad", TransformContext(self.owner))
        _, rev = self.saved(
            {
                "schema_version": "b03-query-input-1",
                "examples": [
                    {
                        "transform_record": processed["transform"],
                        "component": "harmonic",
                        "selection": SELECT,
                    }
                ],
            }
        )
        materialization.materialize(self.sbudget(), self.owner, rev)
        captured = materialization.receipt(self.owner, rev)
        identity = {
            "revision_id": rev["revision_id"],
            "pitch_policy": library.OFF,
            "materialization_id": captured["materialization_id"],
            "query_hash": captured["identity"]["query_hash"],
        }
        execution_path = self.owner.directory / "executions/fixture.json"
        self.owner.publish(
            self.sbudget(),
            execution_path,
            {
                "schema_version": "b03-execution-1",
                "identity": identity,
                "execution_id": digest(identity),
                "state": "complete",
                "revision": rev,
                "materialization": captured,
                "candidates": [],
            },
        )
        result = report.build(
            self.sbudget(),
            self.owner,
            {
                "revisions": [{"revision_id": rev["revision_id"], "label": "Composed fixture"}],
                "executions": [execution_path.relative_to(self.root).as_posix()],
            },
        )
        summary_path = self.json_file("reports/local/report-b03-fixture.json", result)
        bundle_path = (self.root / result["report"]).with_name("bundle.json")
        bundle = record(bundle_path)
        self.assertAlmostEqual(bundle["items"][0]["available_file_zero_seconds"], 0.35)
        self.assertAlmostEqual(bundle["items"][-1]["available_file_zero_seconds"], 0.45)
        answer = validation.native(self.sbudget(), self.owner, summary_path)
        self.assertEqual(answer["native_items"], 3)
        bundle["items"][-1]["source_origin_seconds"] += 1
        bundle["items"][-1]["available_file_zero_seconds"] += 1
        write_record(bundle_path, bundle, self.sbudget())
        with self.assertRaisesRegex(InputError, "origin disagrees"):
            validation.native(self.sbudget(), self.owner, summary_path)

    def test_complete_disposable_batch_and_resume_retains_failures_without_new_inference(self):
        from similar_sound_search.queries import development

        ready = development.preflight(self.sbudget(), self.owner)
        plan = record(self.root / ready["plan"])
        silent = next(v for v in plan["cases"] if v["case_id"] == "silence")
        self.assertFalse(silent["signal"]["geometry"]["full_generated_attack_release"])
        self.assertFalse(silent["input"]["examples"][0]["selection"]["complete"])
        public = self.root / "manifests/queries/development.json"
        public.parent.mkdir(parents=True)
        shutil.copyfile(self.root / ready["plan"], public)
        with patch.object(development, "frozen", return_value=({}, {}, {}, {}, self.desc)):
            for _ in range(8):
                result = development.step(self.sbudget(), self.owner)
            summary = record(self.root / result["summary"])
            self.assertEqual(summary["primary_denominator"], 6)
            self.assertEqual(summary["diagnostic_denominator"], 2)
            self.assertEqual(summary["failures"], ["silence"])
            self.assertEqual(summary["round_trip_exact_cases"], 7)
            calls = self.model.calls
            again = development.step(self.sbudget(), self.owner)
            self.assertEqual(again["summary"], result["summary"])
            self.assertEqual(calls, self.model.calls)
        counts = record(self.owner.directory / "work.json")["counts"]
        self.assertEqual(counts["comparisons"], 1)
        self.assertEqual(counts["comparison_cases"], 8)
        self.assertEqual(counts["comparison_queries"], 16)
        self.assertFalse((self.root / "data/runs/search/ledger.json").exists())
