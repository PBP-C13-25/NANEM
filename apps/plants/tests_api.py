"""Tes kontrak API plants melalui autentikasi session bersama."""

from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Plant


class PlantReadAPITests(APITestCase):
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
