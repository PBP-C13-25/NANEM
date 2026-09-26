"""Exercise fetch/review/import against temporary files and mocked IO only."""
import json
from contextlib import nullcontext
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.plants.management.commands import seed_plants as seed


class SeedWorkflowTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for attr, name in (("SEED_PATH", "seeds.json"),
                           ("CANDIDATES_PATH", "candidates.json"),
                           ("REPORT_PATH", "report.txt")):
            self.start_patch(patch.object(seed, attr, root / name))
        self.start_patch(patch.dict(seed.os.environ, {"PERENUAL_API_KEY": "test-key"}))
        self.session = self.start_patch(patch.object(seed.requests, "Session"))
        self.sleep = self.start_patch(patch.object(seed.time, "sleep"))
        self.start_patch(patch.object(seed.transaction, "atomic", side_effect=lambda: nullcontext()))
        self.command = seed.Command(stdout=StringIO())
        self.fetch = self.start_patch(patch.object(self.command, "fetch_candidates"))
        self.save = self.start_patch(patch.object(self.command, "save_match"))
        self.entries = [
            {"nama_id": "Tanaman A", "query": "query A", "category": "sayur"},
            {"nama_id": "Tanaman B", "query": "query B", "category": "herbal"},
            {"nama_id": "Tanaman C", "query": "query C", "category": "hias"},
        ]
        self.write_seeds()

    def start_patch(self, patcher):
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def write_seeds(self):
        seed.SEED_PATH.write_text(json.dumps(self.entries), encoding="utf-8")

    def run_fetch(self, **options):
        self.command.handle(fetch=True, import_selected=False, **options)

    def run_import(self, **options):
        self.command.handle(fetch=False, import_selected=True, **options)

    def prepare_selection(self, selected=12):
        self.fetch.return_value = {"data": [{"id": 11}, {"id": 12, "description": "API data"}]}
        self.run_fetch(limit=1)
        records = seed.load_candidates()
        records[0]["selected_perenual_id"] = selected
        seed.save_candidates(records)
        self.fetch.reset_mock()
        self.session.reset_mock()

    def test_fetch_caches_full_candidates_without_database_writes(self):
        payload = {"data": [{"id": 1, "scientific_name": ["Species A"]}, {"id": 2}],
                   "current_page": 1, "last_page": 4, "total": 100}
        self.fetch.side_effect = [payload, {"data": []}]
        self.run_fetch(limit=2)
        records = seed.load_candidates()
        self.assertEqual(records[0]["candidates"], payload["data"])
        self.assertEqual(records[0]["pagination"]["last_page"], 4)
        self.assertIsNone(records[0]["selected_perenual_id"])
        self.assertEqual(records[1]["status"], "no_results")
        self.assertTrue(records[0]["fetched_at"])
        self.sleep.assert_called_once_with(0.75)
        self.save.assert_not_called()
        self.assertIn("Plant database writes: 0", seed.REPORT_PATH.read_text())

    def test_completed_and_empty_queries_are_reused_without_key(self):
        self.fetch.side_effect = [{"data": [{"id": 1}]}, {"data": []}]
        self.run_fetch(limit=2)
        self.fetch.reset_mock()
        with patch.dict(seed.os.environ, {"PERENUAL_API_KEY": ""}):
            self.run_fetch(limit=2)
        self.fetch.assert_not_called()
        self.assertIn("Reused from cache: 2", seed.REPORT_PATH.read_text())

    def test_resumes_failed_query_preserving_completed_work(self):
        self.fetch.side_effect = [{"data": [{"id": 1}]}, CommandError("ReadTimeout")]
        with self.assertRaisesMessage(CommandError, "ReadTimeout"):
            self.run_fetch()
        records = seed.load_candidates()
        self.assertEqual([r["status"] for r in records], ["needs_review", "failed"])
        self.fetch.reset_mock()
        self.fetch.side_effect = [{"data": []}, {"data": [{"id": 3}]}]
        self.run_fetch()
        self.assertEqual([call.args[2] for call in self.fetch.call_args_list], ["query B", "query C"])
        self.assertEqual(len(seed.load_candidates()), 3)

    def test_changed_query_invalidates_selection_even_when_request_fails(self):
        self.prepare_selection()
        self.entries[0]["query"] = "new query"
        self.write_seeds()
        self.fetch.side_effect = CommandError("HTTP 429")
        with self.assertRaisesMessage(CommandError, "HTTP 429"):
            self.run_fetch(limit=1)
        record = seed.load_candidates()[0]
        self.assertIsNone(record["selected_perenual_id"])
        self.assertEqual(record["candidates"], [])
        self.assertEqual(record["query"], "new query")
        self.run_import()
        self.save.assert_not_called()

    def test_refresh_clears_selection_and_fetches_again(self):
        self.prepare_selection()
        self.run_fetch(limit=1, refresh=True)
        self.fetch.assert_called_once()
        self.assertIsNone(seed.load_candidates()[0]["selected_perenual_id"])

    def test_normal_fetch_preserves_selection(self):
        self.prepare_selection()
        self.run_fetch(limit=1)
        self.fetch.assert_not_called()
        self.assertEqual(seed.load_candidates()[0]["selected_perenual_id"], 12)

    def test_import_selected_is_offline_and_does_not_require_key(self):
        self.prepare_selection()
        with patch.dict(seed.os.environ, {"PERENUAL_API_KEY": ""}):
            self.run_import()
        self.session.assert_not_called()
        self.fetch.assert_not_called()
        self.save.assert_called_once()
        fields = self.save.call_args.args[0]
        self.assertEqual(fields["perenual_id"], 12)
        self.assertEqual(fields["name"], "Tanaman A")
        self.assertEqual(fields["description"], "API data")
        self.assertIn("Skipped (not selected): 2", seed.REPORT_PATH.read_text())

    def test_unselected_cache_does_not_import_first_result(self):
        self.prepare_selection(selected=None)
        self.run_import()
        self.save.assert_not_called()
        self.fetch.assert_not_called()

    def test_unknown_or_non_integer_selected_id_is_rejected(self):
        self.prepare_selection()
        for selected in (999, "12", True):
            records = seed.load_candidates()
            records[0]["selected_perenual_id"] = selected
            seed.save_candidates(records)
            with self.subTest(selected=selected), self.assertRaises(CommandError):
                self.run_import()
        self.save.assert_not_called()

    def test_import_refuses_stale_query_without_fetch(self):
        self.prepare_selection()
        self.entries[0]["query"] = "changed"
        self.write_seeds()
        with self.assertRaisesMessage(CommandError, "query/source changed"):
            self.run_import()
        self.save.assert_not_called()

    def test_import_uses_current_category_and_ignores_removed_entries(self):
        self.prepare_selection()
        self.entries[0]["category"] = "buah"
        self.write_seeds()
        self.run_import()
        self.assertEqual(self.save.call_args.args[0]["category"], "buah")
        self.save.reset_mock()
        self.entries.pop(0)
        self.write_seeds()
        self.run_import()
        self.save.assert_not_called()

    def test_duplicate_selections_rejected_before_any_writes(self):
        self.prepare_selection()
        record = seed.load_candidates()[0]
        duplicate = dict(record, **self.entries[1])
        seed.save_candidates([record, duplicate])
        with self.assertRaisesMessage(CommandError, "multiple names"):
            self.run_import()
        self.save.assert_not_called()

    def test_invalid_later_selection_prevents_partial_import(self):
        self.prepare_selection()
        record = seed.load_candidates()[0]
        invalid = dict(record, **self.entries[1], selected_perenual_id=999)
        seed.save_candidates([record, invalid])
        with self.assertRaises(CommandError):
            self.run_import()
        self.save.assert_not_called()

    def test_database_error_reports_no_applied_batch(self):
        self.prepare_selection()
        self.save.side_effect = DatabaseError("sensitive backend details")
        with self.assertRaisesMessage(CommandError, "Database write failed"):
            self.run_import()
        report = seed.REPORT_PATH.read_text()
        self.assertIn("Imported: 0 (batch not applied)", report)
        self.assertNotIn("sensitive", report)

    def test_corrupt_cache_is_not_overwritten(self):
        seed.CANDIDATES_PATH.write_text("{broken", encoding="utf-8")
        with self.assertRaises(CommandError):
            self.run_fetch()
        self.assertEqual(seed.CANDIDATES_PATH.read_text(), "{broken")
        self.fetch.assert_not_called()

    def test_failed_atomic_replace_keeps_previous_file(self):
        seed.CANDIDATES_PATH.write_text("[]", encoding="utf-8")
        with patch.object(seed.os, "replace", side_effect=OSError("disk failure")):
            with self.assertRaises(CommandError):
                seed.save_candidates([{"new": "data"}])
        self.assertEqual(seed.CANDIDATES_PATH.read_text(), "[]")

    def test_missing_key_records_failure_without_request(self):
        with patch.dict(seed.os.environ, {"PERENUAL_API_KEY": ""}):
            with self.assertRaisesMessage(CommandError, "PERENUAL_API_KEY"):
                self.run_fetch(limit=1)
        self.fetch.assert_not_called()
        self.assertEqual(seed.load_candidates()[0]["status"], "failed")

    def test_explicit_mode_required_and_refresh_import_rejected(self):
        for options in ({}, {"fetch": True, "import_selected": True},
                        {"import_selected": True, "refresh": True}):
            with self.subTest(options=options), self.assertRaises(CommandError):
                self.command.handle(**options)
        self.fetch.assert_not_called()
        self.save.assert_not_called()

    def test_limit_zero_makes_no_requests(self):
        self.run_fetch(limit=0)
        self.fetch.assert_not_called()
        self.save.assert_not_called()
