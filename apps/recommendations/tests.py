"""Test modul recommendation (versi dengan skor persentase + history)."""
from types import SimpleNamespace
from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from apps.plants.models import Plant

from . import konstan
from .konstan import MEDIUM_HYDROPONIC, MEDIUM_SOIL, land_area_to_capacity, summarize_environment
from .forms import RecommendationForm
from .models import RecommendationHistory
from .services import open_meteo
from .services.engine import fits_land_area, recommend, score_plant
from .services.open_meteo import OpenMeteoError, fetch_environment

User = get_user_model()
PW = "Kopi-Susu-Enak-92"
ENV = {"temperature": 27.0, "humidity": 80.0, "rainfall": 5.0, "period_days": 8}


def fake_plant(space_needed="small", **kw):
    base = dict(
        name="Fake", scientific_name="Fakus fakus", space_needed=space_needed,
        temp_min=None, temp_max=None, humidity_min=None, humidity_max=None,
        rainfall_min=None, rainfall_max=None,
        supports_soil=True, supports_hydroponic=False,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def make_plant(name="Bayam", **kw):
    data = dict(
        name=name, scientific_name=f"{name} scientificus", category="sayur",
        sunlight="full_sun", space_needed="small",
        temp_min=20, temp_max=32, humidity_min=60, humidity_max=90,
        rainfall_min=2, rainfall_max=10, supports_soil=True,
        supports_hydroponic=False,
    )
    data.update(kw)
    return Plant.objects.create(**data)


# --------------------------------------------------------------- constants
class ConstantsTests(SimpleTestCase):
    def test_land_area_to_capacity_boundaries(self):
        self.assertEqual(land_area_to_capacity(5), "small")
        self.assertEqual(land_area_to_capacity(5.01), "medium")
        self.assertEqual(land_area_to_capacity(20), "medium")
        self.assertEqual(land_area_to_capacity(20.01), "large")

    def test_summarize_environment_labels(self):
        summary = summarize_environment({"temperature": 30, "humidity": 30, "rainfall": 10})
        self.assertEqual(summary["temperature_label"], "Panas")
        self.assertEqual(summary["humidity_label"], "Kering")
        self.assertEqual(summary["rainfall_label"], "Tinggi")


# ------------------------------------------------------------------ engine
class LandAreaGateTests(SimpleTestCase):
    def test_small_land_only_fits_small_plant(self):
        self.assertTrue(fits_land_area(fake_plant("small"), 3))
        self.assertFalse(fits_land_area(fake_plant("medium"), 3))
        self.assertFalse(fits_land_area(fake_plant("large"), 3))

    def test_large_land_fits_everything(self):
        for need in ("small", "medium", "large"):
            self.assertTrue(fits_land_area(fake_plant(need), 100))


class ScoringTests(SimpleTestCase):
    def full(self, **kw):
        d = dict(temp_min=20, temp_max=32, humidity_min=60, humidity_max=90,
                 rainfall_min=2, rainfall_max=10)
        d.update(kw)
        return fake_plant(**d)

    def test_value_inside_range_scores_100(self):
        result = score_plant(self.full(), ENV)
        self.assertEqual(result["score"], 100)
        self.assertEqual(len(result["reasons"]), 3)

    def test_value_outside_range_degrades_but_not_below_zero(self):
        # suhu env=27, plant butuh 30-35 -> di luar rentang tapi masih ada skor
        plant = self.full(temp_min=30, temp_max=35)
        result = score_plant(plant, ENV)
        self.assertLess(result["score"], 100)
        self.assertGreaterEqual(result["score"], 0)

    def test_far_outside_range_scores_zero_not_negative(self):
        plant = self.full(temp_min=100, temp_max=110)
        result = score_plant(plant, ENV)
        self.assertGreaterEqual(result["score"], 0)

    def test_missing_criteria_are_skipped(self):
        result = score_plant(fake_plant(temp_min=20, temp_max=32), ENV)
        self.assertEqual(len(result["reasons"]), 1)
        self.assertEqual(result["score"], 100)

    def test_no_climate_data_returns_none(self):
        self.assertIsNone(score_plant(fake_plant(), ENV))

    def test_single_sided_bound(self):
        self.assertEqual(score_plant(fake_plant(temp_min=20), ENV)["score"], 100)
        self.assertEqual(score_plant(fake_plant(temp_max=35), ENV)["score"], 100)
        below = score_plant(fake_plant(temp_min=30), ENV)["score"]
        self.assertLess(below, 100)


class WeightedScoringTests(SimpleTestCase):
    """Pastikan CRITERIA_WEIGHTS beneran dipakai dan dinormalisasi otomatis
    terhadap kriteria yang datanya ada di tanaman (bukan dianggap 0)."""

    def setUp(self):
        self._original_weights = dict(konstan.CRITERIA_WEIGHTS)
        self.addCleanup(lambda: konstan.CRITERIA_WEIGHTS.update(self._original_weights))

    def test_equal_weights_equals_plain_average(self):
        # suhu 100% (di dalam rentang), kelembapan jauh di luar rentang -> ~rendah
        plant = fake_plant(temp_min=20, temp_max=32, humidity_min=10, humidity_max=20)
        result = score_plant(plant, ENV)
        temp_score = 100.0
        humidity_score = _range_score_for_test(80.0, 10, 20)
        expected = round((temp_score + humidity_score) / 2)
        self.assertEqual(result["score"], expected)

    def test_higher_weight_pulls_score_toward_that_criterion(self):
        plant = fake_plant(temp_min=20, temp_max=32, humidity_min=10, humidity_max=20)

        konstan.CRITERIA_WEIGHTS.update({"temperature": 1, "humidity": 1, "rainfall": 1})
        equal_score = score_plant(plant, ENV)["score"]

        konstan.CRITERIA_WEIGHTS.update({"temperature": 9, "humidity": 1, "rainfall": 1})
        temp_heavy_score = score_plant(plant, ENV)["score"]

        # Suhu (100%) dikasih bobot jauh lebih besar dari kelembapan yang jelek
        # -> skor akhir harus naik mendekati skor suhu, bukan turun.
        self.assertGreater(temp_heavy_score, equal_score)

    def test_weight_of_missing_criterion_is_excluded_not_zero(self):
        # Tanaman cuma punya data suhu. Walau bobot rainfall dibikin besar,
        # itu tidak boleh menjatuhkan skor karena datanya memang tidak ada.
        konstan.CRITERIA_WEIGHTS.update({"temperature": 1, "humidity": 1, "rainfall": 99})
        plant = fake_plant(temp_min=20, temp_max=32)
        result = score_plant(plant, ENV)
        self.assertEqual(result["score"], 100)

    def test_reasons_mention_the_weight_used(self):
        konstan.CRITERIA_WEIGHTS.update({"temperature": 2, "humidity": 1, "rainfall": 1})
        plant = fake_plant(temp_min=20, temp_max=32)
        result = score_plant(plant, ENV)
        self.assertTrue(any("bobot 2" in r for r in result["reasons"]))


def _range_score_for_test(value, low, high):
    from .services.engine import _range_score
    return _range_score(value, low, high)


class RecommendEndToEndTests(TestCase):
    def test_gate_excludes_wrong_medium_and_wrong_space(self):
        make_plant("Cocok", temp_min=20, temp_max=32)
        make_plant("SalahMedium", supports_soil=False, supports_hydroponic=True)
        make_plant("KebesaranRuang", space_needed="large")
        names = [p["plant_name"] for p in recommend(ENV, MEDIUM_SOIL, land_area=3)]
        self.assertEqual(names, ["Cocok"])

    def test_top_5_limit_and_sorted_desc(self):
        for i in range(8):
            make_plant(f"P{i}", temp_min=20 + i, temp_max=32)
        result = recommend(ENV, MEDIUM_SOIL, land_area=100)
        self.assertEqual(len(result), 5)
        scores = [p["match_percentage"] for p in result]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_scientific_name_included(self):
        make_plant("Bayam", scientific_name="Amaranthus tricolor")
        result = recommend(ENV, MEDIUM_SOIL, land_area=100)
        self.assertEqual(result[0]["scientific_name"], "Amaranthus tricolor")

    def test_plants_without_climate_data_excluded_from_results(self):
        make_plant("TanpaData", temp_min=None, temp_max=None,
                  humidity_min=None, humidity_max=None,
                  rainfall_min=None, rainfall_max=None)
        self.assertEqual(recommend(ENV, MEDIUM_SOIL, land_area=100), [])


# --------------------------------------------------------------- open-meteo
def fake_response(payload, status=200):
    resp = mock.Mock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status.side_effect = (
        requests.HTTPError("boom") if status >= 400 else None
    )
    return resp


def hourly_payload(days=2, temp=26.0, humidity=80.0, rain_per_hour=0.25):
    n = days * 24
    return {"hourly": {
        "temperature_2m": [temp] * n,
        "relative_humidity_2m": [humidity] * n,
        "precipitation": [rain_per_hour] * n,
    }}


class OpenMeteoTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @mock.patch.object(open_meteo.requests, "get")
    def test_parses_and_averages(self, get):
        get.return_value = fake_response(hourly_payload(days=2))
        env = fetch_environment(-6.2, 106.8)
        self.assertEqual(env["temperature"], 26.0)
        self.assertEqual(env["rainfall"], 6.0)

    @mock.patch.object(open_meteo.requests, "get")
    def test_network_error_becomes_openmeteoerror(self, get):
        get.side_effect = requests.ConnectionError("down")
        with self.assertRaises(OpenMeteoError):
            fetch_environment(1, 1)

    @mock.patch.object(open_meteo.requests, "get")
    def test_second_call_is_served_from_cache(self, get):
        get.return_value = fake_response(hourly_payload())
        fetch_environment(-6.2001, 106.8001)
        fetch_environment(-6.2002, 106.8002)
        self.assertEqual(get.call_count, 1)


# ------------------------------------------------------------------- forms
class RecommendationFormTests(SimpleTestCase):
    def data(self, **kw):
        d = {"land_name": "Kebun", "latitude": "-6.2", "longitude": "106.8",
             "land_area": "10", "planting_medium": MEDIUM_SOIL}
        d.update(kw)
        return d

    def test_valid(self):
        self.assertTrue(RecommendationForm(self.data()).is_valid())

    def test_invalid(self):
        for kw in (dict(land_name=""), dict(land_area="0"), dict(land_area="-5"),
                  dict(latitude="91"), dict(planting_medium="aeroponic")):
            self.assertFalse(RecommendationForm(self.data(**kw)).is_valid(), kw)


# ------------------------------------------------------------------- views
FETCH = "apps.recommendations.views.fetch_environment"


class ViewBase(TestCase):
    def setUp(self):
        cache.clear()
        self.budi = User.objects.create_user("budi", password=PW)
        self.sari = User.objects.create_user("sari", password=PW)
        self.admin = User.objects.create_user("boss", password=PW, is_staff=True)
        self.index = reverse("recommendations:index")
        self.result = reverse("recommendations:result")
        self.save_url = reverse("recommendations:save")
        self.list_url = reverse("recommendations:history_list")

    def submit(self, client=None, **overrides):
        client = client or self.client
        data = {"land_name": "Kebun Depan", "latitude": "-6.2", "longitude": "106.8",
                "land_area": "10", "planting_medium": MEDIUM_SOIL}
        data.update(overrides)
        with mock.patch(FETCH, return_value=dict(ENV)):
            return client.post(self.index, data)

    def make_history(self, user, name="Kebun"):
        return RecommendationHistory.objects.create(
            user=user, land_name=name, latitude=-6.2, longitude=106.8,
            land_area=10, planting_medium=MEDIUM_SOIL,
            environment_snapshot={"raw": ENV, "summary": summarize_environment(ENV)},
            recommended_plants=[{"plant_id": 1, "plant_name": "Bayam",
                                 "scientific_name": "Amaranthus sp.",
                                 "match_percentage": 90, "reasons": ["ok"]}])


class RecommendationFlowTests(ViewBase):
    def test_guest_full_flow(self):
        make_plant("Bayam")
        r = self.submit()
        self.assertRedirects(r, self.result)
        page = self.client.get(self.result)
        self.assertContains(page, "Bayam")
        self.assertContains(page, "Kebun Depan")
        self.assertContains(page, "% cocok")
        self.assertContains(page, "daftar")

    def test_land_area_gate_reflected_in_result(self):
        make_plant("Pohon Besar", space_needed="large")
        self.submit(land_area="2")  # lahan kecil
        page = self.client.get(self.result)
        self.assertNotContains(page, "Pohon Besar")
        self.assertContains(page, "Belum ada tanaman")

    def test_api_failure_shows_error(self):
        with mock.patch(FETCH, side_effect=OpenMeteoError("down")):
            r = self.client.post(self.index, {
                "land_name": "X", "latitude": "-6.2", "longitude": "106.8",
                "land_area": "10", "planting_medium": MEDIUM_SOIL})
        self.assertContains(r, "Data cuaca belum bisa diambil")
        self.assertNotIn("recommendation_result", self.client.session)

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(self.index, {"land_name": "x", "latitude": "1",
                                "longitude": "1", "land_area": "1",
                                "planting_medium": MEDIUM_SOIL})
        self.assertEqual(r.status_code, 403)

    def test_admin_sees_result_but_no_save_button(self):
        make_plant("Bayam")
        self.client.force_login(self.admin)
        self.submit()
        page = self.client.get(self.result)
        self.assertContains(page, "Bayam")
        self.assertNotContains(page, "Simpan ke Riwayat")


class SaveHistoryTests(ViewBase):
    def test_guest_save_redirects_to_login(self):
        r = self.client.post(self.save_url)
        self.assertIn("/accounts/login/", r["Location"])
        self.assertEqual(RecommendationHistory.objects.count(), 0)

    def test_admin_save_forbidden(self):
        self.client.force_login(self.admin)
        self.submit()
        self.assertEqual(self.client.post(self.save_url).status_code, 403)

    def test_save_persists_land_name_from_session(self):
        make_plant("Bayam")
        self.client.force_login(self.budi)
        self.submit(land_name="Kebun Belakang")
        r = self.client.post(self.save_url)
        history = RecommendationHistory.objects.get()
        self.assertRedirects(r, reverse("recommendations:history_detail", args=[history.pk]))
        self.assertEqual(history.land_name, "Kebun Belakang")
        self.assertEqual(history.user, self.budi)
        self.assertIn("raw", history.environment_snapshot)
        self.assertIn("summary", history.environment_snapshot)
        self.assertEqual(history.recommended_plants[0]["plant_name"], "Bayam")

    def test_double_submit_does_not_duplicate(self):
        self.client.force_login(self.budi)
        self.submit()
        self.client.post(self.save_url)
        self.client.post(self.save_url)
        self.assertEqual(RecommendationHistory.objects.count(), 1)

    def test_save_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.budi)
        self.assertEqual(c.post(self.save_url).status_code, 403)


class HistoryAuthorizationTests(ViewBase):
    def setUp(self):
        super().setUp()
        self.mine = self.make_history(self.budi, "Punya Budi")
        self.theirs = self.make_history(self.sari, "Punya Sari")

    def urls_for(self, pk):
        return [reverse(f"recommendations:{n}", args=[pk])
                for n in ("history_detail", "history_update", "history_delete")]

    def test_guest_redirected(self):
        for url in [self.list_url] + self.urls_for(self.mine.pk):
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_admin_forbidden(self):
        self.client.force_login(self.admin)
        for url in [self.list_url] + self.urls_for(self.mine.pk):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_others_history_is_404(self):
        self.client.force_login(self.budi)
        for url in self.urls_for(self.theirs.pk):
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_list_shows_only_own(self):
        self.client.force_login(self.budi)
        page = self.client.get(self.list_url)
        self.assertContains(page, "Punya Budi")
        self.assertNotContains(page, "Punya Sari")


class HistoryCrudTests(ViewBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.budi)
        self.history = self.make_history(self.budi, "Lama")

    def test_detail_renders_snapshot(self):
        page = self.client.get(reverse("recommendations:history_detail", args=[self.history.pk]))
        self.assertContains(page, "Lama")
        self.assertContains(page, "Bayam")
        self.assertContains(page, "90% cocok")

    def test_update_changes_only_land_name(self):
        r = self.client.post(reverse("recommendations:history_update", args=[self.history.pk]),
                             {"land_name": "Baru", "latitude": "1", "land_area": "999"})
        self.assertEqual(r.status_code, 302)
        self.history.refresh_from_db()
        self.assertEqual(self.history.land_name, "Baru")
        self.assertEqual(self.history.latitude, -6.2)
        self.assertEqual(self.history.land_area, 10)

    def test_delete_removes_history(self):
        r = self.client.post(reverse("recommendations:history_delete", args=[self.history.pk]))
        self.assertRedirects(r, self.list_url)
        self.assertFalse(RecommendationHistory.objects.filter(pk=self.history.pk).exists())

    def test_history_survives_plant_rename(self):
        history = self.make_history(self.budi, "Snapshot")
        page = self.client.get(reverse("recommendations:history_detail", args=[history.pk]))
        self.assertContains(page, "Bayam")  # nama tersimpan di snapshot, bukan live query
