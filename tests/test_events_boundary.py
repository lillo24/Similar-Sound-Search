"""B01 integration tests use temporary ledgers and independent numeric answers."""

import copy
import hashlib
import shutil
from contextlib import ExitStack
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase
from scipy.io.wavfile import write as write_wav

from similar_sound_search.evaluation.artifacts import record, write_record
from similar_sound_search.events import compatibility
from similar_sound_search.events.context import Context
from similar_sound_search.events.job import run
from similar_sound_search.inputs import decode
from similar_sound_search.matchers.models import descriptor
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.search import query
from similar_sound_search.search.contracts import (
    code_identity,
    configuration,
    grid,
    load_array,
    recipe_code,
    save_array,
)
from similar_sound_search.search.index import shard_identity
from similar_sound_search.search.job import charge, read_charge
from similar_sound_search.search.ranking import distances
from similar_sound_search.search.report import verify_bundle
from similar_sound_search.storage import InputError, ResourceError, digest


class BoundaryCase(AudioCase):
    def setUp(self):
        super().setUp()
        for name in ("events.json", "search.json"):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        self.context_owner = Context(self.root)

    def budget(self):
        return CatalogueBudget(
            self.root, load_limits(self.root / "config/resource_limits.json", "starter")
        )

    def test_explicit_context_isolated_from_legacy_default_and_exhaustion(self):
        budget = self.budget()
        charge(budget, query_jobs=24)
        before = (self.root / "data/runs/search/work.json").read_bytes()
        with self.assertRaises(ResourceError):
            charge(budget, query_jobs=1)
        charge(budget, context=self.context_owner, query_jobs=1, feature_bytes=100)
        read_charge(budget, {"duration_seconds": 2.25}, context=self.context_owner)
        b01 = record(self.root / "data/runs/events/work.json")["counts"]
        self.assertEqual(b01["query_jobs"], 1)
        self.assertEqual(b01["managed_output_bytes"], 100)
        self.assertEqual(b01["read_audio_seconds"], 2.25)
        self.assertEqual(before, (self.root / "data/runs/search/work.json").read_bytes())

    def test_boundary_audit_allows_unrelated_module_but_keeps_legacy_guard(self):
        current = code_identity()
        with patch.object(
            compatibility, "code_identity", return_value={**current, "extra.py": "x"}
        ):
            receipt = compatibility.audit(REPOSITORY)
        self.assertEqual(receipt["current_consumer_code"]["extra.py"], "x")
        with self.assertRaisesRegex(InputError, "unaudited"):
            recipe_code(REPOSITORY)
        changed = {**current, "preparation.py": "wrong"}
        with (
            patch.object(compatibility, "code_identity", return_value=changed),
            self.assertRaisesRegex(InputError, "preprocessing"),
        ):
            compatibility.audit(REPOSITORY)

    def test_read_only_receipt_rejects_stale_index_and_consumer(self):
        identity = {"nodes": {"source": {"sha256": "bytes"}}, "audit": {"code": "one"}}
        value = {"entries": {"source": "complete"}}
        receipt = {
            "schema_version": "b01-a06-consumer-1",
            "identity": identity,
            "validated_recordings": 1,
        }
        with patch.object(compatibility, "snapshot", return_value=(value, {}, {}, identity)):
            compatibility.validate_receipt(self.budget(), None, value, {}, {}, receipt)
            for key in ("nodes", "audit"):
                stale = copy.deepcopy(receipt)
                stale["identity"][key] = {"changed": True}
                with self.assertRaisesRegex(InputError, "stale"):
                    compatibility.validate_receipt(self.budget(), None, value, {}, {}, stale)

    def test_linked_report_pages_are_allowlisted_and_integrity_checked(self):
        base = self.root / "reports/local/b01/owned"
        base.mkdir(parents=True)
        (base / "index.html").write_text("Event report")
        (base / "single.html").write_text("Separate scores")

        def h(path):
            return hashlib.sha256(path.read_bytes()).hexdigest()

        value = {
            "html_sha256": h(base / "index.html"),
            "items": [],
            "pages": {"single.html": h(base / "single.html")},
        }
        write_record(base / "bundle.json", value, self.budget())
        allowed = verify_bundle(self.root, base, self.context_owner.reports)
        self.assertEqual(set(allowed), {"/index.html", "/single.html"})
        (base / "single.html").write_text("stale")
        with self.assertRaisesRegex(InputError, "stale"):
            verify_bundle(self.root, base, self.context_owner.reports)
        value["pages"] = {"../escape.html": "untrusted"}
        write_record(base / "bundle.json", value, self.budget())
        with self.assertRaisesRegex(InputError, "filename"):
            verify_bundle(self.root, base, self.context_owner.reports)

    def test_shared_fixed_mean_numerical_equivalence_and_order(self):
        # Independent 3-4-5 triangle and unit-vector answers, with no model fixture.
        per, aggregate = distances([[3, 0], [0, 4]], [[3, 4], [-3, 0]], "cosine")
        np.testing.assert_allclose(per, [[0.4, 2], [0.2, 1]], atol=1e-15)
        np.testing.assert_allclose(aggregate, [0.3, 1.5], atol=1e-15)
        np.testing.assert_allclose(
            distances([[0, 4], [3, 0]], [[3, 4], [-3, 0]], "cosine")[1],
            aggregate,
            atol=1e-12,
        )

    def test_unordered_pcm_dedup_keeps_union_of_all_parents(self):
        shutil.copyfile(
            REPOSITORY / "config/matcher_methods.json", self.root / "config/matcher_methods.json"
        )
        path = self.wav(channels=1)
        other = path.with_name("copy.wav")
        shutil.copyfile(path, other)
        desc = descriptor(self.root, "acoustic")
        binding = {"version": "b01-handoff-1", "events": ["first", "second"]}
        items = [{"path": str(path)}, {"path": str(other)}]
        first = self.json_file(
            "config/local/one.json",
            {"schema_version": "a06-query-input-1", "b01_binding": binding, "examples": items},
        )
        second = self.json_file(
            "config/local/two.json",
            {
                "schema_version": "a06-query-input-1",
                "b01_binding": binding,
                "examples": [items[1], items[0], items[0]],
            },
        )

        def parents(root, prepared, pcm):
            return ["parent-b" if "copy.wav" in prepared["source"]["local_path"] else "parent-a"]

        with (
            patch.object(query, "frozen", return_value=({}, {}, {}, {}, desc)),
            patch.object(query, "parents", parents),
        ):
            a = query.prepare_query(self.budget(), first, "acoustic", self.context_owner)
            b = query.prepare_query(self.budget(), second, "acoustic", self.context_owner)
        self.assertTrue(b["reused"])
        self.assertEqual(a["query_id"], b["query_id"])
        self.assertEqual(a["examples"], 1)
        saved = record(self.root / a["query"])
        self.assertEqual(saved["identity"]["excluded_groups"], ["parent-a", "parent-b"])

    def test_worker_interruption_keeps_b01_reservation_and_old_ledger_unchanged(self):
        charge(self.budget(), query_jobs=1)
        original = (self.root / "data/runs/search/work.json").read_bytes()
        req = {"root": str(self.root), "limits": self.budget().limits, "events_action": "propose"}

        def interrupted(request):
            raise OSError("controlled interruption")

        with self.assertRaises(OSError):
            run(req, interrupted)
        ledger = record(self.root / "data/runs/events/timing.json")
        self.assertGreaterEqual(ledger["worker_seconds_by_action"]["propose"], 0)
        self.assertEqual(record(self.root / "data/runs/events/work.json")["counts"]["workers"], 1)
        self.assertEqual(original, (self.root / "data/runs/search/work.json").read_bytes())

    def test_small_legacy_fixture_reuse_and_source_shard_drift(self):
        budget = self.budget()
        cfg = configuration(self.root)
        path = self.root / "data/audio/catalogue/originals/known.wav"
        path.parent.mkdir(parents=True)
        samples = np.tile(np.array([[0.1], [-0.1]], np.float32), (16000, 1))
        write_wav(path, 8000, samples)
        _, meta = decode(path, budget)
        src = {
            "source": {**meta, "local_path": path.relative_to(self.root).as_posix()},
            "recording_id": "one",
            "group": "g",
            "record_hash": "origin",
            "kind": "engineering",
        }
        desc = {"dimension": 2, "distance": "cosine", "method": "fixture"}
        identity = {
            "code": {"legacy": "pinned"},
            "configuration": cfg,
            "representation": desc,
            "sources": [["one", "origin"]],
            "groups_hash": "groups",
        }
        index_id = digest(identity)
        base = self.root / "data/indexes/a06" / index_id
        bounds = grid(32000, 8000, cfg)
        shard = shard_identity(src, bounds, desc, cfg)
        array = np.array([[1, 0], [0, 1]] * (len(bounds) // 2), np.float32)
        save_array(base / "shards", shard, array, budget)
        shard_id = digest(shard)
        write_record(
            base / "entries/one.json",
            {"state": "complete", "source": src, "shards": [shard_id]},
            budget,
        )
        manifest_path = base / "index.json"
        write_record(
            manifest_path,
            {
                "index_id": index_id,
                "identity": identity,
                "state": "complete",
                "entries": {"one": "complete"},
            },
            budget,
        )
        write_record(
            self.root / "manifests/search/execution-repair.json",
            {"before": identity["code"]},
            budget,
        )
        with ExitStack() as stack:
            stack.enter_context(patch.object(compatibility, "INDEX", index_id))
            stack.enter_context(
                patch.object(compatibility, "INDEX_RECORD", record(manifest_path)["record_hash"])
            )
            stack.enter_context(
                patch.object(compatibility, "audit", return_value={"consumer": "fixture"})
            )
            stack.enter_context(
                patch.object(compatibility, "frozen", return_value=({}, {}, {}, {}, desc))
            )
            stack.enter_context(
                patch.object(
                    compatibility.sources,
                    "catalogue",
                    return_value=(
                        [{"entry_id": "one", "record_hash": "origin"}],
                        {"record_hash": "groups", "entry_groups": {"one": "g"}},
                    ),
                )
            )
            stack.enter_context(
                patch.object(compatibility.sources, "public_source", return_value=src)
            )
            first = compatibility.step({"index": manifest_path}, budget, self.context_owner)
            self.assertEqual(first["new_features"], 0)
            vectors, _ = load_array(base / "shards" / shard_id, shard, budget)
            np.testing.assert_array_equal(distances([[1, 0]], vectors, "cosine")[1], [0, 1] * 4)
            compatibility.step({"index": manifest_path}, budget, self.context_owner)
            blob = base / "shards" / shard_id / "features.npy"
            raw = blob.read_bytes()
            blob.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
            with self.assertRaisesRegex(InputError, "corrupt"):
                compatibility.step({"index": manifest_path}, budget, self.context_owner)
            blob.write_bytes(raw)
            with path.open("ab") as stream:
                stream.write(b"changed source")
            with self.assertRaisesRegex(InputError, "original bytes changed"):
                compatibility.step({"index": manifest_path}, budget, self.context_owner)
