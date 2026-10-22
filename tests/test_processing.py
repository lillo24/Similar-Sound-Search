"""Isolated C04 correctness/fault tests; no delivery inputs, model or pool is used."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.processing import api, cache, contracts, job, validation
from similar_sound_search.processing.context import Context
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.storage import InputError, ResourceError, digest, project_lock

REPO = Path(__file__).resolve().parents[1]
DESC = dict(dimension=4, checkpoint="isolated fake adapter", preprocessing="native-test-1")


class FakeModel:
    def __init__(self):
        self.calls = 0

    def encode(self, samples, rate):
        self.calls += 1
        x = samples[:, 0].astype(np.float64)
        return np.asarray(
            [1, np.mean(x), np.mean(x * x), np.mean(np.abs(np.diff(x)))], dtype=np.float32
        )


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in (
            "config/processing.json",
            "config/retrieval.json",
            "manifests/processing/protocol.json",
        ):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / relative, target)
        self.limits = load_limits(REPO / "config/resource_limits.json", "starter")
        self.limits["min_free_bytes"] = 1
        self.owner = Context(self.root)
        self.budget = CatalogueBudget(self.root, self.limits)
        self.model = FakeModel()
        self.patches = [
            patch.object(api, "descriptor", return_value=DESC),
            patch.object(
                contracts,
                "consumer",
                return_value=dict(numerical_hash="test", code={}, declaration_hash="test"),
            ),
            patch.object(Context, "model", return_value=self.model),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(self.temp.cleanup)
        for p in self.patches:
            self.addCleanup(p.stop)
        self.sources = {}
        for key, hz in (("a", 220), ("b", 330), ("c", 440), ("q", 275)):
            path = self.owner.audio / (key + ".wav")
            path.parent.mkdir(parents=True, exist_ok=True)
            t = np.arange(24000) / 8000
            sf.write(
                path, (0.2 * np.sin(2 * np.pi * hz * t)).astype(np.float32), 8000, subtype="FLOAT"
            )
            value = validation.register_sources(
                self.budget,
                self.owner,
                dict(
                    schema_version="c04-local-import-1",
                    files=[
                        dict(
                            path=path.relative_to(self.root).as_posix(),
                            id=key,
                            group=key,
                            title=key,
                            rights="Generated isolated test",
                        )
                    ],
                ),
            )
            self.sources[key] = value["sources"][0]["source"]

    def request(self, population=("a", "b"), query="q"):
        source = self.sources[query]
        return dict(
            schema_version="c04-input-1",
            label="isolated",
            sources=[self.sources[k] for k in population],
            banks=[
                dict(label="original", grid=dict(window_milliseconds=1200, hop_milliseconds=600))
            ],
            query=dict(
                kind="native",
                source=source,
                bounds=[[0, 9600]],
                excluded_groups=[],
                lineage=dict(
                    source_sha256=source["source"]["sha256"], cue=None, transform="original"
                ),
            ),
            policy=dict(arm="legacy-mean", association=None),
            packing=4,
            refinement="off",
            historical=False,
        )

    def plan(self, value=None, previous=None):
        return api.plan(self.root, self.limits, value or self.request(), previous)

    def run_plan(self, plan=None, name="one", **extra):
        request = dict(
            root=str(self.root), limits=self.limits, plan_ref=plan or self.plan(), job=name, **extra
        )
        return job.run(request, lambda r: job.worker(r, CatalogueBudget(self.root, r["limits"])))

    def test_known_answer(self):
        self.assertTrue(validation.known_answer()["passed"])

    def test_cold_warm_and_packing(self):
        plan = self.plan()
        cold = self.run_plan(plan)
        calls = self.model.calls
        warm = self.run_plan(plan, "warm")
        self.assertEqual(warm["new_encodes"], 0)
        self.assertEqual(self.model.calls, calls)
        value = self.request()
        value["packing"] = 1
        packed = self.run_plan(self.plan(value, plan), "packed")
        self.assertEqual(packed["new_encodes"], 0)
        old = api.result(self.root, cold["result"])
        new = api.result(self.root, packed["result"])
        self.assertEqual(old["arms"], new["arms"])

    def test_delta_population_group_and_query(self):
        cold = self.run_plan()
        calls = self.model.calls
        add = self.run_plan(self.plan(self.request(("a", "b", "c"))), "add")
        self.assertEqual(add["new_encodes"], 4)
        value = self.request(("a", "c"))
        remove = self.run_plan(self.plan(value), "remove")
        self.assertEqual(remove["new_encodes"], 0)
        value = self.request(("a", "c"), "b")
        change = self.run_plan(self.plan(value), "query")
        self.assertEqual(change["new_encodes"], 0)  # exact native row already in b's bank
        self.assertGreater(self.model.calls, calls)
        self.assertEqual(api.result(self.root, cold["result"])["population_count"], 2)

    def test_label_and_ancestry_do_not_encode(self):
        result = self.run_plan()
        value = copy.deepcopy(self.request())
        value["sources"][0]["title"] = "renamed"
        value["sources"][0]["group"] = "b"
        value["label"] = "report only"
        calls = self.model.calls
        changed = self.run_plan(self.plan(value), "renamed")
        self.assertEqual(changed["new_encodes"], 0)
        self.assertEqual(self.model.calls, calls)
        self.assertEqual(api.result(self.root, result["result"])["complete_groups"], 2)
        self.assertEqual(api.result(self.root, changed["result"])["complete_groups"], 1)

    def test_complete_population_ranks_change(self):
        a = self.run_plan(self.plan(self.request(("a",))), "a")
        b = self.run_plan(self.plan(self.request(("a", "b", "c"))), "abc")
        for result in (a, b):
            value = api.result(self.root, result["result"])
            self.assertTrue(value["all_eligible_groups_ranked"])
            for ref in value["arms"]["event-multi"]["complete_groups"]:
                group = self.owner.get(ref, "group-results")
                self.assertTrue(
                    all(
                        c["eligible_groups"] == value["complete_groups"]
                        for c in group["contributions"]
                        if "eligible_groups" in c
                    )
                )

    def test_plan_and_status_do_not_infer(self):
        ref = self.plan()
        self.assertEqual(self.model.calls, 0)
        j = api.create_job(self.owner, self.budget, ref, "status")
        state = api.status(self.root, j)
        self.assertEqual(state["completed"], 0)
        self.assertEqual(self.model.calls, 0)
        self.assertIn("full source/array verification", self.owner.get(ref, "plans")["validation"])

    def test_cancellation_resume_and_last_complete(self):
        completed = self.run_plan()
        ref = self.plan(self.request(("a", "b", "c")))
        j = api.create_job(self.owner, self.budget, ref, "cancel")
        api.cancel(self.root, j)
        stopped = job.run(
            dict(root=str(self.root), limits=self.limits, job_ref=j),
            lambda r: job.worker(r, CatalogueBudget(self.root, r["limits"])),
        )
        self.assertEqual(stopped["state"], "cancelled")
        state = api.status(self.root, j)
        self.assertIsNone(state["result"])
        self.assertEqual(state["last_complete"]["result"], completed["result"])
        resumed = job.run(
            dict(root=str(self.root), limits=self.limits, job_ref=j, resume=True),
            lambda r: job.worker(r, CatalogueBudget(self.root, r["limits"])),
        )
        self.assertEqual(resumed["state"], "complete")

    def test_double_resume_never_reembeds(self):
        ready = self.run_plan()
        calls = self.model.calls
        for _ in range(2):
            resumed = job.run(
                dict(root=str(self.root), limits=self.limits, job_ref=ready["job"], resume=True),
                lambda r: job.worker(r, CatalogueBudget(self.root, r["limits"])),
            )
            self.assertEqual(resumed["state"], "complete")
        self.assertEqual(self.model.calls, calls)

    def test_changed_source_bytes_fail_without_old_success(self):
        ready = self.run_plan()
        source = self.sources["a"]
        path = self.root / source["source"]["local_path"]
        sf.write(path, np.ones(24000, dtype=np.float32) * 0.1, 8000, subtype="FLOAT")
        with self.assertRaisesRegex(InputError, "differs"):
            self.run_plan(self.plan(), "altered")
        self.assertEqual(
            record(self.owner.directory / "last-complete.json")["result"], ready["result"]
        )

    def test_corrupt_array_is_not_a_cache_hit(self):
        self.run_plan()
        path = next(self.owner.features.glob("*/features.npy"))
        with path.open("ab") as stream:
            stream.write(b"corruption")
        with self.assertRaisesRegex(InputError, "corrupt"):
            self.run_plan(self.plan(), "corrupt")

    def test_native_identity_ignores_packing_label_group(self):
        source = self.sources["a"]
        changed = copy.deepcopy(source)
        changed.update(title="x", group="new")
        self.assertEqual(
            contracts.row_key(source, [0, 100], DESC), contracts.row_key(changed, [0, 100], DESC)
        )
        for key in ("decoder", "canonical_pcm", "sha256"):
            new = copy.deepcopy(source)
            new["source"][key] = "changed"
            self.assertNotEqual(contracts.source_key(source), contracts.source_key(new))
        self.assertNotEqual(
            contracts.row_key(source, [0, 100], DESC), contracts.row_key(source, [1, 101], DESC)
        )

    def test_unsupported_and_lineage_errors(self):
        for field, value in (("schema_version", "future"), ("packing", 0)):
            spec = self.request()
            spec[field] = value
            with self.assertRaises(InputError):
                self.plan(spec)
        spec = self.request()
        spec["query"]["lineage"]["cue"] = "invented"
        with self.assertRaisesRegex(InputError, "lineage"):
            self.plan(spec)

    def test_lowered_pool_and_rename_never_replenish(self):
        self.run_plan()
        before = self.owner.pool()["counts"].copy()
        cfg = json.loads((self.root / "config/processing.json").read_text())
        cfg["policy"]["max_feature_windows"] = before["feature_windows"]
        (self.root / "config/processing.json").write_text(json.dumps(cfg))
        with self.assertRaises(ResourceError):
            self.run_plan(self.plan(self.request(("a", "b", "c"))), "new-name")
        self.assertGreaterEqual(
            self.owner.pool()["counts"]["feature_windows"], before["feature_windows"]
        )

    def test_disk_and_memory_refusals(self):
        with patch(
            "similar_sound_search.resources.shutil.disk_usage",
            return_value=type("D", (), {"free": 0})(),
        ):
            with self.assertRaisesRegex(ResourceError, "headroom"):
                self.budget.reserve(1)
        with self.assertRaisesRegex(ResourceError, "memory"):
            self.budget.reserve(0, 2 * 1024**3)

    def test_array_orphan_recovery_retains_original_producer(self):
        source = self.sources["a"]
        from similar_sound_search.search import sources

        samples = sources.load(self.budget, source, context=self.owner)

        def fail(point):
            if point == "array":
                raise InputError("injected array-before-membership")

        with self.assertRaises(InputError):
            cache.encode(
                self.budget,
                self.owner,
                source,
                DESC,
                samples,
                [[0, 9600]],
                {"original": True},
                fail,
            )
        calls = self.model.calls
        self.assertEqual(
            cache.encode(
                self.budget, self.owner, source, DESC, samples, [[0, 9600]], {"retry": True}
            ),
            0,
        )
        self.assertEqual(self.model.calls, calls)
        membership = next(
            (self.owner.directory / "cache" / contracts.source_key(source)).glob("*.json")
        )
        self.assertEqual(record(membership)["producer"], {"original": True})

    def test_fault_boundaries_resume_to_identical_result(self):
        plan = self.plan()
        j = api.create_job(self.owner, self.budget, plan, "fault")
        fired = set()

        def fail(point):
            if (
                point
                in {"reservation", "temporary", "array", "membership", "progress", "final"} - fired
            ):
                fired.add(point)
                raise InputError("injected " + point)

        for _ in range(30):
            seq, seconds = job.reserve(self.owner, self.budget)
            try:
                answer = job.step(dict(job_ref=j, reservation=seq), self.budget, self.owner, fail)
            except InputError:
                answer = dict(status="failed")
            job.settle(self.owner, self.budget, seq, seconds, 0.001, answer)
            if api.status(self.root, j)["state"] == "complete":
                break
        self.assertEqual(
            fired, {"reservation", "temporary", "array", "membership", "progress", "final"}
        )
        self.assertEqual(api.status(self.root, j)["state"], "complete")
        self.assertTrue(
            any(
                record(p)["state"] == "failed"
                for p in (self.owner.directory / "attempts" / j["record_hash"]).glob("*.json")
            )
        )

    def test_uncertain_reservation_stays_charged(self):
        seq, seconds = job.reserve(self.owner, self.budget)
        second, more = job.reserve(self.owner, self.budget)
        pool = self.owner.pool()
        self.assertEqual(pool["uncertain_worker_seconds"], seconds)
        self.assertEqual(pool["counts"]["job_seconds"], seconds + more)
        job.settle(self.owner, self.budget, second, more, 0.1, dict(status="ok"))
        with self.assertRaisesRegex(InputError, "already settled"):
            job.settle(self.owner, self.budget, second, more, 0.1, dict(status="ok"))
        self.assertEqual(seq + 1, second)

    def test_process_lock_contention_and_owner_termination(self):
        script = (
            "from pathlib import Path; from similar_sound_search.storage import project_lock; "
            "import time; "
            + "\nwith project_lock(Path(r'"
            + str(self.root)
            + "'), '.c04-worker.lock'):\n print('locked', flush=True)\n time.sleep(30)\n"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            with self.assertRaises(ResourceError):
                with project_lock(self.root, ".c04-worker.lock"):
                    pass
            child.terminate()
            child.wait(timeout=10)
            with project_lock(self.root, ".c04-worker.lock"):
                pass
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
            child.stdout.close()
            child.stderr.close()

    def test_representation_invalidation_without_model_download(self):
        source = self.sources["a"]
        before = contracts.row_key(source, [0, 9600], DESC)
        for key, val in (("preprocessing", "changed"), ("checkpoint", "other"), ("dimension", 5)):
            changed = {**DESC, key: val}
            self.assertNotEqual(before, contracts.row_key(source, [0, 9600], changed))

    def test_exclusion_updates_without_new_features(self):
        self.run_plan()
        value = self.request()
        value["query"]["excluded_groups"] = ["a", "b"]
        ready = self.run_plan(self.plan(value), "excluded")
        output = api.result(self.root, ready["result"])
        self.assertEqual(ready["new_encodes"], 0)
        self.assertEqual(output["complete_groups"], 0)
        self.assertEqual(output["excluded_groups"], ["a", "b"])
        self.assertIsNotNone(output["arms"]["legacy-mean"]["shortfall_reason"])

    def test_consumer_drift_is_explicit(self):
        self.patches[1].stop()
        from similar_sound_search.search.contracts import code_identity

        current = code_identity()
        historical = self.root / "manifests/refinement/report-repair.json"
        historical.parent.mkdir(parents=True, exist_ok=True)
        write_record(historical, dict(consumer_code=current), self.budget)
        classification = {k: "numerical" for k in current}
        value = dict(
            schema_version="c04-consumer-1",
            code=current,
            classification=classification,
            numerical_hash=digest(current),
            inherited_numerical={k: current[k] for k in contracts.INHERITED_NUMERICAL},
        )
        path = self.root / "manifests/processing/consumer.json"
        write_record(path, value, self.budget)
        self.assertEqual(contracts.consumer(self.owner)["code"], current)
        value["code"] = {**current, "processing/commands.py": "unknown edit"}
        write_record(path, value, self.budget)
        with self.assertRaisesRegex(InputError, "drift"):
            contracts.consumer(self.owner)

    def test_partial_temp_is_not_reused(self):
        partial = self.owner.features / ".a06-partial-fixture"
        partial.mkdir(parents=True)
        (partial / "features.npy").write_bytes(b"partial")
        ready = self.run_plan()
        self.assertGreater(ready["new_encodes"], 0)
        self.assertTrue((partial / "features.npy").exists())

    def test_bounded_inventory_no_gc(self):
        self.run_plan()
        value = api.inventory(self.root, 2)
        self.assertTrue(value["truncated"])
        self.assertEqual(len(value["files"]), 2)
        self.assertFalse(value["deletion_authorized"])

    def test_clean_independent_rebuild(self):
        ready = self.run_plan()
        result = validation.clean_check(self.budget, self.owner, self.root / ready["job"]["path"])
        self.assertTrue(result["passed"])
        self.assertTrue(result["exact_feature_bytes"])
        self.assertGreater(result["scalar_pairs"], 0)

    def test_missing_array_blocks_and_preserves_receipt(self):
        self.run_plan()
        path = next(self.owner.features.glob("*/features.npy"))
        # Test-owned artifact only. Historical files never enter disposable roots.
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_plan(self.plan(), "missing")

    def test_failed_windows_replace_retains_commit_for_resume(self):
        plan = self.plan()
        ref = api.create_job(self.owner, self.budget, plan, "sharing")
        seq, seconds = job.reserve(self.owner, self.budget)
        original = self.owner.publish

        def refuse(budget, path, value, immutable=False):
            if path.parent == self.owner.directory / "progress" and value.get("completed"):
                raise PermissionError("simulated Windows sharing/replace failure")
            return original(budget, path, value, immutable)

        with patch.object(self.owner, "publish", side_effect=refuse):
            with self.assertRaises(PermissionError):
                job.step(dict(job_ref=ref, reservation=seq), self.budget, self.owner)
        self.assertTrue(
            list((self.owner.directory / "unit-commits" / ref["record_hash"]).glob("*.json"))
        )
        calls = self.model.calls
        answer = job.step(dict(job_ref=ref, reservation=seq), self.budget, self.owner)
        self.assertEqual(answer["state"], "in_progress")
        self.assertEqual(self.model.calls, calls)
        job.settle(self.owner, self.budget, seq, seconds, 0.1, dict(status="ok"))

    def test_settlement_journal_replays_once(self):
        seq, seconds = job.reserve(self.owner, self.budget)
        original = self.owner.save_pool

        def refuse(budget, value):
            if value.get("last_settled_worker") == seq:
                raise PermissionError("interrupted settlement pool replace")
            return original(budget, value)

        with patch.object(self.owner, "save_pool", side_effect=refuse):
            with self.assertRaises(PermissionError):
                job.settle(self.owner, self.budget, seq, seconds, 0.2, dict(status="ok"))
        _, more = job.reserve(self.owner, self.budget)
        self.assertEqual(self.owner.pool()["measured_worker_seconds"], 0.2)
        self.assertAlmostEqual(self.owner.pool()["counts"]["job_seconds"], more + 0.2)

    def test_conflicting_semantic_bytes_fail(self):
        self.run_plan()
        source = self.sources["a"]
        directory = self.owner.directory / "cache" / contracts.source_key(source)
        path = next(directory.glob("*.json"))
        value = record(path)
        value["rows"][0]["vector_sha256"] = "0" * 64
        value.pop("record_hash")
        self.owner.put(self.budget, "cache/" + contracts.source_key(source), value)
        with self.assertRaisesRegex(InputError, "conflicting"):
            cache.lookup(self.owner, source, DESC)


if __name__ == "__main__":
    unittest.main()
