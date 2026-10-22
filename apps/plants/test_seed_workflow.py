"""Exercise the fetch, review and import workflow with temporary files."""

import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import TestCase

from apps.plants.management.commands import seed_plants as seed
from apps.plants.models import Plant


class SeedWorkflowTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for attr, filename in (
            ("SEED_PATH", "seeds.json"),
            ("SELECTIONS_PATH", "selections.json"),
            ("CANDIDATES_PATH", "candidates.json"),
            ("DETAILS_PATH", "details.json"),
            ("CURATED_DETAILS_PATH", "curated_details.json"),
            ("REPORT_PATH", "report.txt"),
        ):
            patcher = patch.object(seed, attr, root / filename)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.entries = [
            {"nama_id": "Tanaman A", "query": "species A", "category": "sayur",
             "scientific_name": "Species alpha"},
            {"nama_id": "Tanaman B", "query": "species B", "category": "herbal",
             "scientific_name": "Species beta"},
            {"nama_id": "Tanaman C", "query": "species C", "category": "hias",
             "scientific_name": None},
        ]
        self.selections = [
            {"nama_id": "Tanaman A", "status": "approved", "perenual_id": 12},
            {"nama_id": "Tanaman B", "status": "local_only", "perenual_id": None,
             "reason": "No verified match"},
            {"nama_id": "Tanaman C", "status": "approved", "perenual_id": 4001},
        ]
        self.save_inputs()
        self.command = seed.Command(stdout=StringIO())

    def save_inputs(self):
        seed.SEED_PATH.write_text(json.dumps(self.entries), encoding="utf-8")
        seed.SELECTIONS_PATH.write_text(json.dumps(self.selections), encoding="utf-8")

    def run_mode(self, **options):
        self.command.handle(**options)

    def test_fetch_caches_all_first_page_candidates_and_reuses_results(self):
        with patch.object(self.command, "fetch_candidates", side_effect=[
            {"data": [{"id": 12, "scientific_name": ["Species alpha"]}],
             "current_page": 1, "last_page": 2, "total": 40},
            {"data": []},
        ]) as fetch, patch.object(seed.requests, "Session"), patch.object(seed.time, "sleep"):
            self.run_mode(fetch=True, limit=2)
            self.run_mode(fetch=True, limit=2)
        records = seed.load_candidates()
        self.assertEqual(records[0]["pagination"]["last_page"], 2)
        self.assertEqual(records[1]["status"], "no_results")
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(Plant.objects.count(), 0)

    def test_changed_query_is_refetched_and_old_cache_selection_cleared(self):
        with patch.object(self.command, "fetch_candidates", return_value={"data": [{"id": 12}]}):
            self.run_mode(fetch=True, limit=1)
        records = seed.load_candidates()
        records[0]["selected_perenual_id"] = 12
        seed.save_candidates(records)
        self.entries[0]["query"] = "new query"
        self.save_inputs()
        with patch.object(self.command, "fetch_candidates", return_value={"data": []}):
            self.run_mode(fetch=True, limit=1)
        self.assertIsNone(seed.load_candidates()[0]["selected_perenual_id"])
        self.assertEqual(seed.load_candidates()[0]["status"], "no_results")

    def test_detail_fetch_resumes_and_skips_ids_outside_free_tier(self):
        with patch.object(self.command, "request_json", return_value={
            "id": 12, "sunlight": ["full sun"], "watering": "Average",
        }) as request, patch.object(seed.requests, "Session"), patch.object(seed.time, "sleep"):
            self.run_mode(fetch_details=True)
            self.run_mode(fetch_details=True)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(seed.load_details()[0]["status"], "complete")
        self.assertIn("Skipped (local-only or outside free tier): 2",
                      seed.REPORT_PATH.read_text())

    def test_detail_error_is_cached_as_failed_and_can_resume(self):
        with patch.object(self.command, "request_json", side_effect=CommandError("HTTP 429")):
            with self.assertRaisesMessage(CommandError, "HTTP 429"):
                self.run_mode(fetch_details=True)
        self.assertEqual(seed.load_details()[0]["status"], "failed")
        with patch.object(self.command, "request_json", return_value={"id": 12}):
            self.run_mode(fetch_details=True)
        self.assertEqual(seed.load_details()[0]["status"], "complete")

    def test_import_uses_manifest_and_cached_details(self):
        seed.save_details([{
            "perenual_id": 12, "status": "complete", "data": {
                "id": 12, "sunlight": ["full sun", "part shade"],
                "watering": "Average", "drought_tolerant": False,
                "default_image": {
                    "regular_url": "https://example.com/plant.jpg?X-Amz-Expires=86400",
                },
            },
        }])
        with patch.object(seed.requests, "Session") as session:
            self.run_mode(import_selected=True)
        session.assert_not_called()
        self.assertEqual(Plant.objects.count(), 3)
        a = Plant.objects.get(name="Tanaman A")
        b = Plant.objects.get(name="Tanaman B")
        self.assertEqual(a.sunlight, ["full_sun", "partial_shade"])
        self.assertEqual(a.watering, "Average")
        self.assertIs(a.drought_tolerant, False)
        self.assertEqual(a.image_url, "")
        self.assertIsNone(b.perenual_id)
        self.assertEqual(b.scientific_name, "Species beta")

    def test_import_uses_tracked_curated_details_without_local_cache(self):
        seed.CURATED_DETAILS_PATH.write_text(json.dumps([
            {"id": 12, "sunlight": ["full sun"], "watering": "Average",
             "care_level": "Low", "drought_tolerant": True, "indoor": False},
        ]), encoding="utf-8")
        self.run_mode(import_selected=True)
        a = Plant.objects.get(name="Tanaman A")
        self.assertEqual(a.sunlight, ["full_sun"])
        self.assertEqual(a.care_level, "Low")
        self.assertIs(a.drought_tolerant, True)

    def test_dry_run_rolls_back_every_database_write(self):
        self.run_mode(import_selected=True, dry_run=True)
        self.assertEqual(Plant.objects.count(), 0)
        self.assertIn("Would import: 3", seed.REPORT_PATH.read_text())

    def test_rerun_updates_old_match_and_preserves_nanem_id(self):
        old = Plant.objects.create(
            name="Tanaman B", category="herbal", scientific_name="Wrong plant",
            perenual_id=999, temp_min=20, supports_hydroponic=True,
            description="Wrong species description", sunlight=["shade"],
        )
        self.run_mode(import_selected=True)
        self.run_mode(import_selected=True)
        self.assertEqual(Plant.objects.count(), 3)
        updated = Plant.objects.get(name="Tanaman B")
        self.assertEqual(updated.id, old.id)
        self.assertIsNone(updated.perenual_id)
        self.assertEqual(updated.scientific_name, "Species beta")
        self.assertEqual(updated.temp_min, 20)
        self.assertTrue(updated.supports_hydroponic)
        self.assertEqual(updated.description, "")
        self.assertEqual(updated.sunlight, [])

    def test_rerun_preserves_manual_enrichment_when_source_is_unchanged(self):
        Plant.objects.create(
            name="Tanaman B", category="herbal", scientific_name="Species beta",
            description="Manual description", sunlight=["shade"],
            indoor=False, watering="Average",
        )
        self.run_mode(import_selected=True)
        updated = Plant.objects.get(name="Tanaman B")
        self.assertEqual(updated.description, "Manual description")
        self.assertEqual(updated.sunlight, ["shade"])
        self.assertIs(updated.indoor, False)
        self.assertEqual(updated.watering, "Average")

    def test_conflicting_name_and_external_id_rolls_back_batch(self):
        Plant.objects.create(name="Tanaman A", category="sayur", perenual_id=999)
        Plant.objects.create(name="Other", category="sayur", perenual_id=12)
        with self.assertRaisesMessage(CommandError, "Multiple Plant records"):
            self.run_mode(import_selected=True)
        self.assertEqual(Plant.objects.count(), 2)

    def test_manifest_rejects_duplicate_or_uncached_id(self):
        self.selections[2]["perenual_id"] = 12
        self.save_inputs()
        with self.assertRaisesMessage(CommandError, "duplicate approved"):
            self.run_mode(import_selected=True)
        self.selections[2]["perenual_id"] = 4001
        self.save_inputs()
        seed.save_candidates([{
            **self.entries[0], "source_url": seed.API_URL,
            "status": "needs_review", "candidates": [{"id": 88}],
            "selected_perenual_id": None,
        }])
        with self.assertRaisesMessage(CommandError, "not in cached"):
            self.run_mode(import_selected=True)
        self.assertEqual(Plant.objects.count(), 0)

    def test_limit_imports_only_first_n_but_validates_full_manifest(self):
        self.run_mode(import_selected=True, limit=1)
        self.assertEqual(list(Plant.objects.values_list("name", flat=True)), ["Tanaman A"])

    def test_atomic_file_replace_preserves_previous_cache_on_error(self):
        seed.CANDIDATES_PATH.write_text("[]", encoding="utf-8")
        with patch.object(seed.os, "replace", side_effect=OSError("disk failure")):
            with self.assertRaises(CommandError):
                seed.save_candidates([{"id": 1}])
        self.assertEqual(seed.CANDIDATES_PATH.read_text(), "[]")
