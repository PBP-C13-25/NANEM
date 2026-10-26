from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import PlantForm
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

    def test_catalog_marks_guides_unavailable_until_cultivation_route_exists(self):
        response = self.client.get(reverse("plants:index"))
        self.assertContains(response, "Panduan belum tersedia", count=2)
        self.assertNotContains(response, "Lihat detail")

    def test_standalone_plant_detail_route_does_not_exist(self):
        url = f"{reverse('plants:index')}{self.kangkung.pk}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class PlantAdminCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.staff = user_model.objects.create_user(
            username="plant-admin",
            password="safe-test-password",
            is_staff=True,
        )
        cls.regular_user = user_model.objects.create_user(
            username="regular-user",
            password="safe-test-password",
        )
        cls.plant = Plant.objects.create(
            name="Kangkung",
            scientific_name="Ipomoea aquatica",
            category="sayur",
            supports_soil=True,
            supports_hydroponic=True,
            sunlight=["full_sun"],
            space_needed="small",
        )

    def plant_payload(self, **overrides):
        payload = {
            "name": "Pakcoy",
            "scientific_name": "Brassica rapa subsp. chinensis",
            "description": "Sayuran daun.",
            "image_url": "https://example.com/pakcoy.jpg",
            "category": "sayur",
            "supports_soil": "on",
            "supports_hydroponic": "on",
            "sunlight": ["full_sun", "partial_shade"],
            "watering": "Average",
            "care_level": "Low",
            "drought_tolerant": "false",
            "indoor": "true",
            "space_needed": "small",
            "temp_min": "18",
            "temp_max": "30",
            "humidity_min": "50",
            "humidity_max": "80",
            "rainfall_min": "2",
            "rainfall_max": "4",
        }
        payload.update(overrides)
        return payload

    def test_manage_routes_reject_regular_users(self):
        self.client.force_login(self.regular_user)
        urls = [
            reverse("plants:manage"),
            reverse("plants:create"),
            reverse("plants:update", args=[self.plant.pk]),
            reverse("plants:delete", args=[self.plant.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_can_create_plant(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("plants:create"), self.plant_payload()
        )
        self.assertRedirects(response, reverse("plants:manage"), fetch_redirect_response=False)
        plant = Plant.objects.get(name="Pakcoy")
        self.assertEqual(plant.sunlight, ["full_sun", "partial_shade"])
        self.assertIs(plant.indoor, True)
        self.assertIs(plant.drought_tolerant, False)

    def test_staff_can_render_manage_list_and_forms(self):
        self.client.force_login(self.staff)

        manage_response = self.client.get(reverse("plants:manage"))
        self.assertEqual(manage_response.status_code, 200)
        self.assertContains(manage_response, "Kelola Tanaman")
        self.assertContains(manage_response, "Kangkung")

        create_response = self.client.get(reverse("plants:create"))
        self.assertEqual(create_response.status_code, 200)
        self.assertContains(create_response, "Tambah Tanaman")

        update_response = self.client.get(
            reverse("plants:update", args=[self.plant.pk])
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertContains(update_response, "Edit Kangkung")

        delete_response = self.client.get(
            reverse("plants:delete", args=[self.plant.pk])
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertContains(delete_response, "Yakin ingin menghapus")

    def test_manage_list_can_filter_by_search_category_and_status(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("plants:manage"),
            {"q": "kangkung", "category": "sayur", "status": "incomplete"},
        )
        self.assertContains(response, "Kangkung")
        self.assertContains(response, "Kurang")

    def test_manage_link_only_appears_for_staff(self):
        self.client.force_login(self.staff)
        staff_response = self.client.get(reverse("plants:index"))
        self.assertContains(staff_response, reverse("plants:manage"))

        self.client.force_login(self.regular_user)
        regular_response = self.client.get(reverse("plants:index"))
        self.assertNotContains(regular_response, reverse("plants:manage"))

    def test_staff_can_update_plant(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("plants:update", args=[self.plant.pk]),
            self.plant_payload(name="Kangkung Air"),
        )
        self.assertRedirects(response, reverse("plants:manage"), fetch_redirect_response=False)
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.name, "Kangkung Air")

    def test_staff_can_delete_plant(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("plants:delete", args=[self.plant.pk])
        )
        self.assertRedirects(response, reverse("plants:manage"), fetch_redirect_response=False)
        self.assertFalse(Plant.objects.filter(pk=self.plant.pk).exists())

    def test_form_rejects_reversed_range(self):
        form = PlantForm(data=self.plant_payload(temp_min="30", temp_max="20"))
        self.assertFalse(form.is_valid())
        self.assertIn("temp_max", form.errors)

    def test_form_requires_at_least_one_growing_medium(self):
        form = PlantForm(
            data=self.plant_payload(
                supports_soil="",
                supports_hydroponic="",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Pilih minimal satu media tanam", form.non_field_errors()[0])
