from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.plants.models import Plant

from .models import CultivationGuide


GUIDE_DATA = {
    "planting_steps": "Rendam benih\n\nTebar benih\nSiram setiap pagi",
    "watering_frequency": "daily",
    "watering_note": "Siram setiap pagi",
    "fertilizing_frequency": "biweekly",
    "fertilizing_note": "Pupuk kompos setiap 2 minggu",
    "is_harvestable": True,
    "harvest_days_min": 30,
    "harvest_days_max": 40,
    "harvest_note": "Panen saat daun sudah lebat",
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
            plant=self.bayam, **{**GUIDE_DATA, "fertilizing_note": "Pupuk khusus bayam"}
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
        self.assertNotContains(response, "<h3>Media Tanam</h3>")

    def test_form_has_no_fields_duplicated_from_catalog(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("cultivation:create", args=[self.kangkung.pk]))
        form = response.context["form"]
        self.assertEqual(
            list(form.fields),
            [
                "planting_steps",
                "watering_frequency",
                "watering_note",
                "fertilizing_frequency",
                "fertilizing_note",
                "is_harvestable",
                "harvest_days_min",
                "harvest_days_max",
                "harvest_note",
            ],
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
            {**GUIDE_DATA, "harvest_days_min": 45, "harvest_days_max": 50},
        )
        self.assertRedirects(response, self.detail_url(self.kangkung))
        self.assertEqual(CultivationGuide.objects.get(plant=self.kangkung).harvest_days_min, 45)

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
        self.assertContains(response, "Setiap hari")
        self.assertContains(response, "Siram setiap pagi")

    def test_harvest_label_variants(self):
        guide = self.create_guide(self.kangkung)
        self.assertEqual(guide.harvest_label, "30-40 hari setelah tanam")
        guide.harvest_days_max = 30
        self.assertEqual(guide.harvest_label, "Sekitar 30 hari setelah tanam")
        guide.harvest_days_min, guide.harvest_days_max = 365, 1095
        self.assertEqual(guide.harvest_label, "365 hari-3 tahun setelah tanam")
        guide.harvest_days_min = guide.harvest_days_max = None
        self.assertEqual(guide.harvest_label, "Lihat catatan panen")
        guide.is_harvestable = False
        self.assertEqual(guide.harvest_label, "Tidak ada waktu panen")

    def test_non_harvestable_form_clears_days(self):
        self.client.force_login(self.admin)
        data = {**GUIDE_DATA}
        data.pop("is_harvestable")
        response = self.client.post(reverse("cultivation:create", args=[self.kangkung.pk]), data)
        self.assertRedirects(response, self.detail_url(self.kangkung))
        guide = CultivationGuide.objects.get(plant=self.kangkung)
        self.assertFalse(guide.is_harvestable)
        self.assertIsNone(guide.harvest_days_min)
        self.assertIsNone(guide.harvest_days_max)

    def test_harvestable_requires_days_or_note(self):
        self.client.force_login(self.admin)
        data = {**GUIDE_DATA, "harvest_days_min": "", "harvest_days_max": "", "harvest_note": ""}
        response = self.client.post(reverse("cultivation:create", args=[self.kangkung.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CultivationGuide.objects.exists())

    def test_harvest_min_cannot_exceed_max(self):
        self.client.force_login(self.admin)
        data = {**GUIDE_DATA, "harvest_days_min": 50, "harvest_days_max": 40}
        response = self.client.post(reverse("cultivation:create", args=[self.kangkung.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CultivationGuide.objects.exists())

    def test_invalid_frequency_choice_is_rejected(self):
        self.client.force_login(self.admin)
        data = {**GUIDE_DATA, "watering_frequency": "kapan-saja"}
        response = self.client.post(reverse("cultivation:create", args=[self.kangkung.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CultivationGuide.objects.exists())

    def test_detail_shows_harvest_and_fertilizing_details(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "30-40 hari setelah tanam")
        self.assertContains(response, "Dua minggu sekali")
        self.assertContains(response, "Pupuk kompos setiap 2 minggu")

    def test_detail_does_not_display_sources(self):
        guide = self.create_guide(self.kangkung)
        guide.sources = [{"title": "Sumber Uji", "url": "https://example.org/uji"}]
        guide.save()
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertNotContains(response, "Sumber Uji")
        self.assertNotContains(response, "Sumber</h2>")

    def test_detail_shows_all_catalog_facts_and_description_without_guide(self):
        plant = Plant.objects.create(
            name="Aglaonema", scientific_name="Aglaonema spp.", category="hias",
            description="Tanaman hias berdaun lebar.", supports_soil=True,
            supports_hydroponic=False, sunlight=["partial_shade", "shade"],
            watering="Average", care_level="Low", drought_tolerant=False,
            space_needed="small", temp_min=18, temp_max=30.5,
            humidity_min=50, humidity_max=80, rainfall_min=2, rainfall_max=5,
        )
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(plant))
        for text in (
            "Tanaman hias berdaun lebar.", "Aglaonema spp.", "Tanah", "Teduh sebagian, Teduh",
            "Small", "Sedang", "Mudah", "Tidak", "18-30,5 °C", "50-80 %", "2-5 mm/hari",
        ):
            self.assertContains(response, text)
        for label in (
            "Media", "Cahaya", "Ruang", "Kebutuhan air", "Tingkat perawatan",
            "Tahan kekeringan", "Suhu", "Kelembapan", "Curah hujan",
        ):
            self.assertContains(response, f"<dt>{label}</dt>")

    def test_detail_facts_handle_missing_values(self):
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "Belum diketahui")
        self.assertContains(response, "Belum ditentukan")

    def test_detail_shows_catalog_facts_once_before_guide_sections(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        content = self.client.get(self.detail_url(self.kangkung)).content.decode()
        self.assertNotIn("<h3>Media Tanam</h3>", content)
        self.assertNotIn("<h3>Kebutuhan Air</h3>", content)
        self.assertNotIn("<h3>Kebutuhan Cahaya</h3>", content)
        self.assertEqual(content.count("<dt>Media</dt>"), 1)
        self.assertLess(content.index("<dt>Curah hujan</dt>"), content.index("Cara Menanam"))

    def test_admin_actions_sit_between_facts_and_guide_sections(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        content = self.client.get(self.detail_url(self.kangkung)).content.decode()
        self.assertLess(content.index("<dt>Curah hujan</dt>"), content.index("Edit panduan"))
        self.assertLess(content.index("Edit panduan"), content.index("Cara Menanam"))

    def test_there_is_no_public_guide_list_page(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/cultivation/").status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/cultivation/").status_code, 404)

    def test_catalog_links_only_to_individual_guides(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("plants:index"))
        self.assertContains(response, self.detail_url(self.kangkung))
        self.assertNotContains(response, "Lihat semua panduan")

    def test_detail_has_no_link_to_all_guides(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url(self.kangkung))
        self.assertContains(response, "Kembali ke katalog")
        self.assertNotContains(response, "Semua panduan")

    def test_navbar_shows_kelola_panduan_only_for_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("plants:index"))
        self.assertContains(response, reverse("cultivation:kelola_panduan"))
        self.assertNotContains(response, ">Panduan<")
        self.client.force_login(self.user)
        response = self.client.get(reverse("plants:index"))
        self.assertNotContains(response, reverse("cultivation:kelola_panduan"))

    def test_kelola_requires_admin(self):
        url = reverse("cultivation:kelola_panduan")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_kelola_lists_all_plants_with_status_and_actions(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("cultivation:kelola_panduan"))
        self.assertContains(response, "Kangkung")
        self.assertContains(response, "Bayam")
        self.assertContains(response, reverse("cultivation:update", args=[self.kangkung.pk]))
        self.assertContains(response, reverse("cultivation:create", args=[self.bayam.pk]))
        self.assertEqual(response.context["with_guide_count"], 1)
        self.assertEqual(response.context["without_guide_count"], 1)

    def test_kelola_filters_by_status_search_and_category(self):
        self.create_guide(self.kangkung)
        self.client.force_login(self.admin)
        url = reverse("cultivation:kelola_panduan")

        response = self.client.get(url, {"status": "ada"})
        self.assertContains(response, "Kangkung")
        self.assertNotContains(response, "Bayam")

        response = self.client.get(url, {"status": "belum"})
        self.assertContains(response, "Bayam")
        self.assertNotContains(response, "Kangkung")

        response = self.client.get(url, {"q": "baya"})
        self.assertNotContains(response, "Kangkung")

        response = self.client.get(url, {"category": "xxx", "status": "xxx"})
        self.assertEqual(response.context["filters"]["category"], "")
        self.assertEqual(response.context["filters"]["status"], "")

class SeedGuidesCommandTests(TestCase):
    def run_seed(self, entries, *args):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock

        from django.core.management import call_command

        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "guides_test.json").write_text(json.dumps(entries), encoding="utf-8")
            with mock.patch("apps.cultivation.management.commands.seed_guides.DATA_DIR", Path(folder)):
                call_command("seed_guides", *args, stdout=mock.MagicMock(), stderr=mock.MagicMock())

    def entry(self, **overrides):
        data = {
            "plant": "Kangkung",
            "planting_steps": ["Tebar benih", "Siram"],
            "watering_frequency": "daily",
            "fertilizing_frequency": "monthly",
            "is_harvestable": True,
            "harvest_days_min": 25,
            "harvest_days_max": 30,
            "sources": [{"title": "Sumber", "url": "https://example.org/a"}],
        }
        data.update(overrides)
        return data

    def setUp(self):
        self.plant = Plant.objects.create(name="Kangkung", category="sayur", space_needed="small")

    def test_creates_guide_with_sources(self):
        self.run_seed([self.entry()])
        guide = CultivationGuide.objects.get(plant=self.plant)
        self.assertEqual(guide.step_list, ["Tebar benih", "Siram"])
        self.assertEqual(guide.sources[0]["title"], "Sumber")

    def test_dry_run_saves_nothing(self):
        self.run_seed([self.entry()], "--dry-run")
        self.assertFalse(CultivationGuide.objects.exists())

    def test_existing_guide_is_not_overwritten_by_default(self):
        CultivationGuide.objects.create(plant=self.plant, planting_steps="Langkah admin")
        self.run_seed([self.entry()])
        self.assertEqual(CultivationGuide.objects.get().planting_steps, "Langkah admin")

    def test_overwrite_replaces_existing_guide(self):
        CultivationGuide.objects.create(plant=self.plant, planting_steps="Langkah admin")
        self.run_seed([self.entry()], "--overwrite")
        self.assertEqual(CultivationGuide.objects.get().step_list, ["Tebar benih", "Siram"])

    def test_invalid_entries_raise_and_save_nothing(self):
        from django.core.management.base import CommandError

        for bad in (
            self.entry(plant="Tidak ada"),
            self.entry(sources=[]),
            self.entry(watering_frequency="kapan-saja"),
            self.entry(planting_steps=[]),
        ):
            with self.assertRaises(CommandError):
                self.run_seed([bad])
        self.assertFalse(CultivationGuide.objects.exists())

    def test_bundled_seed_file_is_valid(self):
        from apps.cultivation.management.commands.seed_guides import load_entries

        entries = load_entries()
        self.assertEqual(len(entries), len({p["plant"] for p in entries}))
        names = {p["plant"] for p in entries}
        for name in names:
            Plant.objects.get_or_create(name=name, defaults={"category": "hias", "space_needed": "small"})
        from django.core.management import call_command
        from io import StringIO

        call_command("seed_guides", "--dry-run", stdout=StringIO(), stderr=StringIO())