from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.plants.models import Plant

from .models import CultivationGuide


GUIDE_DATA = {
    "planting_steps": "Rendam benih\n\nTebar benih\nSiram setiap pagi",
    "planting_medium": "Tanah gembur",
    "water_needs": "Siram sekali sehari",
    "light_needs": "Matahari penuh",
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
            plant=self.bayam, **{**GUIDE_DATA, "planting_medium": "Rockwool khusus bayam"}
        )
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "Panduan Budidaya Kangkung")
        self.assertContains(response, "Tanah gembur")
        self.assertNotContains(response, "Rockwool khusus bayam")

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

    def test_cultivation_root_redirects_to_catalog(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cultivation:index"))
        self.assertRedirects(response, reverse("plants:index"))

    def test_navbar_has_no_cultivation_links(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("plants:index"))
        self.assertNotContains(response, "Kelola Panduan")
        self.assertNotContains(response, ">Panduan<")