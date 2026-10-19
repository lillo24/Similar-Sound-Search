"""Complete B01 comparison/resumption in a disposable project with a fake adapter."""

import shutil
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase
from scipy.io.wavfile import write as write_wav

from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.evaluation.protocol import comparison_pair
from similar_sound_search.events import comparison
from similar_sound_search.events.context import Context
from similar_sound_search.inputs import decode
from similar_sound_search.preparation import versions
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.storage import digest


class ComparisonCase(AudioCase):
    def test_fixed_batch_resumes_without_another_model_run_or_legacy_writes(self):
        for name in ("events.json", "search.json"):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        budget = CatalogueBudget(
            self.root, load_limits(self.root / "config/resource_limits.json", "starter")
        )
        owner = Context(self.root)
        assets = []
        for hz in (220, 440):
            identity = {"version": "a04-suite-1", "tools": versions(), "recipe": {"hz": hz}}
            key = digest(identity)
            path = self.root / "data/audio/evaluation/generated" / (key + ".wav")
            path.parent.mkdir(parents=True, exist_ok=True)
            x = np.zeros((19200, 1), np.float32)
            x[800:8800, 0] = 0.1 * np.sin(2 * np.pi * hz * np.arange(8000) / 8000)
            write_wav(path, 8000, x)
            _, meta = decode(path, budget)
            write_record(
                self.root / "manifests/evaluation/assets" / (key + ".json"),
                {
                    "asset_id": key,
                    "identity": identity,
                    "audio": meta,
                    "local_path": path.relative_to(self.root).as_posix(),
                    "split": "development",
                    "events": [{"start_frame": 800, "end_frame": 8800}],
                },
                budget,
            )
            assets.append(key)
        query = {
            "query_id": "fixture-query",
            "query_asset_id": assets[0],
            "split": "development",
            "condition": "performance",
            "task": "controlled",
            "candidate_assets": assets,
            "targets": [{"asset_id": assets[0], "start_frame": 0, "end_frame": 19200}],
        }
        suite = {"queries": [query], "assets": assets, "record_hash": "test-suite"}
        case = {
            "query_id": query["query_id"],
            "stratum": "clean:fixture",
            "reference_asset": assets[0],
            "region": [0, 19200],
            "truth_asset": assets[0],
            "silence": False,
        }
        original_plan = record(REPOSITORY / "manifests/events/development.json")
        write_record(
            self.root / "manifests/events/development.json",
            {**original_plan, "historical_suite_hash": suite["record_hash"], "cases": [case]},
            budget,
        )
        write_record(
            self.root / "manifests/search/final-check.json",
            {
                "binding": {
                    "search_configuration": original_plan["configuration"]
                    | {"window_milliseconds": 2400, "hop_milliseconds": 250}
                }
            },
            budget,
        )
        desc = {"dimension": 2, "distance": "euclidean", "method": "fixture"}

        class Fake:
            def encode(self, samples, rate):
                return np.array([0.1, len(samples) / rate], np.float32)

        protocol, _ = comparison_pair(REPOSITORY)
        with (
            patch.object(comparison, "comparison_pair", return_value=(protocol, suite)),
            patch.object(comparison, "frozen", return_value=({}, {}, {}, {}, desc)),
            patch.object(comparison, "adapter", return_value=(Fake(), 0)),
        ):
            first = comparison.step(budget, owner)
            self.assertEqual(first["state"], "in_progress")
            self.assertEqual(first["completed_cases"], 1)
            with patch.object(
                comparison, "adapter", side_effect=AssertionError("repeated inference")
            ):
                done = comparison.step(budget, owner)
                repeated = comparison.step(budget, owner)
        self.assertEqual(done["status"], "ok")
        self.assertEqual(done["retrieval_totals"], repeated["retrieval_totals"])
        self.assertEqual(done["cases"], 1)
        self.assertEqual(record(owner.directory / "work.json")["counts"]["comparisons"], 1)
        self.assertFalse((self.root / "data/runs/search/work.json").exists())
        self.assertFalse((self.root / "data/runs/matchers/work.json").exists())
