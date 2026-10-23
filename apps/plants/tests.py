from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Plant


class PlantCatalogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="catalog-user", password="safe-test-password"
        )
        cls.kangkung = Plant.objects.create(
            name="Kangkung",
            scientific_name="Ipomoea aquatica",
            category="sayur",
            supports_soil=True,
            supports_hydroponic=True,
            sunlight=["full_sun", "partial_shade"],
            space_needed="small",
        )
        cls.monstera = Plant.objects.create(
            name="Monstera",
            scientific_name="Monstera deliciosa",
            category="hias",
            supports_soil=True,
            supports_hydroponic=False,
            sunlight=["partial_shade", "shade"],
            space_needed="medium",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_catalog_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("plants:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_catalog_renders_plants_and_display_labels(self):
        response = self.client.get(reverse("plants:index"))
        self.assertContains(response, "Kangkung")
        self.assertContains(response, "Monstera")
        self.assertContains(response, "Tanah, Hidroponik")
        self.assertContains(response, "Matahari penuh, Teduh sebagian")

    def test_search_and_filters_can_be_combined(self):
        response = self.client.get(reverse("plants:index"), {
            "q": "monstera",
            "category": "hias",
            "medium": "soil",
            "sunlight": "shade",
            "space": "medium",
        })
        self.assertContains(response, "Monstera")
        self.assertNotContains(response, "Kangkung")

    def test_hydroponic_filter_excludes_unsupported_plants(self):
        response = self.client.get(reverse("plants:index"), {"medium": "hydroponic"})
        self.assertContains(response, "Kangkung")
        self.assertNotContains(response, "Monstera")

    def test_empty_result_has_a_clear_state(self):
        response = self.client.get(reverse("plants:index"), {"q": "tidak-ada"})
        self.assertContains(response, "Tanaman tidak ditemukan")

    def test_detail_requires_login_and_renders_catalog_facts(self):
        url = reverse("plants:detail", args=[self.kangkung.pk])
        response = self.client.get(url)
        self.assertContains(response, "Kebutuhan tanaman")
        self.assertContains(response, "Tanah, Hidroponik")

        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
