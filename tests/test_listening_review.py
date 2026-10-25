"""D04 model-free oracles; fixture responses/audio are never human listening evidence."""

import copy
import http.client
import json
import runpy
import socket
import sys
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from listening_review import feedback, manifest  # noqa: E402
from listening_review.common import (  # noqa: E402
    MIB,
    ReviewError,
    inventory,
    output_limits,
    put_new,
    read,
    seal,
    sha,
)
from listening_review.server import byte_range, make_server  # noqa: E402


class ListeningReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.review = read(ROOT / "manifests/listening/d04-v1.json")
        self.store = feedback.Store(self.root, self.root / "metadata/feedback", self.review)

    def mutated(self, operation):
        value = copy.deepcopy(self.review)
        del value["record_hash"]
        operation(value)
        return seal(value)

    def test_public_review_has_exact_original_order_and_native_timestamps(self):
        manifest.validate(self.review)
        self.assertEqual(
            [c["scored_interval"] for c in self.review["cards"]],
            [
                "03:11.000–03:13.400",
                "02:00.000–02:02.400",
                "01:37.000–01:39.400",
                "02:43.750–02:46.150",
                "03:14.500–03:16.900",
                "02:18.000–02:20.400",
                "00:07.750–00:10.150",
                "03:08.500–03:10.900",
                "00:10.000–00:12.400",
                "03:23.250–03:25.650",
            ],
        )
        ref = self.review["reference"]["media"]
        self.assertEqual(ref["frames"] / ref["sample_rate_hz"], 22)
        self.assertEqual(ref["source_frames"], [9613800, 10584000])
        self.assertEqual(len(manifest.media_items(self.review)), 21)

    def test_changed_identity_rank_policy_and_duplicate_recording_are_rejected(self):
        changes = [
            lambda v: v.update(job_id="0" * 64),
            lambda v: v.update(selected_arm="event-multi"),
            lambda v: v["cards"].reverse(),
            lambda v: v["cards"][1].update(recording_id=v["cards"][0]["recording_id"]),
            lambda v: v["cards"][1].update(group=v["cards"][0]["group"]),
            lambda v: v["cards"][0].update(scored_interval="00:00.000–00:02.400"),
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ReviewError):
                manifest.validate(self.mutated(change))
        broken = copy.deepcopy(self.review)
        broken["cards"][0]["title"] = "unversioned change"
        with self.assertRaisesRegex(ReviewError, "checksum"):
            manifest.validate(broken)

    def test_native_header_and_byte_identity_are_independent_checks(self):
        path = self.root / "fixture.wav"
        with wave.open(str(path), "wb") as stream:
            stream.setparams((2, 2, 44100, 4, "NONE", "not compressed"))
            stream.writeframes(b"\x00\x00\x01\x00" * 4)
        expected = dict(
            bytes=path.stat().st_size,
            sha256=sha(path),
            frames=4,
            sample_rate_hz=44100,
            channels=2,
            sample_width=2,
        )
        manifest.audio_header(path, expected)
        with self.assertRaisesRegex(ReviewError, "header"):
            manifest.audio_header(path, {**expected, "frames": 5})
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 1
        path.write_bytes(raw)
        with self.assertRaisesRegex(ReviewError, "bytes"):
            manifest.audio_header(path, expected)

    def test_blank_unlistened_unsure_and_declined_are_distinct(self):
        doc = feedback.blank(self.review)
        self.assertEqual(
            feedback.counts(doc),
            dict(
                shown=10,
                listened_rated=0,
                similar=0,
                different=0,
                unsure=0,
                unanswered=10,
                state="pending",
            ),
        )
        doc["items"]["D04-01"]["rating"] = "similar"
        doc["items"]["D04-02"]["rating"] = "different"
        doc["items"]["D04-03"]["rating"] = "unsure"
        count = feedback.counts(doc)
        self.assertEqual(
            (count["listened_rated"], count["unanswered"], count["state"]), (3, 7, "partial")
        )
        doc["participation"] = "declined"
        self.assertEqual(feedback.counts(doc)["state"], "declined")
        self.assertEqual(feedback.counts(doc)["different"], 1)

    def test_feedback_cannot_migrate_or_add_foreign_ids_or_inferred_ratings(self):
        original = feedback.blank(self.review)
        changes = [
            lambda d: d.update(review_hash="f" * 64),
            lambda d: d["items"].update({"D04-11": dict(rating="similar", note="")}),
            lambda d: d["items"].pop("D04-01"),
            lambda d: d["items"]["D04-01"].update(rating="played"),
            lambda d: d["reference"].update(sound="a" * 2001),
            lambda d: d.update(listener=True),
            lambda d: d.update(unknown=True),
        ]
        for change in changes:
            doc = copy.deepcopy(original)
            change(doc)
            with self.subTest(change=change), self.assertRaises(ReviewError):
                feedback.validate(doc, self.review)

    def test_saved_edits_are_immutable_and_stale_parent_never_overwrites(self):
        doc = feedback.blank(self.review)
        first = self.store.save(doc, None, "local-form")
        old_bytes = next(self.store.directory.iterdir()).read_bytes()
        doc["reference"]["section"] = "no"
        doc["reference"]["sound"] = "Unit fixture only, not an actual listening response"
        with self.assertRaises(feedback.Conflict):
            self.store.save(doc, None, "local-form")
        second = self.store.save(doc, first["record_hash"], "imported-file")
        self.assertEqual(len(self.store.snapshots()), 2)
        self.assertEqual(self.store.latest(), second)
        self.assertEqual(sorted(self.store.directory.iterdir())[0].read_bytes(), old_bytes)
        self.assertEqual(second["parent"], first["record_hash"])
        self.assertEqual(second["document"]["reference"]["section"], "no")

    def test_export_import_roundtrip_preserves_review_and_partial_responses(self):
        doc = feedback.blank(self.review)
        doc["items"]["D04-07"] = dict(rating="unsure", note="Unit fixture, not human evidence")
        first = self.store.save(doc, None, "local-form")
        imported = json.loads(json.dumps(first))["document"]
        second = self.store.save(imported, first["record_hash"], "imported-file")
        self.assertEqual(second["document"], doc)
        self.assertEqual(second["counts"]["unanswered"], 9)

    def test_separate_server_handle_cannot_append_while_feedback_is_locked(self):
        other = feedback.Store(self.root, self.store.directory, self.review)
        with self.store.lock():
            with self.assertRaisesRegex(feedback.Conflict, "active"):
                other.save(feedback.blank(self.review), None, "local-form")
        saved = other.save(feedback.blank(self.review), None, "local-form")
        self.assertEqual(saved["revision"], 1)

    def test_atomic_replacement_with_live_size_monitor(self):
        from similar_sound_search.storage import atomic_json

        path = self.root / "construction.json"
        stop = threading.Event()
        errors = []

        def observe():
            try:
                while not stop.is_set():
                    inventory(self.root, transient=True)
                    stop.wait(0.001)
            except OSError as exc:
                errors.append(exc)

        thread = threading.Thread(target=observe)
        thread.start()
        try:
            for number in range(100):
                atomic_json(path, dict(sequence=number))
        finally:
            stop.set()
            thread.join(3)
        self.assertEqual(errors, [])
        self.assertFalse(thread.is_alive())
        self.assertEqual(read(path), dict(sequence=99))

    @unittest.skipUnless(sys.platform == "win32", "Windows native sharing semantics")
    def test_windows_busy_reader_failure_is_explicit_and_release_restores_replacement(self):
        import ctypes
        from ctypes import wintypes

        from similar_sound_search.storage import atomic_json

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        path = self.root / "construction.json"
        atomic_json(path, dict(sequence=0))
        # Deliberately omit FILE_SHARE_DELETE, reproducing the native failure.
        handle = kernel.CreateFileW(str(path), 0x80000000, 0x1 | 0x2, None, 3, 0x80, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try:
            with self.assertRaises(PermissionError):
                atomic_json(path, dict(sequence=1))
            self.assertEqual(read(path), dict(sequence=0))
        finally:
            kernel.CloseHandle(handle)
        atomic_json(path, dict(sequence=2))
        self.assertEqual(read(path), dict(sequence=2))

    def test_corrupt_latest_is_failure_instead_of_previous_success(self):
        first = self.store.save(feedback.blank(self.review), None, "local-form")
        self.store.save(first["document"], first["record_hash"], "local-form")
        latest = sorted(self.store.directory.iterdir())[-1]
        latest.write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.latest()

    def test_failed_save_and_category_caps_do_not_create_a_success(self):
        with patch("listening_review.feedback.output_limits", side_effect=ReviewError("cap")):
            with self.assertRaisesRegex(ReviewError, "cap"):
                self.store.save(feedback.blank(self.review), None, "local-form")
        self.assertEqual(self.store.snapshots(), [])
        output_limits(self.root, 17 * MIB, "bundle")
        with self.assertRaisesRegex(ReviewError, "metadata"):
            output_limits(self.root, 17 * MIB, "metadata")

    def test_amended_qa_preserves_retained_bytes_and_combined_output_limit(self):
        retained = 33997853
        files = {
            "qa/tmp/retained-fixture.wav": retained,
            "qa/other": 224 * MIB - retained,
            "bundle/media": 20 * MIB,
            "metadata/receipts": 11 * MIB,
        }
        with patch("listening_review.common.inventory", return_value=files):
            self.assertEqual(output_limits(self.root, MIB), files)
            # Each category could still fit, but their combined output would not.
            with self.assertRaisesRegex(ReviewError, "total"):
                output_limits(self.root, MIB + 1)
            with self.assertRaisesRegex(ReviewError, "qa/"):
                output_limits(self.root, 1, "qa")
        self.assertEqual(files["qa/tmp/retained-fixture.wav"], retained)

    def check_fixture(self, count, seconds):
        folder = self.root / "metadata/receipts"
        for i in range(count):
            put_new(
                folder / f"{i + 1:02}-start.json",
                dict(label="test fixture only", reserved_source_seconds=0),
            )
            put_new(folder / f"{i + 1:02}-finish.json", dict(seconds=seconds))
        return folder, runpy.run_path(str(ROOT / "scripts/d04-check.py"))["main"]

    def test_amendment_keeps_prior_receipts_and_only_admits_the_24th_invocation(self):
        folder, check = self.check_fixture(23, 25)
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        argv = ["d04-check", "--root", str(self.root), "--label", "fixture", "--", "fixture"]
        with patch.object(sys, "argv", argv), patch("subprocess.Popen") as launch:
            launch.return_value.wait.return_value = 0
            launch.return_value.poll.return_value = 0
            self.assertEqual(check(), 0)
            self.assertEqual(read(folder / "24-start.json")["deadline"], 25)
            with self.assertRaisesRegex(ReviewError, "exhausted"):
                check()
            launch.assert_called_once()
        self.assertEqual({name: (folder / name).read_bytes() for name in before}, before)

    def test_amendment_does_not_reopen_600_seconds_with_unused_invocations(self):
        folder, check = self.check_fixture(10, 60)
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        argv = ["d04-check", "--root", str(self.root), "--label", "fixture", "--", "fixture"]
        with patch.object(sys, "argv", argv), patch("subprocess.Popen") as launch:
            with self.assertRaisesRegex(ReviewError, "exhausted"):
                check()
            launch.assert_not_called()
        self.assertEqual({p.name: p.read_bytes() for p in folder.iterdir()}, before)

    def test_single_ranges_include_suffix_and_reject_invalid_geometry(self):
        self.assertEqual(byte_range("bytes=0-63", 100), (0, 63, True))
        self.assertEqual(byte_range("bytes=-10", 100), (90, 99, True))
        self.assertEqual(byte_range("bytes=95-", 100), (95, 99, True))
        for value in ("bytes=100-", "bytes=7-6", "bytes=-0", "bytes=0-1,2-3", "bytes=-"):
            with self.subTest(value=value), self.assertRaises(ReviewError):
                byte_range(value, 100)

    def start_server(self):
        put_new(self.root / "bundle/review.json", self.review)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        server = make_server(self.root, port)
        thread = threading.Thread(target=server.serve_forever, kwargs=dict(poll_interval=0.01))
        thread.start()

        def stop():
            server.shutdown()
            thread.join(2)
            server.server_close()

        self.addCleanup(stop)
        return port

    def call(self, port, path, value=None, **headers):
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        raw = json.dumps(value).encode() if value is not None else None
        client.request("POST" if raw else "GET", path, body=raw, headers=headers)
        response = client.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        client.close()
        return result

    def test_http_missing_media_foreign_ids_and_no_application_routes(self):
        port = self.start_server()
        status, raw, _ = self.call(port, "/api/bootstrap")
        self.assertEqual(status, 200)
        data = json.loads(raw)
        self.assertTrue(all(not a["available"] for a in data["availability"].values()))
        for path, expected in (
            ("/media/" + self.review["record_hash"] + "/D04-01-scored", 409),
            ("/media/" + "0" * 64 + "/D04-01-scored", 404),
            ("/api/result/" + manifest.RESULT, 404),
            ("/result-media/" + manifest.RESULT + "/" + "0" * 64, 404),
            ("/api/search", 404),
            ("/../allocation.json", 409),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.call(port, path)[0], expected)
        self.assertEqual(self.call(port, "/", Host="evil.example")[0], 409)
        self.assertEqual(self.store.snapshots(), [])

    def test_http_writes_require_origin_token_and_review_bound_document(self):
        port = self.start_server()
        token = json.loads(self.call(port, "/api/bootstrap")[1])["token"]
        value = dict(document=feedback.blank(self.review), parent=None, provenance="local-form")
        good = {
            "Content-Type": "application/json",
            "X-D04-Token": token,
            "Origin": f"http://127.0.0.1:{port}",
        }
        for changes in ({"Origin": "http://evil.example"}, {"X-D04-Token": "stale"}):
            self.assertEqual(self.call(port, "/api/feedback", value, **{**good, **changes})[0], 403)
        foreign = copy.deepcopy(value)
        foreign["document"]["review_hash"] = "0" * 64
        self.assertEqual(self.call(port, "/api/feedback", foreign, **good)[0], 400)
        status, raw, _ = self.call(port, "/api/feedback", value, **good)
        self.assertEqual(status, 201)
        snapshot = json.loads(raw)
        self.assertEqual(self.call(port, "/api/feedback", value, **good)[0], 409)
        status, exported, headers = self.call(
            port, "/feedback/" + snapshot["record_hash"] + ".json"
        )
        self.assertEqual((status, json.loads(exported)["document"]), (200, value["document"]))
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual(len(self.store.snapshots()), 1)


if __name__ == "__main__":
    unittest.main()
