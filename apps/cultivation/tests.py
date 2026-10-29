from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.plants.models import Plant

from .models import CultivationGuide


GUIDE_DATA = {
    "planting_steps": "Rendam benih\n\nTebar benih\nSiram setiap pagi",
    "watering_frequency": "Setiap pagi",
    "fertilizing": "Pupuk kompos setiap 2 minggu",
    "harvest_time": "30 hari setelah tanam",
}


class CultivationGuideTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="biasa", password="safe-test-password")
        cls.admin = user_model.objects.create_user(
            username="admin-test", password="safe-test-password", is_staff=True
        )
        cls.kangkung = Plant.objects.create(
            name="Kangkung", category="sayur", sunlight=["full_sun"], space_needed="small"
        )
        cls.bayam = Plant.objects.create(
            name="Bayam", category="sayur", sunlight=["full_sun"], space_needed="small"
        )

    def detail_url(self, plant):
        return reverse("cultivation:detail", args=[plant.pk])

    def create_guide(self, plant):
        return CultivationGuide.objects.create(plant=plant, **GUIDE_DATA)

    def test_detail_requires_login(self):
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_detail_unknown_plant_returns_404(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cultivation:detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_detail_shows_guide_of_that_plant_only(self):
        self.create_guide(self.kangkung)
        CultivationGuide.objects.create(
            plant=self.bayam, **{**GUIDE_DATA, "fertilizing": "Pupuk khusus bayam"}
        )
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "Panduan Budidaya Kangkung")
        self.assertContains(response, "Pupuk kompos setiap 2 minggu")
        self.assertNotContains(response, "Pupuk khusus bayam")

    def test_detail_takes_medium_water_and_light_from_catalog(self):
        self.kangkung.supports_soil = True
        self.kangkung.supports_hydroponic = True
        self.kangkung.watering = "Frequent"
        self.kangkung.save()
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "Tanah, Hidroponik")
        self.assertContains(response, "Sering")
        self.assertContains(response, "Matahari penuh")

    def test_form_has_no_fields_duplicated_from_catalog(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("cultivation:create", args=[self.kangkung.pk]))
        form = response.context["form"]
        self.assertEqual(
            list(form.fields),
            ["planting_steps", "watering_frequency", "fertilizing", "harvest_time"],
        )
        
    def test_detail_without_guide_shows_empty_state_without_admin_buttons(self):
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "Panduan belum tersedia")
        self.assertNotContains(response, "Tambah Panduan")

    def test_admin_sees_add_button_when_guide_missing(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "Tambah Panduan")

    def test_regular_user_does_not_see_admin_actions(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertNotContains(response, "Edit panduan")
        self.assertNotContains(response, "Hapus panduan")

    def test_step_list_ignores_blank_lines(self):
        guide = self.create_guide(self.kangkung)
        self.assertEqual(guide.step_list, ["Rendam benih", "Tebar benih", "Siram setiap pagi"])

    def test_regular_user_cannot_create_update_or_delete(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        for name, method in (("create", "get"), ("update", "get"), ("delete", "post")):
            url = reverse(f"cultivation:{name}", args=[self.kangkung.pk])
            response = getattr(self.client, method)(url)
            self.assertEqual(response.status_code, 403, name)

    def test_guest_is_redirected_from_admin_pages(self):
        response = self.client.get(reverse("cultivation:create", args=[self.kangkung.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_admin_can_create_guide(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("cultivation:create", args=[self.kangkung.pk]), GUIDE_DATA
        )
        self.assertRedirects(response, self.detail_url(self.kangkung))
        guide = CultivationGuide.objects.get(plant=self.kangkung)
        self.assertEqual(guide.step_list, ["Rendam benih", "Tebar benih", "Siram setiap pagi"])

    def test_create_rejects_empty_steps(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("cultivation:create", args=[self.kangkung.pk]),
            {**GUIDE_DATA, "planting_steps": "  \n  "},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CultivationGuide.objects.exists())

    def test_create_redirects_to_edit_when_guide_exists(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("cultivation:create", args=[self.kangkung.pk]))
        self.assertRedirects(
            response,
            reverse("cultivation:update", args=[self.kangkung.pk]),
            fetch_redirect_response=False,
        )

    def test_admin_can_update_guide(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("cultivation:update", args=[self.kangkung.pk]),
            {**GUIDE_DATA, "harvest_time": "45 hari"},
        )
        self.assertRedirects(response, self.detail_url(self.kangkung))
        self.assertEqual(CultivationGuide.objects.get(plant=self.kangkung).harvest_time, "45 hari")

    def test_update_without_guide_returns_404(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("cultivation:update", args=[self.kangkung.pk]))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_delete_guide(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("cultivation:delete", args=[self.kangkung.pk]))
        self.assertRedirects(response, self.detail_url(self.kangkung))
        self.assertFalse(CultivationGuide.objects.exists())

    def test_delete_rejects_get(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("cultivation:delete", args=[self.kangkung.pk]))
        self.assertEqual(response.status_code, 405)

    def test_deleting_plant_cascades_to_guide(self):
        self.create_guide(self.kangkung)
        self.kangkung.delete()
        self.assertFalse(CultivationGuide.objects.exists())

    def test_detail_shows_watering_frequency(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "Frekuensi Penyiraman")
        self.assertContains(response, "Setiap pagi")

    def test_list_requires_login(self):
        response = self.client.get(reverse("cultivation:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_list_shows_only_plants_with_guides(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        response = self.client.get(reverse("cultivation:index"))
        self.assertContains(response, "Kangkung")
        self.assertNotContains(response, "Bayam")
        self.assertContains(response, self.detail_url(self.kangkung))

    def test_list_empty_state(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cultivation:index"))
        self.assertContains(response, "Panduan tidak ditemukan")

    def test_list_filters_by_search_category_and_medium(self):
        self.create_guide(self.kangkung)
        monstera = Plant.objects.create(
            name="Monstera", category="hias", supports_soil=True,
            supports_hydroponic=False, space_needed="medium",
        )
        self.create_guide(monstera)
        self.kangkung.supports_hydroponic = True
        self.kangkung.save()
        self.client.force_login(self.user)
        url = reverse("cultivation:index")

        response = self.client.get(url, {"q": "monst"})
        self.assertContains(response, "Monstera")
        self.assertNotContains(response, "Kangkung")

        response = self.client.get(url, {"category": "sayur"})
        self.assertContains(response, "Kangkung")
        self.assertNotContains(response, "Monstera")

        response = self.client.get(url, {"medium": "hydroponic"})
        self.assertContains(response, "Kangkung")
        self.assertNotContains(response, "Monstera")

    def test_list_invalid_filters_fall_back_to_defaults(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("cultivation:index"),
            {"category": "xxx", "medium": "xxx", "sort": "xxx"},
        )
        self.assertEqual(response.context["filters"]["category"], "")
        self.assertEqual(response.context["filters"]["medium"], "")
        self.assertEqual(response.context["filters"]["sort"], "name")

    def test_list_sort_name_desc(self):
        self.create_guide(self.kangkung)
        self.create_guide(self.bayam)
        self.client.force_login(self.user)
        response = self.client.get(reverse("cultivation:index"), {"sort": "name_desc"})
        names = [guide.plant.name for guide in response.context["guides"]]
        self.assertEqual(names, ["Kangkung", "Bayam"])

    def test_list_pagination_keeps_filters(self):
        for index in range(7):
            plant = Plant.objects.create(
                name=f"Sayur {index}", category="sayur", space_needed="small"
            )
            self.create_guide(plant)
        self.client.force_login(self.user)
        response = self.client.get(reverse("cultivation:index"), {"category": "sayur"})
        self.assertTrue(response.context["is_paginated"])
        self.assertContains(response, "category=sayur&amp;page=2")

    def test_catalog_links_to_guide_list(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("plants:index"))
        self.assertContains(response, reverse("cultivation:index"))

    def test_navbar_has_no_cultivation_links(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("plants:index"))
        self.assertNotContains(response, "Kelola Panduan")
        self.assertNotContains(response, ">Panduan<")