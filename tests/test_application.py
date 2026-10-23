"""D01 isolated accounting, product API, security and native-media regression checks."""

import http.client
import json
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from similar_sound_search.application import api, codec, history, job, media, pipeline, queries
from similar_sound_search.application.context import POOL_WRITE, Context, PersistenceError, payload
from similar_sound_search.application.files import atomic_bytes
from similar_sound_search.application.locks import active, lock
from similar_sound_search.application.server import make_server
from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.storage import InputError, ResourceError, atomic_json, digest

REPO = Path(__file__).resolve().parents[1]
PROOF = dict(
    declaration_hash="a" * 64, numerical_hash="b" * 64, code_hash="c" * 64, version="d01-consumer-1"
)


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in (
            "config/application.json",
            "config/queries.json",
            "config/retrieval.json",
            "config/search.json",
            "manifests/application/protocol.json",
        ):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / relative, path)
        self.limits = load_limits(REPO / "config/resource_limits.json", "starter")
        self.limits["min_free_bytes"] = 1
        self.owner = Context(self.root, "test")
        self.owner.admit("test", 4 * 1024**2, acceptance=True)
        self.budget = CatalogueBudget(self.root, self.limits)
        p = patch.object(history, "consumer", return_value=PROOF)
        p.start()
        self.addCleanup(p.stop)

    def terminal(self, identity="attempt", **kw):
        self.owner.reserve_attempt(identity)
        path = self.owner.directory / "states/test.json"
        self.owner.terminal(
            identity, path, dict(state="failed", error="ordinary output refused"), **kw
        )
        return path

    def wav(self, hz=220):
        path = self.owner.audio / "imports/reference.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        t = np.arange(24000) / 8000
        sf.write(path, (0.2 * np.sin(2 * np.pi * hz * t)).astype(np.float32), 8000, subtype="FLOAT")
        return path

    def test_exhausted_ordinary_keeps_terminal_and_settlement(self):
        self.owner.reserve_attempt("attempt")
        remaining = self.owner.pool()["allocations"]["test"]["remaining"]
        self.owner.charge(self.budget, metadata_bytes=remaining - POOL_WRITE)
        with self.assertRaises(ResourceError):
            self.owner.put(self.budget, "output", dict(a="refused"))
        path = self.owner.directory / "states/test.json"
        self.owner.terminal(
            "attempt", path, dict(state="blocked", error="ordinary exhausted"), elapsed=2
        )
        self.assertEqual(record(path)["state"], "blocked")
        self.assertTrue(self.owner.pool()["attempts"]["attempt"]["settled"])
        self.assertEqual(self.owner.pool()["counts"]["job_seconds"], 2)

    def test_settlement_retry_is_read_only_when_already_applied(self):
        path = self.terminal(elapsed=3)
        before = self.owner.pool()
        with patch(
            "similar_sound_search.application.context.atomic_json",
            side_effect=AssertionError("rewrote terminal"),
        ):
            self.owner.terminal(
                "attempt", path, dict(state="failed", error="ordinary output refused"), elapsed=3
            )
        self.assertEqual(before, self.owner.pool())

    def test_unobservable_attempt_retains_full_time(self):
        self.terminal(uncertain=True)
        self.assertEqual(self.owner.pool()["counts"]["job_seconds"], 120)
        self.assertEqual(self.owner.pool()["uncertain_worker_seconds"], 120)

    def test_failure_while_recording_failure_is_explicit(self):
        self.owner.reserve_attempt("attempt")
        with patch(
            "similar_sound_search.application.context.atomic_json",
            side_effect=PermissionError("filesystem refuses every write"),
        ):
            with self.assertRaisesRegex(PersistenceError, "observed process outcome is separate"):
                self.owner.terminal(
                    "attempt", self.owner.directory / "failure.json", dict(state="failed")
                )
        self.assertFalse((self.owner.directory / "failure.json").exists())
        self.assertFalse(self.owner.pool()["attempts"]["attempt"]["settled"])

    def test_crash_after_journal_replays_once(self):
        self.owner.reserve_attempt("attempt")
        real = self.owner._save
        with patch.object(self.owner, "_save", side_effect=PermissionError("replace failed")):
            with self.assertRaises(PersistenceError):
                self.owner.terminal(
                    "attempt",
                    self.owner.directory / "failure.json",
                    dict(state="failed"),
                    elapsed=4,
                )
        self.owner._save = real
        self.owner.terminal(
            "attempt", self.owner.directory / "failure.json", dict(state="failed"), elapsed=4
        )
        self.assertEqual(self.owner.pool()["counts"]["job_seconds"], 4)
        self.assertEqual(record(self.owner.directory / "failure.json")["state"], "failed")

    def test_protected_slot_admitted_before_worker(self):
        self.owner.reserve_attempt("a")
        p = self.owner.pool()
        self.assertEqual(p["protected_reserved"], 262144 - POOL_WRITE)
        with self.assertRaises(ResourceError):
            self.owner.reserve_attempt("b")
        self.assertEqual(self.owner.pool(), p)

    def test_cancel_has_separate_prepaid_control_slot(self):
        self.owner.reserve_attempt("worker")
        self.owner.reserve_attempt("cancel", seconds=0)
        self.owner.terminal(
            "cancel", self.owner.directory / "cancel.json", dict(cancel=True), elapsed=0
        )
        self.assertFalse(self.owner.pool()["attempts"]["worker"]["settled"])
        self.assertEqual(self.owner.pool()["counts"]["workers"], 1)
        self.owner.terminal(
            "worker", self.owner.directory / "stopped.json", dict(state="cancelled"), elapsed=5
        )
        self.assertEqual(self.owner.pool()["protected_reserved"], 0)

    def test_worker_journal_replay_preserves_later_control_settlements(self):
        self.owner.reserve_attempt("worker")
        self.owner.reserve_attempt("control", seconds=0)
        self.owner.terminal(
            "control", self.owner.directory / "control.json", dict(cancel=True), elapsed=0
        )
        with patch.object(
            self.owner, "_save", side_effect=PermissionError("crash after worker journal")
        ):
            with self.assertRaises(PersistenceError):
                self.owner.terminal(
                    "worker",
                    self.owner.directory / "worker.json",
                    dict(state="cancelled"),
                    elapsed=5,
                )
        self.owner.reserve_attempt("later-control", seconds=0)
        self.owner.terminal(
            "later-control", self.owner.directory / "later.json", dict(resume=True), elapsed=0
        )
        before = self.owner.pool()
        self.owner.terminal(
            "worker", self.owner.directory / "worker.json", dict(state="cancelled"), elapsed=5
        )
        after = self.owner.pool()
        self.assertTrue(after["attempts"]["worker"]["settled"])
        self.assertEqual(after["last_settled"], before["last_settled"])
        self.assertGreaterEqual(
            after["counts"]["metadata_bytes"], before["counts"]["metadata_bytes"]
        )
        self.assertEqual(after["counts"]["job_seconds"], 5)
        self.assertEqual(after["protected_reserved"], 0)

    def test_admission_covers_whole_request(self):
        before = self.owner.pool()
        with self.assertRaisesRegex(ResourceError, "complete path"):
            self.owner.admit("impossible", 97 * 1024**2)
        self.assertEqual(before, self.owner.pool())

    def test_unknown_counter_and_increased_policy_fail(self):
        with self.assertRaises(InputError):
            self.owner.charge(self.budget, unknown=1)
        cfg = json.loads((self.root / "config/application.json").read_text())
        cfg["policy"]["max_workers"] = 257
        atomic_json(self.root / "config/application.json", cfg)
        with self.assertRaises(InputError):
            Context(self.root)

    def test_immutable_and_reader_limit(self):
        path = self.owner.directory / "same.json"
        self.owner.publish(self.budget, path, dict(a=1), immutable=True)
        with self.assertRaises(InputError):
            self.owner.publish(self.budget, path, dict(a=2), immutable=True)
        with self.assertRaises(InputError):
            payload(dict(a="x" * 1024**2))

    def test_group_codec_lossless_bounded_and_corruption(self):
        value = dict(
            schema_version="c04-group-1", passages=[dict(score=0.12345678901234567)] * 1000
        )
        packed = codec.encode("group-results", value)
        packed["record_hash"] = digest(packed)
        self.assertEqual(codec.decode(packed), {**value, "record_hash": packed["record_hash"]})
        packed["content_hash"] = "f" * 64
        with self.assertRaises(InputError):
            codec.decode(packed)

    def test_catalogue_geometry_without_inference(self):
        value = pipeline.geometry_estimate(self.owner)
        self.assertTrue(value["fits"])
        self.assertEqual(value["groups"], 72)
        self.assertLess(value["complete_path_counted_bytes"], 96 * 1024**2)

    def test_real_os_lock_contention_and_release(self):
        with lock(self.root, "worker"):
            self.assertTrue(active(self.root, "worker"))
            with self.assertRaises(ResourceError):
                with lock(self.root, "worker"):
                    pass
        self.assertFalse(active(self.root, "worker"))
        self.assertTrue((self.owner.directory / "worker.lock").exists())

    def test_windows_replace_failure_retains_temporary(self):
        path = self.owner.directory / "binary"
        with patch(
            "similar_sound_search.application.files.os.replace",
            side_effect=PermissionError("Windows sharing violation"),
        ):
            with self.assertRaises(PermissionError):
                atomic_bytes(path, b"new bytes")
        self.assertFalse(path.exists())
        self.assertEqual(len(list(path.parent.glob(".d01-write-*"))), 1)

    def test_low_disk_and_memory_refuse_without_success(self):
        with patch(
            "similar_sound_search.resources.shutil.disk_usage",
            return_value=type("Disk", (), {"free": 0})(),
        ):
            with self.assertRaises(ResourceError):
                self.budget.reserve(1)
        with self.assertRaises(ResourceError):
            self.budget.reserve(1, self.limits["max_working_bytes"] + 1)

    def test_native_media_caches_and_detects_corruption(self):
        path = self.wav()
        result = queries.register(self.budget, self.owner, path, "native test")
        source = media.source_for_asset(self.owner, result["asset_id"])
        ref = media.cached_clip(self.budget, self.owner, source, [123, 8123])
        target, value = media.validate(self.owner, ref["record_hash"])
        actual, rate = sf.read(target, dtype="int16", always_2d=True)
        source_samples, _ = sf.read(path, dtype="float32", always_2d=True)
        expected, _ = media.pcm16(source_samples[123:8123])
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(rate, 8000)
        before = self.owner.pool()
        self.assertEqual(media.cached_clip(self.budget, self.owner, source, [123, 8123]), ref)
        self.assertEqual(before, self.owner.pool())
        target.write_bytes(b"corrupt")
        with self.assertRaisesRegex(InputError, "missing/changed"):
            media.validate(self.owner, ref["record_hash"])

    def test_changed_import_bytes_cannot_reuse_asset(self):
        path = self.wav()
        result = queries.register(self.budget, self.owner, path, "source")
        self.wav(330)
        from similar_sound_search.queries.assets import read_asset

        with self.assertRaisesRegex(InputError, "changed source"):
            read_asset(self.budget, queries.QueryOwner(self.owner), result["asset_id"])

    def spec(self):
        return dict(
            kind="search",
            input=dict(
                query=dict(historical=True, **self.owner.protocol["delivery"]), arm="legacy-mean"
            ),
            request_id="stable-request",
        )

    def test_duplicate_request_and_conflict(self):
        spec = self.spec()
        first = api.submit(self.root, self.limits, spec, acceptance=True)
        before = self.owner.pool()
        second = api.submit(self.root, self.limits, spec, acceptance=True)
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertEqual(before, self.owner.pool())
        spec["input"]["arm"] = "event-multi"
        with self.assertRaisesRegex(InputError, "request conflict"):
            api.submit(self.root, self.limits, spec, acceptance=True)

    def test_status_polling_read_only_and_stale_state(self):
        key = api.submit(self.root, self.limits, self.spec(), acceptance=True)["job_id"]
        state = record(api.state_path(self.owner, key))
        state["state"] = "running"
        atomic_json(api.state_path(self.owner, key), state)
        # Recompute the state integrity after deliberate test fixture mutation.
        state.pop("record_hash")
        atomic_json(api.state_path(self.owner, key), {**state, "record_hash": digest(state)})
        before = self.owner.pool()
        for _ in range(30):
            self.assertEqual(api.status(self.root, key)["state"], "interrupted")
        self.assertEqual(before, self.owner.pool())
        with self.assertRaises(InputError):
            api.result(self.root, key)

    def test_resume_acknowledges_pending_before_dispatch_and_is_idempotent(self):
        key = api.submit(self.root, self.limits, self.spec(), acceptance=True)["job_id"]
        state = record(api.state_path(self.owner, key))
        state["state"] = "cancelled"
        self.owner.publish(self.budget, api.state_path(self.owner, key), state)
        api.cancel(self.root, key, "a" * 64)
        answer = api.resume_control(self.root, key, "b" * 64)
        self.assertEqual(answer["state"], "resume_requested")
        self.assertEqual(api.status(self.root, key)["state"], "pending")
        before = self.owner.pool()
        api.resume_control(self.root, key, "b" * 64)
        self.assertEqual(before, self.owner.pool())
        self.assertEqual(before["counts"]["workers"], 0)

    def test_unavailable_setting_is_not_accepted(self):
        spec = self.spec()
        spec["input"]["arm"] = "pitch"
        before = self.owner.pool()
        with self.assertRaisesRegex(InputError, "unavailable"):
            api.submit(self.root, self.limits, spec, acceptance=True)
        self.assertEqual(before, self.owner.pool())

    def test_server_security_and_ranges_no_hidden_work(self):
        server = make_server(self.root, self.limits, 18774)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        conn = http.client.HTTPConnection("127.0.0.1", 18774, timeout=5)
        self.addCleanup(conn.close)
        conn.request("GET", "/api/bootstrap")
        response = conn.getresponse()
        bootstrap = json.loads(response.read())
        token = bootstrap["token"]
        before = self.owner.pool()
        for target in ("/../AGENTS.md", "/media/../../AGENTS.md", "/data/audio", "/api/submit"):
            conn.request("GET", target)
            response = conn.getresponse()
            self.assertGreaterEqual(response.status, 400)
            response.read()
        for headers in ({}, {"Origin": "https://evil.example", "X-D01-Token": token}):
            conn.request(
                "POST",
                "/api/submit",
                body=json.dumps(self.spec()),
                headers={"Content-Type": "application/json", **headers},
            )
            response = conn.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
            conn.close()
            conn = http.client.HTTPConnection("127.0.0.1", 18774, timeout=5)
        conn.request("GET", "/", headers={"Host": "attacker.example:18774"})
        response = conn.getresponse()
        self.assertGreaterEqual(response.status, 400)
        response.read()
        conn.request("GET", "/app.js", headers={"Range": "bytes=0-31"})
        response = conn.getresponse()
        self.assertEqual(response.status, 206)
        self.assertEqual(len(response.read()), 32)
        conn.request("GET", "/app.js", headers={"Range": "bytes=0-1,4-5"})
        response = conn.getresponse()
        self.assertEqual(response.status, 416)
        response.read()
        self.assertEqual(before, self.owner.pool())
        conn.close()

    def test_revision_save_reorder_optimistic_edit_and_rename(self):
        from similar_sound_search.queries import library

        imported = queries.register(self.budget, self.owner, self.wav(), "reference")
        selection = dict(
            origin="isolated native selection",
            version="b03-manual-native-1",
            complete=False,
            uncertainty=["engineering mixture"],
        )
        a = dict(
            asset_id=imported["asset_id"], event=[0, 8000], context=[0, 9000], selection=selection
        )
        b = {**a, "event": [12000, 20000], "context": [11000, 21000]}
        first = queries.save(self.budget, self.owner, dict(label="Two examples", examples=[a, b]))
        second = queries.save(
            self.budget,
            self.owner,
            dict(
                label="Same reordered",
                examples=[b, a, a],
                query_id=first["query_id"],
                expected=first["revision_id"],
            ),
        )
        self.assertEqual(first["revision_id"], second["revision_id"])
        with self.assertRaisesRegex(InputError, "revision conflict"):
            queries.save(
                self.budget,
                self.owner,
                dict(
                    label="stale edit", examples=[a], query_id=first["query_id"], expected="e" * 64
                ),
            )
        view = queries.QueryOwner(self.owner)
        head = record(library.name_path(view, first["query_id"]))
        queries.rename(
            self.budget,
            self.owner,
            dict(query_id=first["query_id"], expected=head["record_hash"], label="Renamed"),
        )
        with self.assertRaisesRegex(InputError, "conflict"):
            queries.rename(
                self.budget,
                self.owner,
                dict(query_id=first["query_id"], expected=head["record_hash"], label="stale"),
            )
        self.assertFalse((self.root / "data/runs/queries").exists())

    def test_query_materialization_deduplicates_pcm_and_retains_native_bounds(self):
        from similar_sound_search.queries import materialization
        from similar_sound_search.search import query as query_module

        imported = queries.register(self.budget, self.owner, self.wav(), "reference")
        selection = dict(
            origin="isolated exact native",
            version="b03-manual-native-1",
            complete=False,
            uncertainty=[],
        )
        example = dict(
            asset_id=imported["asset_id"], event=[123, 8123], context=[0, 9000], selection=selection
        )
        another = {**example, "selection": {**selection, "origin": "second contributing selection"}}
        revision = queries.save(
            self.budget, self.owner, dict(label="PCM dedup", examples=[example, another])
        )
        desc = dict(dimension=2, method="isolated")

        class Model:
            calls = 0

            def encode(self, samples, rate):
                self.calls += 1
                return np.asarray([1.0, 0.5], dtype=np.float32)

        model = Model()
        patches = [
            patch.object(query_module, "frozen", return_value=(None, None, None, None, desc)),
            patch.object(materialization, "frozen", return_value=(None, None, None, None, desc)),
            patch("similar_sound_search.queries.features.adapter", return_value=(model, 0)),
            patch(
                "similar_sound_search.search.sources.catalogue",
                return_value=([], {"entry_groups": {}}),
            ),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        value, matrix = queries.load(
            self.budget, self.owner, dict(revision=revision["revision_id"])
        )
        self.assertEqual(len(value["query"]["examples"]), 1)
        self.assertEqual(model.calls, 1)
        self.assertEqual(matrix.shape, (1, 2))
        bindings = value["query"]["identity"]["consumer"]["examples"]
        self.assertEqual(len(bindings), 2)
        self.assertTrue(all(e["event"] == [123, 8123] for e in bindings))
        warm, _ = queries.load(
            self.budget,
            self.owner,
            dict(revision=revision["revision_id"], materialization=value["materialization"]),
        )
        self.assertEqual(warm["query"]["record_hash"], value["query"]["record_hash"])
        self.assertEqual(model.calls, 1)
        self.assertFalse((self.root / "data/features/queries").exists())

    def test_completed_search_navigation_is_read_only_and_keeps_resolved_query(self):
        revision, materialization = "1" * 64, "2" * 64
        identity = dict(request=dict(kind="search"))
        key = digest(identity)
        self.owner.publish(
            self.budget,
            self.owner.directory / "jobs" / (key + ".json"),
            dict(job_id=key, identity=identity),
        )
        query = self.owner.put(
            self.budget, "queries", dict(revision=revision, materialization=materialization)
        )
        result = self.owner.put(
            self.budget,
            "results",
            dict(
                query=query,
                selection=dict(historical=False, materialization=None),
                policy="legacy-mean",
                query_hash="3" * 64,
            ),
        )
        self.owner.publish(
            self.budget,
            api.state_path(self.owner, key),
            dict(job_id=key, state="complete", result=result),
        )
        before = self.owner.pool()
        with patch.object(queries, "inventory", return_value=dict(names=[])):
            values = api.completed_searches(self.root)
            self.assertEqual(values[0]["job_id"], key)
            self.assertEqual(values[0]["query"]["materialization"], materialization)
            self.assertEqual(values[0]["query"]["revision"], revision)
            self.assertEqual(values[0]["label"], "Saved query")
        self.assertEqual(self.owner.pool(), before)

    def test_controlled_population_scalar_exclusion_and_exact_players(self):
        from similar_sound_search.inputs import decode
        from similar_sound_search.processing.contracts import source_key

        population = []
        for i, hz in enumerate((220, 330, 440)):
            path = self.owner.audio / (str(i) + ".wav")
            path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(
                path,
                (0.2 * np.sin(2 * np.pi * hz * np.arange(24000) / 8000)).astype(np.float32),
                8000,
                subtype="FLOAT",
            )
            _, audio = decode(path, self.budget)
            population.append(
                dict(
                    recording_id=str(i),
                    group=str(i),
                    kind="engineering",
                    source={**audio, "local_path": path.relative_to(self.root).as_posix()},
                    title="Song " + str(i),
                    artist="Generated",
                    offset=None,
                    offset_evidence=None,
                )
            )
        q = dict(
            record_hash="a" * 64,
            examples=[
                dict(
                    example_id="query",
                    audio=dict(duration_seconds=2.4),
                    prepared=dict(
                        source=dict(sha256=population[0]["source"]["sha256"]),
                        technical_metadata=dict(
                            canonical_pcm=population[0]["source"]["canonical_pcm"]
                        ),
                    ),
                )
            ],
            identity=dict(excluded_groups=["0"]),
        )
        oldplan = dict(
            input=dict(
                sources=population,
                banks=[
                    dict(label="legacy", grid=dict(window_milliseconds=2400, hop_milliseconds=600))
                ],
            ),
            representation=dict(dimension=2),
            tombstones=[],
        )
        values = {}
        for i, s in enumerate(population):
            # Independent scalar cosine. Source 0 is a perfect match but must be excluded.
            vector = [1.0, 0.0] if i == 0 else [4.0, 3.0] if i == 1 else [0.0, 1.0]
            scalar = 1 - vector[0] / (sum(v * v for v in vector) ** 0.5)
            row = dict(key=digest([i, 0]), bounds=[0, 19200], per=[scalar], mean=scalar)
            scores = dict(banks=[dict(count=2, baseline=row, supports=[[row]])])
            values[s["recording_id"]] = dict(
                scores=scores, proof=dict(path="owned-proof", record_hash=source_key(s))
            )
        with patch.object(history, "inputs", return_value=(None, oldplan, None)):
            result, capture = pipeline.aggregate(
                self.budget, self.owner, dict(arm="legacy-mean"), values, dict(query=q)
            )
        for _, (kind, data) in capture.records.items():
            self.owner.put(self.budget, kind, data)
        self.assertEqual(result["excluded_groups"], ["0"])
        groups = [
            self.owner.get(ref, "group-results")
            for ref in result["arms"]["legacy-mean"]["complete_groups"]
        ]
        self.assertEqual([g["group"] for g in groups], ["1", "2"])
        self.assertAlmostEqual(groups[0]["score"], 0.2)
        cards = media.cards(self.budget, self.owner, result, 0, 2)
        self.assertEqual([c["group"] for c in cards], ["1", "2"])
        for c in cards:
            p = c["passages"][0]
            _, saved = media.validate(self.owner, p["scored"]["record_hash"])
            self.assertEqual(saved["bounds"], p["scored_bounds"])
            self.assertEqual(saved["original"]["group"], c["group"])
            self.assertEqual(c["query_hash"], q["record_hash"])
        query_ref = self.owner.put(self.budget, "queries", dict(query=q))
        result_key = "d" * 64
        published = self.owner.put(
            self.budget,
            "results",
            dict(
                **result,
                schema_version="d01-result-1",
                state="complete",
                job_id=result_key,
                query=query_ref,
                cards=cards,
            ),
        )
        self.owner.publish(
            self.budget,
            api.state_path(self.owner, result_key),
            dict(state="complete", result=published),
        )
        target, _ = api.result_media(
            self.root, published["record_hash"], cards[0]["passages"][0]["scored"]["record_hash"]
        )
        self.assertTrue(target.is_file())
        foreign = media.cached_clip(self.budget, self.owner, population[1], [800, 8800])
        with self.assertRaisesRegex(InputError, "does not belong"):
            api.result_media(self.root, published["record_hash"], foreign["record_hash"])

    def test_committed_unit_survives_coordinator_failure_without_duplicate_work(self):
        request = dict(kind="save", input={}, request_id="crash-after-commit")
        key = api.submit(self.root, self.limits, request, acceptance=True)["job_id"]
        calls = []

        def perform(*args):
            calls.append(1)
            return dict(saved="immutable")

        def interrupted(owner, key, limits, validate_units=None, finalization_audit=False):
            job.worker(dict(root=str(owner.root), job_id=key, limits=limits))
            raise RuntimeError("coordinator interrupted after immutable publication")

        with (
            patch.object(job, "perform", side_effect=perform),
            patch.object(job, "execute", side_effect=interrupted),
        ):
            self.assertEqual(job.run(self.root, self.limits, key)["state"], "failed")

        def execute(owner, key, limits, validate_units=None, finalization_audit=False):
            return job.worker(dict(root=str(owner.root), job_id=key, limits=limits))

        with (
            patch.object(job, "perform", side_effect=perform),
            patch.object(job, "execute", side_effect=execute),
        ):
            self.assertEqual(job.run(self.root, self.limits, key)["state"], "complete")
        self.assertEqual(len(calls), 1)
        self.assertEqual(api.result(self.root, key)["output"], dict(saved="immutable"))

    def test_fresh_consumer_receipt_preserves_semantic_resume_and_rejects_drift(self):
        declaration = dict(code={}, numerical_hash=PROOF["numerical_hash"])
        key = digest(declaration)
        atomic_json(
            self.root / "manifests/application/consumers" / (key + ".json"),
            {**declaration, "record_hash": key},
        )
        prior = {**PROOF, "declaration_hash": key, "code_hash": digest({})}
        before = self.owner.put(
            self.budget, "adoptions", dict(consumer=prior, source="fixture", membership="exact")
        )
        after = self.owner.put(
            self.budget, "adoptions", dict(consumer=PROOF, source="fixture", membership="exact")
        )
        job.validate_resumed(
            self.owner,
            self.budget,
            "source",
            dict(proof=before, scores="bound"),
            dict(proof=after, scores="bound"),
        )
        changed = self.owner.put(
            self.budget, "adoptions", dict(consumer=PROOF, source="fixture", membership="different")
        )
        with self.assertRaisesRegex(InputError, "semantic dependency"):
            job.validate_resumed(
                self.owner,
                self.budget,
                "source",
                dict(proof=before, scores="bound"),
                dict(proof=changed, scores="bound"),
            )

    def test_actual_owned_worker_interruption_releases_os_lock_and_keeps_reservation(self):
        from similar_sound_search.processing.runner import python_command

        key = api.submit(
            self.root,
            self.limits,
            dict(kind="save", input={}, request_id="owned-interruption"),
            acceptance=True,
        )["job_id"]
        owner = Context(self.root, key)
        owner.reserve_attempt("killed-worker")
        script = self.root / "owned-worker.py"
        script.write_text(
            "from pathlib import Path\nimport sys,time\n"
            "from similar_sound_search.application.locks import lock\n"
            "r=Path(sys.argv[1])\nwith lock(r,'worker'):\n"
            " (r/'ready').write_text('ready')\n time.sleep(60)\n",
            encoding="utf-8",
        )
        process = subprocess.Popen(
            python_command(script, [str(self.root)]), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            deadline = time.monotonic() + 8
            while not (self.root / "ready").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue((self.root / "ready").exists())
            self.assertTrue(active(self.root, "worker"))
            process.terminate()
            process.wait(timeout=5)
            self.assertFalse(active(self.root, "worker"))
            with lock(self.root, "coordinator"), lock(self.root, "worker"):
                job.reconcile(owner, key)
            self.assertEqual(owner.pool()["uncertain_worker_seconds"], 120)
            self.assertEqual(owner.pool()["counts"]["job_seconds"], 120)
            self.assertEqual(api.status(self.root, key)["state"], "interrupted")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            process.communicate()


if __name__ == "__main__":
    unittest.main()
