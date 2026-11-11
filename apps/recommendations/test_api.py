"""Tes API Rekomendasi & Riwayat (Django REST Framework).

Open-Meteo dan engine di-mock: tes tidak boleh memanggil internet,
dan tes engine sendiri sudah ada di tes web.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import RecommendationHistory
from .services.open_meteo import OpenMeteoError
from .views import SESSION_KEY

User = get_user_model()

ENVIRONMENT = {
    "temperature": 27.4,
    "humidity": 82.0,
    "rainfall": 5.2,
    "period_days": 91,
    "source": "open-meteo",
    "fetched_at": "2026-11-09T12:30:00+00:00",
}
PLANTS = [
    {
        "plant_id": 1,
        "plant_name": "Kangkung",
        "match_percentage": 95,
        "criteria_count": 3,
        "matched_count": 2,
        "reasons": [{"text": "Suhu: 100% cocok", "matched": True}],
    },
    {"plant_id": 2, "plant_name": "Bayam", "match_percentage": 80},
]
VALID_INPUT = {
    "land_name": "Kebun Belakang",
    "latitude": -6.36,
    "longitude": 106.83,
    "land_area": 20,
    "planting_medium": "hydroponic",
}

FETCH = "apps.recommendations.api.views.fetch_environment"
RECOMMEND = "apps.recommendations.api.views.recommend"


class ApiTestBase(APITestCase):
    def setUp(self):
        cache.clear()  # rate limit & cache cuaca disimpan di cache
        self.user = User.objects.create_user(username="jihan", password="rahasia123")
        self.other = User.objects.create_user(username="lain", password="rahasia123")
        self.recommend_url = reverse("recommendations_api:recommend")
        self.list_url = reverse("recommendations_api:history_list")

    def detail_url(self, pk):
        return reverse("recommendations_api:history_detail", args=[pk])

    def make_history(self, user, land_name="Kebun", plants=None, environment=None):
        return RecommendationHistory.objects.create(
            user=user,
            land_name=land_name,
            latitude=-6.36,
            longitude=106.83,
            land_area=20,
            planting_medium="hydroponic",
            environment_snapshot=(
                {"raw": ENVIRONMENT, "summary": {}} if environment is None else environment
            ),
            recommended_plants=PLANTS if plants is None else plants,
        )

    def generate(self, data=None):
        with patch(FETCH, return_value=ENVIRONMENT), patch(RECOMMEND, return_value=PLANTS):
            return self.client.post(self.recommend_url, data or VALID_INPUT, format="json")


class RecommendationApiTests(ApiTestBase):
    def test_guest_can_generate_but_cannot_save(self):
        response = self.generate()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["can_save"])
        self.assertEqual(response.data["result"]["plants"], PLANTS)
        self.assertEqual(response.data["result"]["environment"]["raw"], ENVIRONMENT)
        self.assertEqual(
            response.data["result"]["environment"]["summary"]["humidity_label"], "Lembap"
        )
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertEqual(RecommendationHistory.objects.count(), 0)

    def test_logged_in_user_can_save(self):
        self.client.force_login(self.user)
        response = self.generate()
        self.assertTrue(response.data["can_save"])

    def test_invalid_input_returns_field_errors(self):
        response = self.generate({**VALID_INPUT, "land_area": 0, "latitude": 100})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("land_area", response.data["errors"])
        self.assertIn("latitude", response.data["errors"])

    def test_invalid_medium_is_rejected(self):
        response = self.generate({**VALID_INPUT, "planting_medium": "pasir"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("planting_medium", response.data["errors"])

    def test_open_meteo_failure_returns_503(self):
        with patch(FETCH, side_effect=OpenMeteoError("down")):
            response = self.client.post(self.recommend_url, VALID_INPUT, format="json")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("cuaca", response.data["detail"])

    def test_rate_limit_after_ten_requests(self):
        for _ in range(10):
            self.assertEqual(self.generate().status_code, status.HTTP_200_OK)

        response = self.generate()
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_invalid_input_does_not_use_rate_limit(self):
        for _ in range(12):
            self.generate({**VALID_INPUT, "land_area": 0})

        self.assertEqual(self.generate().status_code, status.HTTP_200_OK)


class SaveHistoryApiTests(ApiTestBase):
    def test_guest_cannot_save(self):
        self.generate()
        response = self.client.post(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(RecommendationHistory.objects.count(), 0)

    def test_save_without_result_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_save_creates_history_once(self):
        self.client.force_login(self.user)
        self.generate()

        first = self.client.post(self.list_url)
        second = self.client.post(self.list_url)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertTrue(first.data["created"])
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertFalse(second.data["created"])
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(RecommendationHistory.objects.count(), 1)

        history = RecommendationHistory.objects.get()
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.land_name, "Kebun Belakang")
        self.assertEqual(history.recommended_plants, PLANTS)

    def test_save_again_after_history_deleted(self):
        self.client.force_login(self.user)
        self.generate()
        first_id = self.client.post(self.list_url).data["id"]
        RecommendationHistory.objects.filter(pk=first_id).delete()

        response = self.client.post(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.data["id"], first_id)

    def test_save_ignores_plants_sent_by_client(self):
        self.client.force_login(self.user)
        self.generate()

        self.client.post(self.list_url, {"plants": [{"plant_name": "Palsu"}]}, format="json")

        self.assertEqual(RecommendationHistory.objects.get().recommended_plants, PLANTS)


class HistoryListApiTests(ApiTestBase):
    def test_guest_gets_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lists_only_own_histories_newest_first(self):
        old = self.make_history(self.user, "Kebun Lama")
        new = self.make_history(self.user, "Kebun Baru")
        self.make_history(self.other, "Punya Orang")
        self.client.force_login(self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["histories"]]
        self.assertEqual(ids, [new.pk, old.pk])

    def test_list_item_shape(self):
        self.make_history(self.user)
        self.client.force_login(self.user)

        item = self.client.get(self.list_url).data["histories"][0]

        self.assertEqual(item["planting_medium_label"], "Hidroponik")
        self.assertEqual(item["top_plant"], "Kangkung")
        self.assertEqual(item["plant_count"], 2)
        self.assertIn("created_at", item)

    def test_list_handles_empty_and_old_plant_formats(self):
        self.make_history(self.user, "Kosong", plants=[])
        self.make_history(self.user, "Lama", plants=["Kangkung cocok"])
        self.client.force_login(self.user)

        items = self.client.get(self.list_url).data["histories"]

        self.assertTrue(all(item["top_plant"] is None for item in items))

    def test_search_by_land_name(self):
        self.make_history(self.user, "Kebun Belakang")
        self.make_history(self.user, "Sawah Depan")
        self.client.force_login(self.user)

        response = self.client.get(self.list_url, {"q": "kebun"})

        names = [item["land_name"] for item in response.data["histories"]]
        self.assertEqual(names, ["Kebun Belakang"])


class HistoryDetailApiTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.history = self.make_history(self.user, "Kebun Belakang")
        self.client.force_login(self.user)

    def test_detail_returns_snapshot(self):
        response = self.client.get(self.detail_url(self.history.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["plants"], PLANTS)
        self.assertEqual(response.data["environment"]["raw"], ENVIRONMENT)
        self.assertEqual(response.data["period_days"], 91)
        self.assertIn("period_start", response.data)

    def test_period_days_defaults_to_90(self):
        history = self.make_history(self.user, environment={})

        response = self.client.get(self.detail_url(history.pk))

        self.assertEqual(response.data["period_days"], 90)

    def test_other_users_history_is_404(self):
        other_history = self.make_history(self.other)

        for method in ("get", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.detail_url(other_history.pk), {"land_name": "x"}, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertTrue(RecommendationHistory.objects.filter(pk=other_history.pk).exists())

    def test_patch_updates_only_land_name(self):
        response = self.client.patch(
            self.detail_url(self.history.pk),
            {"land_name": "  Kebun Depan  ", "latitude": 50, "recommended_plants": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"id": self.history.pk, "land_name": "Kebun Depan"})
        self.history.refresh_from_db()
        self.assertEqual(self.history.land_name, "Kebun Depan")
        self.assertEqual(self.history.latitude, -6.36)
        self.assertEqual(self.history.recommended_plants, PLANTS)

    def test_patch_rejects_blank_name(self):
        response = self.client.patch(
            self.detail_url(self.history.pk), {"land_name": "   "}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("land_name", response.data)

    def test_put_is_not_allowed(self):
        response = self.client.put(
            self.detail_url(self.history.pk), {"land_name": "Baru"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_removes_history(self):
        response = self.client.delete(self.detail_url(self.history.pk))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RecommendationHistory.objects.filter(pk=self.history.pk).exists())

    def test_guest_gets_401(self):
        self.client.logout()
        response = self.client.get(self.detail_url(self.history.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
