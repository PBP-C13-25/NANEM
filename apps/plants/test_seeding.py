"""Focused offline tests for curated Plant field mapping."""

from io import StringIO
from unittest.mock import Mock

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.plants.management.commands import seed_plants as seed


class FieldMappingTests(SimpleTestCase):
    def setUp(self):
        self.entry = {
            "nama_id": "Pakcoy",
            "query": "Brassica rapa",
            "category": "sayur",
            "scientific_name": "Brassica rapa subsp. chinensis",
        }
        self.selection = {"nama_id": "Pakcoy", "status": "approved", "perenual_id": 1330}

    def test_sunlight_retains_all_supported_values(self):
        self.assertEqual(
            seed.map_sunlight(["full sun", "part shade", "full shade", "full sun"]),
            ["full_sun", "partial_shade", "shade"],
        )
        self.assertEqual(seed.map_sunlight(["unknown", None]), [])
        self.assertEqual(seed.map_sunlight("full sun"), [])

    def test_details_fill_only_available_fields(self):
        fields = seed.map_match(self.entry, self.selection, {
            "id": 1330,
            "common_name": "pak-choi",
            "description": "API description",
            "sunlight": ["full sun", "part shade"],
            "watering": "Average",
            "care_level": "Medium",
            "drought_tolerant": False,
            "indoor": True,
            "default_image": {"regular_url": "https://example.com/plant.jpg"},
        })
        self.assertEqual(fields["name"], "Pakcoy")
        self.assertEqual(fields["scientific_name"], "Brassica rapa subsp. chinensis")
        self.assertEqual(fields["category"], "sayur")
        self.assertEqual(fields["sunlight"], ["full_sun", "partial_shade"])
        self.assertEqual(fields["watering"], "Average")
        self.assertEqual(fields["care_level"], "Medium")
        self.assertIs(fields["drought_tolerant"], False)
        self.assertIs(fields["indoor"], True)
        self.assertEqual(fields["image_url"], "https://example.com/plant.jpg")

    def test_missing_details_stay_unknown(self):
        fields = seed.map_match(self.entry, self.selection)
        self.assertEqual(fields["sunlight"], [])
        self.assertEqual(fields["watering"], "")
        self.assertEqual(fields["care_level"], "")
        self.assertIsNone(fields["drought_tolerant"])
        self.assertIsNone(fields["indoor"])
        self.assertEqual(fields["description"], "")
        self.assertEqual(fields["image_url"], "")

    def test_local_only_entry_uses_null_external_id(self):
        selection = {
            "nama_id": "Pakcoy",
            "status": "local_only",
            "perenual_id": None,
            "reason": "No reliable candidate",
        }
        self.assertIsNone(seed.map_match(self.entry, selection)["perenual_id"])

    def test_expiring_or_placeholder_image_is_never_imported(self):
        self.assertEqual(seed.stable_image_url({
            "regular_url": "https://example.com/plant.jpg?X-Amz-Expires=86400",
        }), "")
        self.assertEqual(seed.stable_image_url({
            "regular_url": "https://example.com/image/upgrade_access.jpg",
        }), "")

    def test_detail_id_mismatch_is_rejected(self):
        with self.assertRaisesMessage(CommandError, "detail id"):
            seed.map_match(self.entry, self.selection, {"id": 123})

    def test_oversized_scientific_name_is_rejected(self):
        entry = dict(self.entry, scientific_name="x" * 201)
        with self.assertRaisesMessage(CommandError, "scientific_name"):
            seed.map_match(entry, self.selection)


class RequestHandlingTests(SimpleTestCase):
    def setUp(self):
        self.command = seed.Command(stdout=StringIO())

    def test_rate_limit_and_auth_errors_are_clear(self):
        for status, message in ((429, "rate limit"), (401, "authentication"), (403, "authentication")):
            with self.subTest(status=status):
                session = Mock()
                session.get.return_value = Mock(status_code=status, headers={})
                with self.assertRaisesMessage(CommandError, message):
                    self.command.request_json(session, seed.API_URL, "secret", {"q": "plant"}, True)

    def test_network_error_does_not_expose_api_key(self):
        session = Mock()
        session.get.side_effect = seed.requests.ConnectionError("secret-key in URL")
        with self.assertRaises(CommandError) as caught:
            self.command.request_json(session, seed.API_URL, "secret-key", {"q": "plant"}, True)
        self.assertNotIn("secret-key", str(caught.exception))
