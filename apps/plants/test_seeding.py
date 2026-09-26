"""Offline seeding tests: no real API requests, migrations or database writes."""
import json
from contextlib import nullcontext
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import requests
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.plants.management.commands import seed_plants as seed


class SeedPlantsTests(SimpleTestCase):
    def setUp(self):
        self.entry = {"nama_id": "Nama lokal uji", "query": "test query", "category": "sayur"}
        self.command = seed.Command(stdout=StringIO())

    def test_sunlight_prefers_most_shade_tolerant(self):
        for values, expected in [
            (["full sun", "part shade", "full shade"], "shade"),
            (["full_sun", "sun-part_shade"], "partial_shade"),
            (["Full Sun"], "full_sun"),
            (["part sun/part shade"], "partial_shade"),
            (["unknown", None], ""),
            (None, ""),
            ("full sun", ""),
        ]:
            with self.subTest(values=values):
                self.assertEqual(seed.map_sunlight(values), expected)

    def test_mapping_uses_curated_identity_and_only_response_data(self):
        fields = seed.map_match(self.entry, {
            "id": 123, "common_name": "Not the display name", "category": "hias",
            "scientific_name": ["Species test"], "description": "API description",
            "default_image": {"regular_url": "https://example.com/plant.jpg"},
            "sunlight": ["full sun", "part shade"],
        })
        self.assertEqual(fields, {
            "perenual_id": 123, "name": "Nama lokal uji", "category": "sayur",
            "scientific_name": "Species test", "description": "API description",
            "image_url": "https://example.com/plant.jpg", "sunlight": "partial_shade",
        })

    def test_missing_optional_api_fields_are_blank(self):
        fields = seed.map_match(self.entry, {"id": 123})
        for name in ("scientific_name", "description", "image_url", "sunlight"):
            self.assertEqual(fields[name], "")
        self.assertNotIn("space_needed", fields)
        self.assertNotIn("temp_min", fields)

    def test_long_image_url_is_preserved(self):
        url = "https://example.com/" + "a" * 300 + ".jpg"
        fields = seed.map_match(self.entry, {
            "id": 123, "default_image": {"original_url": url},
        })
        self.assertEqual(fields["image_url"], url)

    def test_invalid_or_oversized_image_url_is_still_rejected(self):
        for url in ("not-a-url", "https://example.com/" + "a" * 2048):
            with self.subTest(url_length=len(url)), self.assertRaisesMessage(CommandError, "image_url"):
                seed.map_match(self.entry, {
                    "id": 123, "default_image": {"original_url": url},
                })

    def test_invalid_match_id_is_rejected(self):
        for match in ({}, {"id": None}, {"id": True}, {"id": "wrong"}):
            with self.subTest(match=match), self.assertRaises(CommandError):
                seed.map_match(self.entry, match)

    def test_preserves_all_candidates_and_query_parameter(self):
        session = Mock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {"data": [{"id": 12}, {"id": 13}]}
        self.assertEqual(self.command.fetch_candidates(session, "test-key", "water spinach"),
                         {"data": [{"id": 12}, {"id": 13}]})
        session.get.assert_called_once_with(
            seed.API_URL, params={"key": "test-key", "q": "water spinach"},
            timeout=30, allow_redirects=False,
        )

    def test_auth_rate_limit_and_other_http_errors_stop(self):
        for status in (401, 403, 429, 500, 302):
            session = Mock()
            session.get.return_value.status_code = status
            with self.subTest(status=status), self.assertRaises(CommandError):
                self.command.fetch_candidates(session, "test-key", "test")

    def test_quota_display_uses_response_headers_without_extra_requests(self):
        for status, remaining in ((200, "91"), (429, "0")):
            with self.subTest(status=status):
                output = StringIO()
                command = seed.Command(stdout=output)
                session = Mock()
                response = session.get.return_value
                response.status_code = status
                response.headers = {"X-RateLimit-Remaining": remaining, "X-RateLimit-Limit": "100"}
                response.json.return_value = {"data": []}
                if status == 429:
                    with self.assertRaises(CommandError):
                        command.fetch_candidates(session, "secret-key", "test")
                else:
                    command.fetch_candidates(session, "secret-key", "test")
                session.get.assert_called_once()
                self.assertIn(f"Sisa kuota: {remaining} / 100", output.getvalue())
                self.assertNotIn("secret-key", output.getvalue())

    def test_missing_quota_headers_do_not_guess_remaining(self):
        session = Mock()
        session.get.return_value.status_code = 200
        session.get.return_value.headers = {}
        session.get.return_value.json.return_value = {"data": []}
        self.command.fetch_candidates(session, "secret-key", "test")
        self.assertIn("Sisa kuota: tidak tersedia / tidak tersedia", self.command.stdout._out.getvalue())

    def test_api_errors_are_not_counted_as_empty_results(self):
        session = Mock()
        session.get.return_value.status_code = 200
        for payload in ({"error": "quota"}, {"data": [], "message": "invalid key"},
                        {}, {"data": None}, {"data": [None]}, []):
            session.get.return_value.json.return_value = payload
            with self.subTest(payload=payload), self.assertRaises(CommandError):
                self.command.fetch_candidates(session, "test-key", "test")
        session.get.return_value.json.side_effect = ValueError("not JSON")
        with self.assertRaises(CommandError):
            self.command.fetch_candidates(session, "test-key", "test")

    def test_network_error_does_not_expose_api_key(self):
        session = Mock()
        session.get.side_effect = requests.Timeout("URL contains secret-key")
        with self.assertRaises(CommandError) as caught:
            self.command.fetch_candidates(session, "secret-key", "test")
        self.assertNotIn("secret-key", str(caught.exception))

    def test_seed_file_validation_and_limit(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "seeds.json"
            with patch.object(seed, "SEED_PATH", path):
                with self.assertRaises(CommandError):
                    self.command.load_entries(None)
                path.write_text(json.dumps([self.entry, dict(self.entry, nama_id="Other")]), encoding="utf-8")
                self.assertEqual(self.command.load_entries(1), [self.entry])
                self.assertEqual(self.command.load_entries(0), [])
                with self.assertRaises(CommandError):
                    self.command.load_entries(-1)
                path.write_text('[{"nama_id": "Incomplete"}]', encoding="utf-8")
                with self.assertRaises(CommandError):
                    self.command.load_entries(None)

    def test_existing_id_or_name_is_updated_without_touching_climate(self):
        fields = seed.map_match(self.entry, {"id": 123})
        plant = Mock(temp_min=20, space_needed="small", supports_hydroponic=True)
        with patch.object(seed.transaction, "atomic", return_value=nullcontext()), \
                patch.object(seed.Plant, "objects") as manager:
            manager.select_for_update.return_value.filter.return_value = [plant]
            self.command.save_match(fields)
            manager.select_for_update.return_value.filter.assert_called_once_with(
                seed.Q(perenual_id=123) | seed.Q(name=self.entry["nama_id"])
            )
            manager.create.assert_not_called()
            self.assertEqual(plant.name, self.entry["nama_id"])
            self.assertEqual(plant.temp_min, 20)
            self.assertEqual(plant.space_needed, "small")
            self.assertTrue(plant.supports_hydroponic)
            self.assertEqual(set(plant.save.call_args.kwargs["update_fields"]), {*fields, "updated_at"})

    def test_rerun_reuses_created_record(self):
        fields = seed.map_match(self.entry, {"id": 123})
        with patch.object(seed.transaction, "atomic", return_value=nullcontext()), \
                patch.object(seed.Plant, "objects") as manager:
            records = []
            manager.select_for_update.return_value.filter.side_effect = lambda *a: records
            manager.create.side_effect = lambda **kw: records.append(Mock(**kw))
            self.command.save_match(fields)
            self.command.save_match(fields)
            manager.create.assert_called_once_with(**fields)
            records[0].save.assert_called_once()

    def test_conflicting_matches_are_not_silently_merged(self):
        with patch.object(seed.transaction, "atomic", return_value=nullcontext()), \
                patch.object(seed.Plant, "objects") as manager:
            manager.select_for_update.return_value.filter.return_value = [Mock(), Mock()]
            with self.assertRaises(CommandError):
                self.command.save_match(seed.map_match(self.entry, {"id": 123}))
            manager.create.assert_not_called()
