"""Tes kontrak API plants melalui autentikasi session bersama."""

from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.cultivation.models import CultivationGuide

from .models import Plant


class PlantAPITestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="catalog-reader")
        cls.staff = get_user_model().objects.create_user(
            username="catalog-staff", is_staff=True
        )
        cls.kangkung = Plant.objects.create(
            name="Kangkung", scientific_name="Ipomoea aquatica", category="sayur",
            description="Sayuran daun.", image_url="https://example.com/kangkung.jpg",
            supports_soil=True, supports_hydroponic=True,
            sunlight=["full_sun", "partial_shade"], space_needed="small",
        )
        cls.monstera = Plant.objects.create(
            name="Monstera", scientific_name="Monstera deliciosa", category="hias",
            supports_soil=True, supports_hydroponic=False,
            sunlight=["partial_shade", "shade"], space_needed="medium",
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.list_url = reverse("plants_api:list")
        self.detail_url = reverse("plants_api:detail", args=[self.kangkung.pk])


class PlantReadAPITests(PlantAPITestBase):
    def test_guest_receives_json_401_for_list_and_detail(self):
        self.client.logout()
        for url in (self.list_url, self.detail_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 401)
                self.assertIn("detail", response.json())

    def test_inactive_session_cannot_read_plants(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(self.list_url).status_code, 401)

    def test_user_can_read_paginated_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertIsNone(response.data["next"])
        self.assertEqual(
            [plant["name"] for plant in response.data["results"]],
            ["Kangkung", "Monstera"],
        )

    def test_detail_includes_catalog_content_and_preserves_unknown_values(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.kangkung.pk)
        self.assertEqual(response.data["description"], self.kangkung.description)
        self.assertEqual(response.data["image_url"], self.kangkung.image_url)
        self.assertEqual(response.data["sunlight"], ["full_sun", "partial_shade"])
        for field in ("indoor", "drought_tolerant", "temp_min", "humidity_min"):
            self.assertIsNone(response.data[field])

    def test_staff_can_also_read_plants(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url).status_code, 200)

    def test_search_matches_name_and_scientific_name_ignoring_case(self):
        for query in ("KANGKUNG", "aquatica"):
            with self.subTest(query=query):
                response = self.client.get(self.list_url, {"q": query})
                self.assertEqual(response.data["count"], 1)
                self.assertEqual(response.data["results"][0]["id"], self.kangkung.pk)

    def test_filters_can_be_combined(self):
        response = self.client.get(self.list_url, {
            "q": "monstera", "category": "hias", "medium": "soil",
            "sunlight": "shade", "space": "medium",
        })
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.monstera.pk)

    def test_hydroponic_filter_excludes_unsupported_plants(self):
        response = self.client.get(self.list_url, {"medium": "hydroponic"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.kangkung.pk)

    def test_sunlight_matches_any_supported_option(self):
        response = self.client.get(self.list_url, {"sunlight": "partial_shade"})
        self.assertEqual(response.data["count"], 2)

    def test_invalid_filters_fall_back_to_unfiltered_name_order(self):
        response = self.client.get(self.list_url, {
            "category": "invalid", "medium": "invalid", "space": "invalid",
            "sunlight": "invalid", "sort": "invalid",
        })
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["name"], "Kangkung")

    def test_sorting(self):
        for sort, first in (
            ("name_desc", "Monstera"), ("category", "Monstera"),
            ("updated", "Monstera"),
        ):
            with self.subTest(sort=sort):
                response = self.client.get(self.list_url, {"sort": sort})
                self.assertEqual(response.data["results"][0]["name"], first)

    def test_pagination_keeps_search_and_filter_parameters(self):
        Plant.objects.bulk_create([
            Plant(name=f"Tanaman {i}", category="sayur", space_needed="small")
            for i in range(8)
        ])
        response = self.client.get(self.list_url, {"q": "Tanaman", "category": "sayur"})
        self.assertEqual(response.data["count"], 8)
        self.assertEqual(len(response.data["results"]), 6)
        query = parse_qs(urlparse(response.data["next"]).query)
        self.assertEqual(query, {"q": ["Tanaman"], "category": ["sayur"], "page": ["2"]})
        next_page = self.client.get(self.list_url, {"q": "Tanaman", "category": "sayur", "page": 2})
        self.assertEqual(len(next_page.data["results"]), 2)

    def test_empty_results(self):
        response = self.client.get(self.list_url, {"q": "tidak-ada"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_missing_plant_and_invalid_page_return_404(self):
        self.assertEqual(
            self.client.get(reverse("plants_api:detail", args=[999999])).status_code, 404
        )
        self.assertEqual(self.client.get(self.list_url, {"page": 999}).status_code, 404)

    def test_detail_includes_labels_and_guide_flag(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.data["category_label"], self.kangkung.get_category_display())
        self.assertEqual(response.data["space_needed_label"], self.kangkung.get_space_needed_display())
        self.assertFalse(response.data["has_guide"])

        CultivationGuide.objects.create(plant=self.kangkung, planting_steps="Siapkan media tanam.")
        response = self.client.get(self.detail_url)
        self.assertTrue(response.data["has_guide"])
        

class PlantWriteAPITests(PlantAPITestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def payload(self, **overrides):
        data = {
            "name": "Pakcoy", "scientific_name": "Brassica rapa subsp. chinensis",
            "description": "Sayuran daun.", "image_url": "https://example.com/pakcoy.jpg",
            "category": "sayur", "space_needed": "small",
            "supports_soil": True, "supports_hydroponic": True,
            "sunlight": ["full_sun", "partial_shade"], "watering": "Average",
            "care_level": "Low", "indoor": True, "drought_tolerant": False,
            "temp_min": 18, "temp_max": 30, "humidity_min": 50, "humidity_max": 80,
            "rainfall_min": 2, "rainfall_max": 4,
        }
        data.update(overrides)
        return data

    def test_guest_cannot_create_update_or_delete(self):
        self.client.logout()
        for method, url in (
            ("post", self.list_url), ("patch", self.detail_url),
            ("put", self.detail_url), ("delete", self.detail_url),
        ):
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, self.payload(), format="json")
                self.assertEqual(response.status_code, 401)
        self.assertEqual(Plant.objects.count(), 2)

    def test_regular_user_cannot_create_update_or_delete(self):
        self.client.force_login(self.user)
        for method, url in (
            ("post", self.list_url), ("patch", self.detail_url),
            ("put", self.detail_url), ("delete", self.detail_url),
        ):
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, self.payload(), format="json")
                self.assertEqual(response.status_code, 403)
        self.assertEqual(Plant.objects.count(), 2)
        self.kangkung.refresh_from_db()
        self.assertEqual(self.kangkung.name, "Kangkung")

    def test_inactive_staff_cannot_write(self):
        self.staff.is_active = False
        self.staff.save(update_fields=["is_active"])
        response = self.client.post(self.list_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Plant.objects.count(), 2)

    def test_staff_can_create_with_json_booleans_and_sunlight_list(self):
        response = self.client.post(self.list_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        plant = Plant.objects.get(pk=response.data["id"])
        self.assertEqual(plant.sunlight, ["full_sun", "partial_shade"])
        self.assertIs(plant.indoor, True)
        self.assertIs(plant.drought_tolerant, False)
        self.assertIs(plant.supports_hydroponic, True)
        self.assertEqual(plant.humidity_min, 50)
        # CRUD web dan katalog membaca baris yang sama.
        self.assertContains(self.client.get(reverse("plants:manage")), "Pakcoy")
        self.assertContains(self.client.get(reverse("plants:index")), "Pakcoy")

    def test_create_with_minimal_fields_uses_model_defaults(self):
        response = self.client.post(self.list_url, {
            "name": "Mint", "category": "herbal", "space_needed": "small",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIs(response.data["supports_soil"], True)
        self.assertEqual(response.data["sunlight"], [])
        self.assertIsNone(response.data["indoor"])

    def test_invalid_inputs_return_field_errors_without_creating_records(self):
        cases = (
            ({"name": "kangkung"}, "name"),
            ({"name": "   "}, "name"),
            ({"category": "invalid"}, "category"),
            ({"space_needed": "invalid"}, "space_needed"),
            ({"temp_min": 35, "temp_max": 20}, "temp_max"),
            ({"humidity_min": -1}, "humidity_min"),
            ({"humidity_max": 101}, "humidity_max"),
            ({"humidity_min": 80, "humidity_max": 50}, "humidity_max"),
            ({"rainfall_min": -1}, "rainfall_min"),
            ({"rainfall_min": 5, "rainfall_max": 2}, "rainfall_max"),
            ({"temp_min": "invalid"}, "temp_min"),
            ({"image_url": "invalid"}, "image_url"),
            ({"sunlight": ["invalid"]}, "sunlight"),
            ({"sunlight": "full_sun"}, "sunlight"),
            ({"care_level": "invalid"}, "care_level"),
            ({"watering": "invalid"}, "watering"),
            ({"supports_soil": False, "supports_hydroponic": False}, "__all__"),
        )
        for overrides, field in cases:
            with self.subTest(overrides=overrides):
                response = self.client.post(self.list_url, self.payload(**overrides), format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn(field, response.data["errors"])
                self.assertEqual(Plant.objects.count(), 2)

    def test_required_fields_are_reported(self):
        response = self.client.post(self.list_url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        for field in ("name", "category", "space_needed"):
            self.assertIn(field, response.data["errors"])

    def test_patch_preserves_unsent_values_and_accepts_existing_name(self):
        Plant.objects.filter(pk=self.kangkung.pk).update(
            temp_min=18, temp_max=30, humidity_min=50, humidity_max=80, indoor=True
        )
        response = self.client.patch(self.detail_url, {
            "name": "Kangkung", "description": "Deskripsi diperbarui.",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.kangkung.refresh_from_db()
        self.assertEqual(self.kangkung.description, "Deskripsi diperbarui.")
        self.assertEqual(self.kangkung.sunlight, ["full_sun", "partial_shade"])
        self.assertEqual(self.kangkung.humidity_min, 50)
        self.assertEqual(self.kangkung.humidity_max, 80)
        self.assertEqual(self.kangkung.temp_min, 18)
        self.assertIs(self.kangkung.indoor, True)

    def test_patch_validates_against_existing_range_without_saving(self):
        Plant.objects.filter(pk=self.kangkung.pk).update(temp_min=20, temp_max=30)
        response = self.client.patch(self.detail_url, {"temp_max": 10}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("temp_max", response.data["errors"])
        self.kangkung.refresh_from_db()
        self.assertEqual(self.kangkung.temp_max, 30)

    def test_nullable_values_can_be_cleared_and_false_is_preserved(self):
        Plant.objects.filter(pk=self.kangkung.pk).update(indoor=True, temp_min=20)
        response = self.client.patch(self.detail_url, {
            "indoor": None, "drought_tolerant": False, "temp_min": None,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.kangkung.refresh_from_db()
        self.assertIsNone(self.kangkung.indoor)
        self.assertIsNone(self.kangkung.temp_min)
        self.assertIs(self.kangkung.drought_tolerant, False)

    def test_read_only_source_id_and_timestamps_cannot_be_changed(self):
        self.kangkung.perenual_id = 12
        self.kangkung.save(update_fields=["perenual_id"])
        created_at = self.kangkung.created_at
        response = self.client.patch(self.detail_url, {
            "id": 999, "perenual_id": 999,
            "created_at": "2000-01-01T00:00:00Z", "updated_at": "2000-01-01T00:00:00Z",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.kangkung.refresh_from_db()
        self.assertEqual(response.data["id"], self.kangkung.pk)
        self.assertEqual(self.kangkung.perenual_id, 12)
        self.assertEqual(self.kangkung.created_at, created_at)
        self.assertEqual(self.kangkung.updated_at.year, created_at.year)

    def test_staff_can_replace_editable_data_with_put(self):
        response = self.client.put(self.detail_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.kangkung.refresh_from_db()
        self.assertEqual(self.kangkung.name, "Pakcoy")
        self.assertEqual(self.kangkung.temp_max, 30)

    def test_staff_can_delete_and_related_guide_follows_existing_cascade(self):
        guide = CultivationGuide.objects.create(
            plant=self.kangkung, planting_steps="Siapkan media tanam."
        )
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Plant.objects.filter(pk=self.kangkung.pk).exists())
        self.assertFalse(CultivationGuide.objects.filter(pk=guide.pk).exists())

    def test_update_and_delete_missing_plant_return_404(self):
        url = reverse("plants_api:detail", args=[999999])
        self.assertEqual(self.client.patch(url, {"name": "Baru"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_api_uses_real_login_session_and_logout_revokes_access(self):
        self.staff.set_password("KebunHijau#2026")
        self.staff.save(update_fields=["password"])
        self.client.logout()
        response = self.client.post(reverse("accounts_api:login"), {
            "username": self.staff.username, "password": "KebunHijau#2026",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(self.list_url, self.payload(), format="json").status_code, 201)
        self.client.post(reverse("accounts_api:logout"), {}, format="json")
        self.assertEqual(self.client.get(self.list_url).status_code, 401)
