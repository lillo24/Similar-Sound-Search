"""B01 integration tests use temporary ledgers and independent numeric answers."""

import copy
import shutil
from unittest.mock import patch

import numpy as np
from helpers import REPOSITORY, AudioCase

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.events import compatibility
from similar_sound_search.events.context import Context
from similar_sound_search.resources import CatalogueBudget, load_limits
from similar_sound_search.search.contracts import code_identity, recipe_code
from similar_sound_search.search.job import charge, read_charge
from similar_sound_search.search.ranking import distances
from similar_sound_search.storage import InputError, ResourceError


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
