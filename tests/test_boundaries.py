import contextlib
import io
import json
import sys
import time
from unittest.mock import patch

from helpers import AudioCase

from similar_sound_search.cli import execute, main
from similar_sound_search.resources import load_limits
from similar_sound_search.storage import InputError, ResourceError, atomic_json, project_lock


class BoundaryTests(AudioCase):
    def cli(self, *arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["--root", str(self.root), *arguments])
        return code, json.loads(output.getvalue())

    def test_offline_smoke_missing_reference_and_reuse(self):
        before = (self.root / "manifests/references/loulou.json").read_bytes()
        # The delivered smoke needs neither network nor an actual reference.
        code, result = self.cli("smoke")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["checks"]["observed_event_sample"], 8000)
        self.assertEqual(result["reference"]["validation_status"], "unverified")
        self.assertEqual(result["reference"]["experiment_status"], "not_run")
        self.assertIn("missing", result["reference"]["reason"])
        self.assertEqual(result["retrieval_quality"], "not_measured")
        self.assertFalse(result["preparation"]["reused"])
        code, repeated = self.cli("smoke")
        self.assertEqual(code, 0, repeated)
        self.assertTrue(repeated["preparation"]["reused"])
        self.assertEqual((self.root / "manifests/references/loulou.json").read_bytes(), before)
        report = json.loads((self.root / "reports/local/smoke.json").read_text())
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["environment"]["tools"]["python"], sys.version.split()[0])

    def test_cli_inspect_prepare_and_actionable_failure(self):
        path = self.wav()
        code, inspected = self.cli("inspect", str(path))
        self.assertEqual(code, 0, inspected)
        code, prepared = self.cli("prepare", str(path), "--rate", "16000", "--channels", "mean")
        self.assertEqual(code, 0, prepared)
        self.assertEqual(prepared["record"]["artifact"]["sample_count"], 16000)
        code, failed = self.cli("prepare", str(path), "--rate", "16000", "--channels", "channel:7")
        self.assertEqual(code, 1)
        self.assertEqual(failed["status"], "failed")
        self.assertIn("zero-based", failed["error"])
        self.assertTrue(failed["report_written"])
        self.assertEqual(
            json.loads((self.root / "reports/local/prepare.json").read_text())["status"], "failed"
        )

    def test_report_cannot_overwrite_input_or_external_paths(self):
        path = self.wav()
        original = path.read_bytes()
        code, failure = self.cli("--report", str(path), "smoke")
        self.assertEqual(code, 1)
        self.assertFalse(failure["report_written"])
        self.assertEqual(path.read_bytes(), original)
        target = self.root / "unrelated.json"
        target.write_text("preserve me")
        code, _ = self.cli("--report", str(target), "smoke")
        self.assertEqual(code, 1)
        self.assertEqual(target.read_text(), "preserve me")

    def test_concurrency_refusal_preserves_previous_report_and_recovers(self):
        report = self.root / "reports/local/inspect.json"
        atomic_json(report, {"previous_run": True})
        path = self.wav()
        with project_lock(self.root):
            with self.assertRaises(ResourceError):
                with project_lock(self.root):
                    self.fail("second operation acquired the lock")
            code, failure = self.cli("inspect", str(path))
            self.assertEqual(code, 1)
            self.assertFalse(failure["report_written"])
            self.assertIn("concurrency", failure["error"])
            self.assertEqual(json.loads(report.read_text()), {"previous_run": True})
        self.assertEqual(self.cli("inspect", str(path))[0], 0)

    def test_actual_worker_timeout_is_explicit_and_retains_no_complete_output(self):
        # Shorter than interpreter startup; directly exercise the production hard-kill boundary.
        request = {
            "root": str(self.root),
            "command": "smoke",
            "limits": {**self.limits, "max_seconds": 0.0001},
        }
        started = time.monotonic()
        result = execute(request)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "ResourceError")
        self.assertIn("terminated", result["error"])
        self.assertLess(time.monotonic() - started, 5)
        self.assertFalse((self.root / "data/audio/prepared").exists())

    def test_invalid_or_incomplete_profiles_do_not_invent_defaults(self):
        profile = json.loads((self.root / "config/resource_limits.json").read_text())
        for key, value in (
            ("max_input_bytes", None),
            ("max_seconds", float("inf")),
            ("concurrency", 2),
            ("max_channels", True),
            ("max_model_candidates", -1),
            ("max_input_bytes", 10**400),
        ):
            with self.subTest(key=key):
                changed = json.loads(json.dumps(profile))
                changed["tiers"]["smoke"][key] = value
                file = self.json_file("config/local/bad.json", changed)
                with self.assertRaises(InputError):
                    load_limits(file, "smoke")
        del profile["tiers"]["smoke"]["max_download_bytes"]
        file = self.json_file("config/local/missing.json", profile)
        with self.assertRaisesRegex(InputError, "requires"):
            load_limits(file, "smoke")
        profile["tiers"] = []
        file = self.json_file("config/local/wrong-shape.json", profile)
        with self.assertRaisesRegex(InputError, "tiers object"):
            load_limits(file, "smoke")

    def test_atomic_report_preserves_previous_json_when_replace_fails(self):
        path = self.root / "reports/local/test.json"
        atomic_json(path, {"old": True})
        with patch("similar_sound_search.storage.os.replace", side_effect=OSError("write failure")):
            with self.assertRaises(OSError):
                atomic_json(path, {"new": True})
        self.assertEqual(json.loads(path.read_text()), {"old": True})
        self.assertEqual(list(path.parent.glob(".a02-report-*")), [])
