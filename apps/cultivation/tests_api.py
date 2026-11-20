from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.plants.models import Plant

from .models import CultivationGuide


VALID = {
    "planting_steps": ["Rendam benih semalam", "Tebar benih di media", "Siram setiap pagi"],
    "watering_frequency": "daily",
    "watering_note": "Siram pagi hari",
    "fertilizing_frequency": "monthly",
    "fertilizing_note": "",
    "is_harvestable": True,
    "harvest_days_min": 30,
    "harvest_days_max": 40,
    "harvest_note": "",
}


class CultivationAPITests(APITestCase):
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

    def guide_url(self, plant):
        return reverse("cultivation_api:guide", args=[plant.pk])

    def list_url(self):
        return reverse("cultivation_api:guide_list")

    def create_guide(self, plant):
        return CultivationGuide.objects.create(
            plant=plant, **{**VALID, "planting_steps": "\n".join(VALID["planting_steps"])}
        )

    def test_guest_gets_401(self):
        response = self.client.get(self.guide_url(self.kangkung))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_null_when_no_guide(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.guide_url(self.kangkung))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["guide"])
        self.assertEqual(response.data["plant"]["name"], "Kangkung")

    def test_user_sees_guide(self):
        self.create_guide(self.kangkung)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.guide_url(self.kangkung))
        guide = response.data["guide"]
        self.assertEqual(len(guide["planting_steps"]), 3)
        self.assertEqual(guide["watering_frequency_label"], "Setiap hari")
        self.assertEqual(guide["harvest_label"], "30-40 hari setelah tanam")

    def test_unknown_plant_returns_404(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("cultivation_api:guide", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_cannot_write(self):
        response = self.client.post(self.guide_url(self.kangkung), VALID, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_write(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.guide_url(self.kangkung), VALID, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CultivationGuide.objects.count(), 0)

    def test_admin_creates_guide(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.guide_url(self.kangkung), VALID, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CultivationGuide.objects.filter(plant=self.kangkung).exists())

    def test_admin_duplicate_returns_409(self):
        self.create_guide(self.kangkung)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.guide_url(self.kangkung), VALID, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_admin_invalid_input_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        payload = {**VALID, "planting_steps": []}
        response = self.client.post(self.guide_url(self.kangkung), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("planting_steps", response.data["errors"])
        self.assertFalse(CultivationGuide.objects.exists())

    def test_admin_patch_keeps_other_fields(self):
        self.create_guide(self.kangkung)
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            self.guide_url(self.kangkung), {"watering_note": "Siram sore hari"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        guide = CultivationGuide.objects.get(plant=self.kangkung)
        self.assertEqual(guide.watering_note, "Siram sore hari")
        self.assertEqual(len(guide.step_list), 3)
        self.assertEqual(guide.harvest_days_min, 30)

    def test_admin_patch_without_guide_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            self.guide_url(self.kangkung), {"watering_note": "x"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_deletes_guide(self):
        self.create_guide(self.kangkung)
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(self.guide_url(self.kangkung))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b"")
        self.assertFalse(CultivationGuide.objects.exists())

    def test_user_cannot_delete(self):
        self.create_guide(self.kangkung)
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.guide_url(self.kangkung))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(CultivationGuide.objects.exists())

    def test_wrong_method_returns_405(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(self.list_url())
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_is_admin_only(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_filters_by_status_and_query(self):
        self.create_guide(self.kangkung)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url(), {"status": "belum"})
        self.assertEqual([p["name"] for p in response.data["plants"]], ["Bayam"])
        self.assertEqual(response.data["summary"]["with_guide"], 1)
        self.assertEqual(response.data["summary"]["without_guide"], 1)
        response = self.client.get(self.list_url(), {"q": "kang"})
        self.assertTrue(response.data["plants"][0]["has_guide"])