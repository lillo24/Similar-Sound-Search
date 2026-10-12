"""Offline HTTP/ingestion answers, durable budgets, identity, and timestamp boundaries."""

import contextlib
import hashlib
import io
import json
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import numpy as np
import soundfile as sf
from helpers import REPOSITORY, AudioCase

from similar_sound_search.catalogue.ingestion import (
    duplicate_groups,
    entry_key,
    ingest,
    local_descriptor,
)
from similar_sound_search.catalogue.job import load_policy, run, write_manifest
from similar_sound_search.catalogue.source import licence, release, select
from similar_sound_search.catalogue.transfer import Ledger, fetch, public_url
from similar_sound_search.cli import main
from similar_sound_search.inputs import decode, pcm_identity
from similar_sound_search.records import map_time
from similar_sound_search.storage import (
    InputError,
    ResourceError,
    atomic_json,
    project_lock,
    read_json,
)


class CatalogueCase(AudioCase):
    def setUp(self):
        super().setUp()
        self.policy = load_policy(REPOSITORY / "config/catalogue.json")
        self.json_file("config/catalogue.json", self.policy)
        self.policy.update({"request_timeout_seconds": 0.1, "backoff_seconds": 0})
        self.directory = self.root / "data/runs/catalogue/test"
        self.output = self.root / "manifests/catalogue/test"
        self.limits.update({"max_download_bytes": 1000000})
        self.body = self.wav().read_bytes()
        self.calls = []
        case = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                case.calls.append(self.path)
                payload = case.body
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/ok")
                    payload = b"redirect body"
                elif self.path == "/loop":
                    self.send_response(302)
                    self.send_header("Location", "/loop")
                    payload = b""
                elif self.path == "/range":
                    self.send_response(206)
                elif self.path == "/error":
                    self.send_response(503)
                    payload = b"temporary failure"
                else:
                    self.send_response(200)
                if self.path == "/huge":
                    self.send_header("Content-Length", str(10**9))
                elif self.path == "/short":
                    self.send_header("Content-Length", str(len(payload)))
                    payload = payload[:100]
                elif self.path == "/wrong":
                    self.send_header("Content-Length", "10")
                elif self.path != "/no-length":
                    self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if self.path == "/slow":
                    time.sleep(0.3)
                try:
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def ledger(self, **limits):
        return Ledger(self.directory, self.budget(**limits), self.policy)

    def fetch(self, route="/ok", **kwargs):
        return fetch(
            self.url + route,
            self.directory / "staging/download.wav",
            self.ledger(),
            max_bytes=kwargs.pop("max_bytes", 65536),
            allow_local=True,
            **kwargs,
        )

    def descriptor(self, route="/ok", name="recording-a", kind="full_track", offset=None):
        return {
            "provider": "internet_archive",
            "provider_recording_id": name,
            "source_item_id": "test-item",
            "source_page": "https://archive.org/details/test-item",
            "origin_url": self.url + route,
            "file_name": "recording.wav",
            "expected_bytes": len(self.body),
            "expected_md5": hashlib.md5(self.body).hexdigest(),
            "title": "Independent fixture",
            "artist": "Engineering only",
            "album": "Test",
            "version": "known constructed PCM",
            "genre": "engineering",
            "known_family_id": None,
            "source_snapshot": {
                "sha256": "e" * 64,
                "url": "https://archive.org/metadata/test-item",
            },
            "rights": {"permitted_use": "Generated engineering test", "audio_licence_url": None},
            "available_aliases": [],
            "kind": kind,
            "original_recording_offset_seconds": offset,
            "offset_evidence": "Known fixture construction" if offset is not None else None,
            "time_evidence": "Known fixture construction; never a real catalogue recording",
        }

    def ingest(self, descriptor=None, **kwargs):
        return ingest(
            descriptor or self.descriptor(),
            self.directory,
            self.ledger(),
            self.output,
            allow_local_http=True,
            **kwargs,
        )

    def record(self, descriptor=None):
        return read_json(
            self.output / "entries" / (entry_key(descriptor or self.descriptor()) + ".json")
        )


class TransferTests(CatalogueCase):
    def test_locked_disk_accounting_matches_real_files_after_stream_and_preparation(self):
        from similar_sound_search.resources import Budget, CatalogueBudget

        budget = CatalogueBudget(self.root, self.limits)
        ledger = Ledger(self.directory, budget, self.policy)
        descriptor = self.descriptor()
        ingest(descriptor, self.directory, ledger, self.output, allow_local_http=True)
        self.assertEqual(budget.managed_bytes(), Budget(self.root, self.limits).managed_bytes())
        # Replacing a metadata file with smaller/larger content accounts exact final size.
        from similar_sound_search.storage import bounded_json

        path = self.directory / "accounting.json"
        bounded_json(path, {"value": "x" * 5000}, budget)
        bounded_json(path, {"value": "x"}, budget)
        self.assertEqual(budget.managed_bytes(), Budget(self.root, self.limits).managed_bytes())

    def test_per_file_streaming_disk_and_manifest_bounds(self):
        with self.assertRaises(ResourceError):
            self.fetch("/no-length", max_bytes=100)
        self.assertEqual(self.ledger().value["received_bytes"], 101)
        with self.assertRaisesRegex(ResourceError, "managed"):
            self.ledger(max_managed_bytes=1)
        with self.assertRaises(InputError):
            write_manifest(self.output / "too-large.json", {"text": "é" * 200000}, self.budget())
        self.assertFalse((self.output / "too-large.json").exists())

    def test_valid_missing_length_and_redirect_payload_accounting(self):
        self.fetch()
        self.assertEqual((self.directory / "staging/download.wav").read_bytes(), self.body)
        self.fetch("/no-length")
        self.fetch("/redirect")
        ledger = self.ledger()
        self.assertEqual(ledger.value["received_bytes"], len(self.body) * 3 + len(b"redirect body"))
        self.assertEqual(ledger.value["charged_bytes"], ledger.value["received_bytes"])
        self.assertEqual(self.calls, ["/ok", "/no-length", "/redirect", "/ok"])

    def test_headers_truncation_retry_and_error_bodies_remain_charged(self):
        with self.assertRaisesRegex(ResourceError, "Content-Length"):
            self.fetch("/huge")
        self.assertEqual(self.ledger().value["received_bytes"], 0)
        with self.assertRaisesRegex(InputError, "truncated"):
            self.fetch("/short")
        self.assertEqual(self.calls.count("/short"), 2)
        self.assertEqual(self.ledger().value["received_bytes"], 200)
        with self.assertRaisesRegex(InputError, "changed length"):
            self.fetch("/wrong", expected_bytes=len(self.body))
        with self.assertRaisesRegex(InputError, "503"):
            self.fetch("/error")
        self.assertEqual(self.ledger().value["received_bytes"], 200 + 2 * len(b"temporary failure"))
        with self.assertRaises(InputError):
            self.fetch("/range")

    def test_streaming_unknown_length_and_cumulative_resume_limits(self):
        ledger = self.ledger(max_download_bytes=100)
        with self.assertRaisesRegex(ResourceError, "allowance"):
            fetch(
                self.url + "/no-length",
                self.directory / "partial.wav",
                ledger,
                65536,
                allow_local=True,
            )
        self.assertEqual(ledger.value["received_bytes"], 100)
        resumed = self.ledger(max_download_bytes=1000000)
        self.assertEqual(resumed.remaining, 0)
        self.assertEqual(resumed.value["ceilings"]["download_bytes"], 100)
        with self.assertRaises(ResourceError):
            fetch(self.url + "/ok", self.directory / "other.wav", resumed, 65536, allow_local=True)
        self.assertEqual(len(self.calls), 1)

    def test_socket_timeout_and_read_crash_reservations_are_not_refunded(self):
        with self.assertRaises(InputError):
            self.fetch("/slow")
        before = self.ledger().value["charged_bytes"]
        self.assertEqual(before, 2 * len(self.body))

        class Crash(BaseException):
            pass

        response = type("Response", (), {"read": lambda _, n: (_ for _ in ()).throw(Crash())})()
        ledger = self.ledger()
        with self.assertRaises(Crash):
            ledger.read(response, 123)
        resumed = self.ledger()
        self.assertEqual(resumed.value["charged_bytes"], before + 123)
        self.assertEqual(resumed.value["pending_read_bytes"], 123)
        resumed.begin_worker(20)
        resumed = self.ledger()
        self.assertEqual(resumed.value["charged_worker_seconds"], 20)
        resumed.begin_worker(10)
        resumed.end_worker(2)
        self.assertEqual(resumed.value["charged_worker_seconds"], 22)
        resumed.begin_worker(1)
        resumed.end_worker(1.5)
        self.assertEqual(resumed.value["charged_worker_seconds"], 23.5)

    def test_offline_attempt_and_redirect_bounds_and_public_hosts(self):
        with self.assertRaises(ResourceError):
            fetch(
                self.url + "/ok",
                self.directory / "offline.wav",
                self.ledger(max_download_bytes=0),
                65536,
                allow_local=True,
            )
        self.assertEqual(self.calls, [])
        # A fresh disposable ledger for the remaining independent bound checks.
        self.directory = self.directory / "online"
        self.policy["max_http_attempts"] = 3
        with self.assertRaises(ResourceError):
            self.fetch("/loop")
        self.assertEqual(len(self.calls), 3)
        for url in (
            "file:///etc/passwd",
            "https://user:secret@archive.org/file",
            "http://archive.org/x",
            "https://archive.org.evil.test/x",
            "https://archive.org/download/a?token=secret",
        ):
            with self.subTest(url=url), self.assertRaises(InputError):
                public_url(url)
        with self.assertRaises(InputError):
            public_url(self.url)


class IngestionTests(CatalogueCase):
    def test_completed_original_survives_interrupted_preparation_without_redownload(self):
        with patch(
            "similar_sound_search.catalogue.ingestion.prepare",
            side_effect=ResourceError("interrupted preparation"),
        ):
            with self.assertRaises(ResourceError):
                self.ingest()
        self.assertEqual(self.record()["state"], "rejected")
        self.assertEqual(len(list((self.root / "data/audio/catalogue/originals").iterdir())), 1)
        self.assertEqual(self.ingest()["state"], "ready")
        self.assertEqual(self.calls, ["/ok"])

    def test_derivative_corruption_and_metadata_corruption_refuse_reuse(self):
        self.ingest()
        record = self.record()
        derivative = self.root / record["analysis_derivative"]["local_path"]
        original = derivative.read_bytes()
        derivative.write_bytes(b"bad")
        with self.assertRaises(InputError):
            self.ingest()
        self.assertEqual(self.record()["state"], "invalidated")
        derivative.write_bytes(original)
        self.ingest()
        key = entry_key(self.descriptor())
        path = self.directory / "entries" / (key + ".json")
        state = read_json(path)
        state["record"]["recording"]["title"] = "incorrect changed metadata"
        atomic_json(path, state)
        with self.assertRaisesRegex(InputError, "integrity"):
            self.ingest()

    def test_decoder_version_change_refreshes_identity_without_download(self):
        from similar_sound_search.preparation import versions

        self.ingest()
        before = self.record()
        changed = {**versions(), "libsndfile": "simulated-next-decoder"}
        with (
            patch("similar_sound_search.catalogue.ingestion.versions", return_value=changed),
            patch("similar_sound_search.preparation.versions", return_value=changed),
        ):
            self.ingest()
        after = self.record()
        self.assertNotEqual(before["ingestion_identity"], after["ingestion_identity"])
        self.assertNotEqual(before["preparation_key"], after["preparation_key"])
        self.assertEqual(self.calls, ["/ok"])

    def test_real_ingestion_path_local_network_immutable_and_reuse(self):
        descriptor = self.descriptor()
        result = self.ingest(descriptor)
        record = self.record(descriptor)
        self.assertEqual(result["state"], "ready")
        self.assertEqual(record["source_asset"]["sha256"], hashlib.sha256(self.body).hexdigest())
        self.assertEqual(record["source_asset"]["sample_count"], 8000)
        self.assertEqual(record["analysis_derivative"]["sample_count"], 16000)
        self.assertEqual(record["analysis_derivative"]["channels"], 2)
        self.assertEqual((self.root / record["source_asset"]["local_path"]).read_bytes(), self.body)
        received = self.ledger().value["received_bytes"]
        self.assertTrue(self.ingest(descriptor)["reused"])
        self.assertEqual(self.ledger().value["received_bytes"], received)
        self.assertEqual(self.calls, ["/ok"])
        self.assertNotIn(str(self.root), json.dumps(record))
        local = self.wav("local-copy.wav")
        local_descriptor_value = local_descriptor(local, self.context("full_track", 0))
        self.ingest(local_descriptor_value, local_input=local)
        local_record = self.record(local_descriptor_value)
        self.assertEqual(
            local_record["source_asset"]["canonical_pcm"], record["source_asset"]["canonical_pcm"]
        )
        groups = duplicate_groups([record, local_record])
        self.assertEqual(len(groups["groups"]), 1)
        self.assertEqual(len(list((self.root / "data/audio/catalogue/originals").iterdir())), 1)
        self.assertIn("decoded_pcm_sha256", {e["evidence"] for e in groups["edges"]})

    def test_invalid_and_silent_downloads_never_publish_ready_assets(self):
        for body in (b"not audio", self.wav("silent.wav", values={}).read_bytes(), self.body[:100]):
            self.body = body
            descriptor = self.descriptor(name="rejected-" + hashlib.sha256(body).hexdigest())
            with self.assertRaises(InputError):
                self.ingest(descriptor)
            self.assertEqual(self.record(descriptor)["state"], "rejected")
        self.assertFalse((self.root / "data/audio/catalogue/originals").exists())

    def test_changed_payload_requires_explicit_refresh_and_invalidates_ready(self):
        descriptor = self.descriptor()
        self.ingest(descriptor)
        self.body = self.wav("changed.wav", values={(1234, 0): 12000}).read_bytes()
        with self.assertRaisesRegex(InputError, "checksum"):
            self.ingest(descriptor, refresh=True)
        self.assertEqual(self.record(descriptor)["state"], "rejected")
        with self.assertRaisesRegex(InputError, "prior refresh failed"):
            self.ingest(descriptor)
        self.assertEqual(len(self.calls), 2)

    def test_corrupt_original_or_derivative_visible_and_preserved(self):
        self.ingest()
        record = self.record()
        source = self.root / record["source_asset"]["local_path"]
        source.write_bytes(b"corrupt")
        with self.assertRaisesRegex(InputError, "identity changed"):
            self.ingest()
        self.assertEqual(source.read_bytes(), b"corrupt")
        self.assertEqual(self.record()["state"], "invalidated")

    def test_identity_configuration_changes_invalidate_without_redownloading(self):
        descriptor = self.descriptor()
        self.ingest(descriptor)
        before = self.record(descriptor)["ingestion_identity"]
        descriptor["rights"]["permitted_use"] += "; additional required attribution"
        self.assertFalse(self.ingest(descriptor)["reused"])
        self.assertNotEqual(before, self.record(descriptor)["ingestion_identity"])
        self.assertEqual(self.calls, ["/ok"])
        self.policy["analysis_rate_hz"] = 8000
        self.ingest(descriptor)
        self.assertEqual(self.record(descriptor)["analysis_derivative"]["sample_count"], 8000)
        self.assertEqual(self.calls, ["/ok"])

    def test_timestamp_full_known_and_unknown_excerpt_maps(self):
        for kind, offset, expected in (
            ("full_track", 0, 0.5),
            ("excerpt", 218, 218.5),
            ("excerpt", None, None),
        ):
            descriptor = self.descriptor(name=str(offset) + kind, kind=kind, offset=offset)
            self.ingest(descriptor)
            record = self.record(descriptor)
            self.assertEqual(map_time(record, 0.5)["recording_seconds"], expected)
            self.assertEqual(map_time(record, 0.5)["source_seconds"], 0.5)

    def test_local_changed_bytes_new_identity_and_permission_required(self):
        path = self.wav()
        descriptor = local_descriptor(path, self.context())
        self.ingest(descriptor, local_input=path)
        old = self.record(descriptor)["source_asset"]["sha256"]
        self.wav(values={(1000, 0): 12000})
        self.ingest(descriptor, local_input=path)
        self.assertNotEqual(self.record(descriptor)["source_asset"]["sha256"], old)
        self.assertEqual(len(list((self.root / "data/audio/catalogue/originals").iterdir())), 2)
        self.assertEqual(self.calls, [])
        with self.assertRaisesRegex(InputError, "permitted_use"):
            local_descriptor(path, None)


class DecoderAndSelectionTests(CatalogueCase):
    def test_provider_declared_snippet_preserves_unknown_excerpt_offset(self):
        descriptor = {
            **self.descriptor(),
            "artist": "Fixture artist",
            "title": "Instrumental (Snippet)",
            "genre": "Electronic",
            "kind": "full_track",
        }
        selection = select([{"candidates": [descriptor]}], self.policy)
        selected = selection["entries"][0]
        self.assertEqual(selected["kind"], "excerpt")
        self.assertIsNone(selected["original_recording_offset_seconds"])
        self.assertIsNone(selected["offset_evidence"])
        self.ingest(selected)
        record = self.record(selected)
        self.assertEqual(record["source_asset"]["kind"], "excerpt")
        self.assertIsNone(record["timestamp_mapping"]["original_recording_offset_seconds"])

    def test_distinct_audio_same_titles_stays_separate_and_groups_are_order_stable(self):
        first_descriptor = self.descriptor(name="first")
        self.ingest(first_descriptor)
        first = self.record(first_descriptor)
        self.body = self.wav("second.wav", values={(1234, 0): 12000}).read_bytes()
        second_descriptor = self.descriptor(name="second")
        self.ingest(second_descriptor)
        second = self.record(second_descriptor)
        self.assertEqual(first["recording"]["title"], second["recording"]["title"])
        groups = duplicate_groups([first, second])
        self.assertEqual(len(groups["groups"]), 2)
        self.assertEqual(groups, duplicate_groups([second, first]))
        second["recording"]["known_family_id"] = "provider-family"
        first["recording"]["known_family_id"] = "provider-family"
        self.assertEqual(len(duplicate_groups([first, second])["groups"]), 1)

    def test_canonical_pcm_independent_serialization_and_alternate_encodings(self):
        samples = np.array([[0.5, -0.25], [-0.0, 0.0]], dtype=np.float32)
        header = (
            b'{"channels":2,"sample_count":2,"sample_rate_hz":8000,'
            b'"schema_version":"sss-pcm-f32le-1"}\n'
        )
        expected = hashlib.sha256(header + struct.pack("<ffff", 0.5, -0.25, 0, 0)).hexdigest()
        self.assertEqual(pcm_identity(samples, 8000)["sha256"], expected)
        hashes = []
        for ext, encoding in (("wav", "PCM_16"), ("flac", "PCM_16")):
            path = self.root / ("same." + ext)
            sf.write(path, samples, 8000, subtype=encoding)
            _, metadata = decode(path, self.budget())
            hashes.append(metadata["canonical_pcm"]["sha256"])
        self.assertEqual(hashes, [expected, expected])
        self.assertNotEqual(pcm_identity(samples, 16000)["sha256"], expected)

    def test_mp3_sequential_delay_padding_counts_and_truncation(self):
        for rate in (32000, 44100, 48000):
            samples = np.zeros((rate * 2, 2), dtype=np.float32)
            samples[rate // 2, 0] = 0.75
            samples[rate, 1] = 0.5
            path = self.root / f"known-{rate}.mp3"
            sf.write(path, samples, rate, format="MP3", subtype="MPEG_LAYER_III")
            actual, metadata = decode(path, self.budget())
            self.assertEqual(actual.shape, (rate * 2, 2))
            self.assertEqual(int(np.argmax(np.abs(actual[:, 0]))), rate // 2)
            self.assertEqual(int(np.argmax(np.abs(actual[:, 1]))), rate)
            self.assertFalse(metadata["decoder"]["compressed_seek_verified"])
            encoded = path.read_bytes()
            path.write_bytes(encoded[:-100])
            with self.assertRaisesRegex(InputError, "truncated"):
                decode(path, self.budget())

    def test_selection_is_stable_artist_capped_and_not_title_deduplication(self):
        entries = []
        for genre in ("electronic", "jazz", "rock"):
            for artist in ("A", "B", "C"):
                for n in range(3):
                    entry = self.descriptor(name=genre + artist + str(n))
                    entry.update({"genre": genre, "artist": artist})
                    entries.append(entry)
        policy = {**self.policy, "max_requested_recordings": 6, "max_tracks_per_artist": 2}
        a = select([{"candidates": entries}], policy)
        b = select([{"candidates": list(reversed(entries))}], policy)
        self.assertEqual(a, b)
        self.assertEqual(a["eligible_recordings"], 27)
        self.assertEqual(len({e["genre"] for e in a["entries"]}), 3)
        uneven = select([{"candidates": entries}], {**policy, "max_requested_recordings": 5})
        self.assertEqual(len(uneven["entries"]), 5)
        self.assertTrue(
            all(sum(e["artist"] == artist for e in a["entries"]) == 2 for artist in ("A", "B", "C"))
        )

    def test_provider_alternate_files_and_rights_snapshot(self):
        provider = {
            "metadata": {
                "licenseurl": "https://creativecommons.org/licenses/by-sa/4.0/",
                "title": "Album",
            },
            "files": [
                {
                    "name": "original.mp3",
                    "size": "4000",
                    "md5": "a" * 32,
                    "length": "90",
                    "artist": "Artist",
                    "title": "Song",
                    "track": "1",
                    "format": "VBR MP3",
                },
                {
                    "name": "alternate.mp3",
                    "original": "original.mp3",
                    "size": "3000",
                    "md5": "b" * 32,
                    "length": "90",
                },
            ],
        }
        evidence = {"url": "https://archive.org/metadata/test", "sha256": "c" * 64}
        with patch(
            "similar_sound_search.catalogue.source.cached_json", return_value=(provider, evidence)
        ):
            result = release("test", self.directory, self.ledger())
        self.assertEqual(len(result["candidates"]), 1)
        entry = result["candidates"][0]
        self.assertEqual(entry["file_name"], "original.mp3")
        self.assertEqual(len(entry["available_aliases"]), 1)
        self.assertEqual(entry["rights"]["evidence_sha256"], "c" * 64)
        self.assertEqual(licence(provider["metadata"]["licenseurl"]), "CC BY-SA 4.0")
        self.assertIsNone(licence("https://creativecommons.org/licenses/by-nc-nd/3.0/"))
        self.assertIsNone(licence("https://evil.test/licenses/by/4.0/"))

    def test_cli_explicit_import_resume_and_concurrent_orphan_refusal(self):
        path = self.wav()
        context_path = self.json_file("config/local/import.json", self.context("full_track", 0))

        def cli():
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    [
                        "--root",
                        str(self.root),
                        "catalogue",
                        "import",
                        str(path),
                        "--context",
                        str(context_path),
                        "--job",
                        "local",
                        "--data-role",
                        "engineering",
                    ]
                )
            return code, json.loads(output.getvalue())

        code, result = cli()
        self.assertEqual(code, 0, result)
        self.assertEqual(result["counts"]["ready_assets"], 1)
        self.assertEqual(result["counts"]["real_ready_assets"], 0)
        self.assertEqual(result["ledger"]["received_bytes"], 0)
        self.assertEqual(cli()[1]["reused_this_invocation"], 1)
        with project_lock(self.root, ".a03-worker.lock"):
            code, result = cli()
            self.assertEqual(code, 1)
            self.assertIn("concurrency", result["error"])

    def test_invalid_policy_and_missing_network_are_explicit(self):
        policy = dict(self.policy)
        policy["attempts_per_url"] = 0
        path = self.json_file("config/local/bad-policy.json", policy)
        with self.assertRaises(InputError):
            load_policy(path)
        request = {
            "root": str(self.root),
            "limits": self.budget(max_download_bytes=0).limits,
            "catalogue_policy": str(REPOSITORY / "config/catalogue.json"),
            "catalogue_action": "acquire",
            "job": "offline",
            "take": 12,
            "refresh": False,
        }
        from similar_sound_search.cli import execute

        result = run(request, execute)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["counts"]["ready_assets"], 0)
        self.assertEqual(result["ledger"]["received_bytes"], 0)
        self.assertEqual(result["assessment"], "partial")

    def test_batched_verification_cursor_and_manifests_without_local_state(self):
        from similar_sound_search.cli import execute

        self.output = self.root / "manifests/private/catalogue/test"
        policy = {**self.policy, "max_operations_per_invocation": 1}
        policy_path = self.json_file("config/local/batch-policy.json", policy)
        selected = []
        for index in range(3):
            path = self.wav(f"batch-{index}.wav", values={(1000 + index, 0): 12000})
            context = self.context()
            context["recording"]["recording_id"] = "independent-" + str(index)
            descriptor = local_descriptor(path, context, "engineering")
            self.ingest(descriptor, local_input=path)
            key = entry_key(descriptor)
            write_manifest(
                self.directory / "selection" / (key + ".json"), descriptor, self.budget()
            )
            from similar_sound_search.storage import digest

            selected.append({"entry_id": key, "descriptor_sha256": digest(descriptor)})
        write_manifest(
            self.directory / "job.json",
            {"identity": {"source": "local", "policy": policy}},
            self.budget(),
        )
        write_manifest(
            self.output / "selection.json",
            {"selected": selected, "requested_count": 3},
            self.budget(),
        )
        request = {
            "root": str(self.root),
            "limits": self.limits,
            "catalogue_policy": str(policy_path),
            "catalogue_action": "verify",
            "job": "test",
        }
        visited = []

        def bounded_execute(child):
            visited.append(child["entry_id"])
            return execute(child)

        for _ in range(3):
            result = run(request, bounded_execute)
        self.assertEqual(visited, [item["entry_id"] for item in selected])
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["counts"]["ready_assets"], 3)
        for path in (self.directory / "entries").glob("*.json"):
            path.unlink()
        result = run(
            request,
            lambda child: {
                "status": "failed",
                "error_type": "ResourceError",
                "error": "controlled stop",
            },
        )
        self.assertEqual(result["counts"]["ready_assets"], 0)
        self.assertEqual(result["counts"]["states"]["not_locally_ready"], 3)
