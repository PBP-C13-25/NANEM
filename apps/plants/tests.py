from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import resolve, reverse

from .forms import PlantForm
from .models import Plant
from .views import PlantManageListView


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

    def test_manage_routes_redirect_guests_to_login(self):
        urls = [
            reverse("plants:manage"),
            reverse("plants:create"),
            reverse("plants:update", args=[self.plant.pk]),
            reverse("plants:delete", args=[self.plant.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:login"), response.url)

    def test_regular_user_cannot_post_crud_operations(self):
        self.client.force_login(self.regular_user)
        requests = [
            (reverse("plants:create"), self.plant_payload()),
            (
                reverse("plants:update", args=[self.plant.pk]),
                self.plant_payload(name="Perubahan tidak sah"),
            ),
            (reverse("plants:delete", args=[self.plant.pk]), {}),
        ]
        for url, payload in requests:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, payload).status_code, 403)

        self.plant.refresh_from_db()
        self.assertEqual(self.plant.name, "Kangkung")
        self.assertTrue(Plant.objects.filter(pk=self.plant.pk).exists())

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

    def test_invalid_create_does_not_change_database(self):
        self.client.force_login(self.staff)
        initial_count = Plant.objects.count()
        response = self.client.post(
            reverse("plants:create"),
            self.plant_payload(temp_min="35", temp_max="20"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Plant.objects.count(), initial_count)
        self.assertContains(response, "maksimum tidak boleh lebih kecil")

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

    def test_form_and_delete_pages_render_final_ui_content(self):
        self.client.force_login(self.staff)
        form_response = self.client.get(
            reverse("plants:update", args=[self.plant.pk])
        )
        for heading in (
            "Identitas tanaman",
            "Media dan lokasi",
            "Perawatan",
            "Kondisi lingkungan",
            "Deskripsi dan gambar",
        ):
            self.assertContains(form_response, heading)
        self.assertContains(form_response, "plant_manage.css")
        self.assertNotContains(form_response, 'href="#"')

        delete_response = self.client.get(
            reverse("plants:delete", args=[self.plant.pk])
        )
        self.assertContains(delete_response, "hilang dari katalog")
        self.assertContains(delete_response, "hasil rekomendasi")
        self.assertNotContains(delete_response, 'href="#"')

    def test_manage_list_can_filter_by_search_category_and_status(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("plants:manage"),
            {"q": "kangkung", "category": "sayur", "status": "incomplete"},
        )
        self.assertContains(response, "Kangkung")
        self.assertContains(response, "Kurang")

    def test_manage_list_can_filter_by_growing_medium(self):
        Plant.objects.create(
            name="Mangga",
            category="buah",
            supports_soil=True,
            supports_hydroponic=False,
            space_needed="large",
        )
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("plants:manage"), {"medium": "hydroponic"}
        )
        self.assertContains(response, "Kangkung")
        self.assertNotContains(response, "Mangga")

    def test_manage_list_renders_final_table_elements(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("plants:manage"))
        self.assertContains(response, "plant-admin__thumbnail")
        self.assertContains(response, "Media &amp; cahaya")
        self.assertContains(response, "Perawatan")
        self.assertContains(response, reverse("plants:create"))
        self.assertContains(response, reverse("plants:update", args=[self.plant.pk]))
        self.assertContains(response, reverse("plants:delete", args=[self.plant.pk]))
        self.assertNotContains(response, "plant-admin__badge")
        self.assertNotContains(response, "plant-admin__status--")
        self.assertNotContains(response, 'href="#"')

    def test_manage_list_renders_empty_state(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("plants:manage"), {"q": "tidak-ada"})
        self.assertContains(response, "Tanaman tidak ditemukan")
        self.assertContains(response, "Reset filter")

    def test_manage_list_sorting_is_stable(self):
        Plant.objects.create(
            name="Bayam",
            category="sayur",
            supports_soil=True,
            space_needed="small",
        )
        Plant.objects.create(
            name="Tomat",
            category="sayur",
            supports_soil=True,
            space_needed="small",
        )
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("plants:manage"), {"sort": "name_desc"}
        )
        names = [plant.name for plant in response.context["plants"]]
        self.assertEqual(names, ["Tomat", "Kangkung", "Bayam"])

    def test_invalid_management_filters_fall_back_to_defaults(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("plants:manage"),
            {
                "category": "invalid",
                "medium": "invalid",
                "status": "invalid",
                "sort": "invalid",
            },
        )
        self.assertEqual(response.context["filters"]["category"], "")
        self.assertEqual(response.context["filters"]["medium"], "")
        self.assertEqual(response.context["filters"]["status"], "")
        self.assertEqual(response.context["filters"]["sort"], "name")

    def test_pagination_preserves_management_query(self):
        for index in range(11):
            Plant.objects.create(
                name=f"Plant {index:02d}",
                category="sayur",
                supports_soil=True,
                space_needed="small",
            )
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("plants:manage"),
            {
                "q": "Plant",
                "category": "sayur",
                "medium": "soil",
                "status": "incomplete",
                "sort": "name_desc",
            },
        )
        self.assertTrue(response.context["is_paginated"])
        content = response.content.decode()
        self.assertIn("q=Plant", content)
        self.assertIn("category=sayur", content)
        self.assertIn("medium=soil", content)
        self.assertIn("status=incomplete", content)
        self.assertIn("sort=name_desc", content)
        self.assertIn("page=2", content)

    def test_manage_link_only_appears_for_staff(self):
        self.client.force_login(self.staff)
        staff_response = self.client.get(reverse("plants:index"))
        self.assertContains(staff_response, reverse("plants:manage"))

        self.client.force_login(self.regular_user)
        regular_response = self.client.get(reverse("plants:index"))
        self.assertNotContains(regular_response, reverse("plants:manage"))

    def test_manage_route_and_navigation_active_state(self):
        match = resolve(reverse("plants:manage"))
        self.assertIs(match.func.view_class, PlantManageListView)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("plants:manage"))
        self.assertContains(
            response,
            f'href="{reverse("plants:manage")}" '
            'class="dropdown__item dropdown__item--sub is-active"',
        )

    def test_staff_can_update_plant(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("plants:update", args=[self.plant.pk]),
            self.plant_payload(name="Kangkung Air"),
        )
        self.assertRedirects(response, reverse("plants:manage"), fetch_redirect_response=False)
        self.plant.refresh_from_db()
        self.assertEqual(self.plant.name, "Kangkung Air")

    def test_form_rejects_duplicate_name_ignoring_case(self):
        form = PlantForm(data=self.plant_payload(name="  KANGKUNG  "))

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("sudah digunakan", form.errors["name"][0])

    def test_update_can_keep_its_existing_name(self):
        form = PlantForm(
            data=self.plant_payload(name="  Kangkung  "),
            instance=self.plant,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Kangkung")

    def test_database_rejects_duplicate_name_ignoring_case(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Plant.objects.create(
                name="KANGKUNG",
                category="sayur",
                supports_soil=True,
                space_needed="small",
            )

    def test_staff_can_delete_plant(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("plants:delete", args=[self.plant.pk])
        )
        self.assertRedirects(response, reverse("plants:manage"), fetch_redirect_response=False)
        self.assertFalse(Plant.objects.filter(pk=self.plant.pk).exists())

    def test_delete_confirmation_does_not_delete_plant(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("plants:delete", args=[self.plant.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Plant.objects.filter(pk=self.plant.pk).exists())

    def test_missing_plant_returns_404_for_staff(self):
        self.client.force_login(self.staff)
        missing_pk = self.plant.pk + 999
        for route_name in ("update", "delete"):
            with self.subTest(route_name=route_name):
                response = self.client.get(
                    reverse(f"plants:{route_name}", args=[missing_pk])
                )
                self.assertEqual(response.status_code, 404)

    def test_crud_success_messages_are_rendered(self):
        self.client.force_login(self.staff)
        create_response = self.client.post(
            reverse("plants:create"), self.plant_payload(), follow=True
        )
        self.assertContains(create_response, "Pakcoy berhasil ditambahkan")
        pakcoy = Plant.objects.get(name="Pakcoy")

        update_response = self.client.post(
            reverse("plants:update", args=[pakcoy.pk]),
            self.plant_payload(name="Pakcoy Hijau"),
            follow=True,
        )
        self.assertContains(update_response, "Pakcoy Hijau berhasil diperbarui")

        delete_response = self.client.post(
            reverse("plants:delete", args=[pakcoy.pk]), follow=True
        )
        self.assertContains(delete_response, "Pakcoy Hijau berhasil dihapus")

    def test_form_rejects_reversed_range(self):
        form = PlantForm(data=self.plant_payload(temp_min="30", temp_max="20"))
        self.assertFalse(form.is_valid())
        self.assertIn("temp_max", form.errors)

    def test_form_rejects_humidity_outside_percentage_range(self):
        for field_name, value in (("humidity_min", "-1"), ("humidity_max", "101")):
            with self.subTest(field_name=field_name, value=value):
                form = PlantForm(data=self.plant_payload(**{field_name: value}))
                self.assertFalse(form.is_valid())
                self.assertIn(field_name, form.errors)

    def test_form_rejects_negative_rainfall(self):
        form = PlantForm(data=self.plant_payload(rainfall_min="-0.1"))

        self.assertFalse(form.is_valid())
        self.assertIn("rainfall_min", form.errors)
        self.assertIn("tidak boleh bernilai negatif", form.errors["rainfall_min"][0])

    def test_form_requires_at_least_one_growing_medium(self):
        form = PlantForm(
            data=self.plant_payload(
                supports_soil="",
                supports_hydroponic="",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Pilih minimal satu media tanam", form.non_field_errors()[0])
