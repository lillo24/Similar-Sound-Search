"""D03 archive trust boundary, one allocation, complete-path admission and recovery."""

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from similar_sound_search.evaluation.artifacts import record
from similar_sound_search.resources import CatalogueBudget
from similar_sound_search.storage import InputError, ResourceError, digest
from sound_search_distribution import authority, bootstrap
from sound_search_distribution.context import Context
from sound_search_distribution.files import relative, verify_files
from sound_search_distribution.policy import MIB, SHARE, estimate, limits

ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "space à workspace"
        self.root.mkdir()
        for name in (
            "config/resource_limits.json",
            "config/application.json",
            "manifests/application/protocol.json",
        ):
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        self.registry = self.base / "external"
        authority.initialize(self.root, self.registry)
        self.owner = Context(self.root, "fixture", "verification")
        self.budget = CatalogueBudget(self.root, limits(self.root))

    def test_initialization_never_renews_a_workspace_or_another_install(self):
        before = (self.registry / "allocation.json").read_bytes()
        with self.assertRaisesRegex(InputError, "already initialized"):
            authority.initialize(self.root, self.registry)
        other = self.base / "other"
        other.mkdir()
        with self.assertRaisesRegex(InputError, "already initialized"):
            authority.initialize(other, self.registry)
        self.assertEqual((self.registry / "allocation.json").read_bytes(), before)

    def test_historical_revision_keeps_its_read_only_library_owner(self):
        from sound_search_distribution.runtime import ReadContext, Runtime

        key = "d" * 64
        p = self.root / "data/runs/application/library/revisions" / (key + ".json")
        p.parent.mkdir(parents=True)
        p.write_text("{}")
        view = Runtime(self.root).revision_context(key)
        self.assertIsInstance(view, ReadContext)
        with self.assertRaisesRegex(InputError, "read-only"):
            view.admit(key, MIB)

    def test_full_identity_search_transaction_fits_prepaid_geometry(self):
        owner = Context(self.root, "a" * 64, "verification")
        owner.operation = "search"
        owner.admit("a" * 64, 96 * MIB, jobs=1)
        owner.reserve_attempt("attempt-" + "b" * 32)
        owner.charge(self.budget, read_audio_seconds=123.45678, feature_windows=2)
        owner.terminal(
            "attempt-" + "b" * 32,
            owner.directory / "states/x.json",
            dict(state="complete"),
            elapsed=12.345678,
        )
        owner.release("a" * 64)
        self.assertIsNone(authority.read(self.root)[1]["active"])
        self.assertGreater(owner.pool()["counts"]["job_seconds"], 12)

    def test_doctor_dependency_failures_name_expected_pin(self):
        import importlib.metadata

        from sound_search_distribution.doctor import dependencies

        for name in ("requirements.lock", "requirements-models.lock"):
            shutil.copyfile(ROOT / name, self.root / name)
        with patch(
            "importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError
        ):
            with self.assertRaisesRegex(InputError, "missing dependency cffi"):
                dependencies(self.root)
        with patch("importlib.metadata.version", return_value="wrong"):
            with self.assertRaisesRegex(InputError, "expected 1.17.1, found wrong"):
                dependencies(self.root)

    def test_copy_missing_pool_and_stale_backup_are_explicit_failures(self):
        copied = self.base / "backup"
        shutil.copytree(self.root, copied)
        with self.assertRaisesRegex(InputError, "copied/stale"):
            Context(copied)
        pool = self.owner.directory / "pool.json"
        old = pool.read_bytes()
        self.owner.operation = "save"
        self.owner.admit("fixture", 2 * MIB)
        pool.write_bytes(old)
        with self.assertRaisesRegex(InputError, "stale"):
            self.owner.pool()
        pool.unlink()
        with self.assertRaisesRegex(InputError, "missing"):
            self.owner.pool()

    def test_ordinary_exhaustion_keeps_protected_terminal_and_normal_share(self):
        self.owner.operation = "save"
        self.owner.admit("fixture", 128 * 1024)
        self.owner.reserve_attempt("terminal", seconds=0)
        with self.assertRaises(ResourceError):
            self.owner.charge(self.budget, metadata_bytes=2 * MIB)
        self.owner.terminal(
            "terminal",
            self.owner.directory / "states/x.json",
            dict(state="blocked", error="ordinary exhausted"),
            elapsed=0,
        )
        self.assertEqual(record(self.owner.directory / "states/x.json")["state"], "blocked")
        normal = Context(self.root, share="normal").pool()
        self.assertTrue(all(v == 0 for v in normal["counts"].values()))

    def test_whole_path_reservation_blocks_other_profile_and_survives_reopen(self):
        self.owner.operation = "save"
        self.owner.admit("fixture", 2 * MIB)
        reopened = Context(self.root, "fixture", "verification")
        reopened.operation = "save"
        reopened.admit("fixture", 2 * MIB)
        normal = Context(self.root, "other", "normal")
        with self.assertRaisesRegex(ResourceError, "admitted request"):
            normal.admit("other", MIB)
        self.owner.release("fixture")
        normal.operation = "save"
        normal.admit("other", MIB)
        self.assertEqual(authority.read(self.root)[1]["active"]["share"], "normal")

    def test_complete_search_admission_checks_each_resource_and_disk(self):
        p = self.owner.pool()
        plan = estimate("search", 8)
        self.assertEqual(plan["feature_windows"], 8)
        self.assertEqual(SHARE["feature_windows"], 512)
        for key in ("metadata_bytes", "clips", "workers", "read_audio_seconds"):
            changed = json.loads(json.dumps(p))
            changed["counts"][key] = SHARE[key]
            self.assertFalse(authority.availability(self.root, "verification", changed, plan)[0])
        with patch(
            "sound_search_distribution.authority.shutil.disk_usage",
            return_value=type("D", (), {"free": 1})(),
        ):
            self.assertIn("disk", authority.availability(self.root, "verification", p, plan)[1])

    def test_relocation_preserves_ledger_and_rejects_active_operation(self):
        before = (self.owner.directory / "pool.json").read_bytes()
        destination = self.base / "moved è"
        authority.relocate(self.root, destination)
        self.assertEqual(
            (destination / "data/runs/runtime-verification/pool.json").read_bytes(), before
        )
        self.assertEqual(
            Context(destination).binding["workspace_id"], self.owner.binding["workspace_id"]
        )
        self.assertFalse(self.root.exists())

    def test_portable_paths_archive_hash_duplicates_and_traversal(self):
        for name in ("../x", "C:/x", "a\\b", "AUX.wav", "a/../b", "a./x", 42):
            with self.assertRaises((InputError, ValueError)):
                relative(name)
        archive = self.base / "bad.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("../outside", "bad")
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            bootstrap.extract(archive, self.base / "unpacked", bootstrap.sha(archive))
        self.assertFalse((self.base / "unpacked").exists())
        with self.assertRaisesRegex(ValueError, "SHA256"):
            bootstrap.extract(archive, self.base / "unpacked", "0" * 64)
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("a", "x")
            z.writestr("A", "y")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            bootstrap.extract(archive, self.base / "unpacked", bootstrap.sha(archive))

    def test_missing_changed_inventory_and_existing_environment_refused(self):
        with self.assertRaisesRegex(InputError, "missing/changed"):
            verify_files(self.root, {"missing": dict(bytes=1, sha256="0" * 64)})
        value = dict(release="d03-1.0.0", files={"a": dict(bytes=1, sha256=digest("x"))})
        (self.base / "release.json").write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "Missing/changed"):
            bootstrap.verify(self.base)


if __name__ == "__main__":
    unittest.main()
