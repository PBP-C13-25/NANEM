from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()
GOOD_PW = "Kopi-Susu-Enak-92"


def _make_png(size=(40, 40), color=(34, 139, 34)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


class ProfileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="budi",
            password=GOOD_PW,
            first_name="Budi",
            email="budi@example.com",
        )
        self.other = User.objects.create_user(
            username="sari",
            password=GOOD_PW,
            first_name="Sari",
            email="sari@example.com",
        )
        self.inactive = User.objects.create_user(
            username="nonaktif",
            password=GOOD_PW,
            first_name="Nonaktif",
            email="nonaktif@example.com",
            is_active=False,
        )

    def test_guest_unauthorized_401(self):
        r = self.client.get(reverse("profiles_api:profile"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_own_profile_ok(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.get(reverse("profiles_api:profile"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["username"], "budi")
        self.assertEqual(r.data["email"], "budi@example.com")
        self.assertIsNone(r.data["photo"])
        self.assertEqual(r.data["collections"], [])

    def test_edit_profile_success(self):
        self.client.force_authenticate(user=self.user)
        photo = SimpleUploadedFile("avatar.png", _make_png(), content_type="image/png")
        r = self.client.patch(
            reverse("profiles_api:profile_edit"),
            data={"first_name": "Budi Santoso", "name": "Kebun Budi", "photo": photo},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["first_name"], "Budi Santoso")
        self.assertEqual(r.data["name"], "Kebun Budi")
        self.assertIsNotNone(r.data["photo"])

    def test_edit_duplicate_username_case_insensitive_400(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.patch(
            reverse("profiles_api:profile_edit"),
            data={"username": "SARI"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", r.data)
        self.assertIn("username", r.data["errors"])

    def test_edit_photo_over_2mb_400(self):
        self.client.force_authenticate(user=self.user)
        oversized = SimpleUploadedFile(
            "large.png",
            b"0" * (2 * 1024 * 1024 + 1),
            content_type="image/png",
        )
        r = self.client.patch(
            reverse("profiles_api:profile_edit"),
            data={"photo": oversized},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", r.data)
        self.assertIn("photo", r.data["errors"])

    def test_public_profile_hides_email_and_inactive_or_unknown_404(self):
        self.client.force_authenticate(user=self.user)

        r_ok = self.client.get(reverse("profiles_api:public_profile", args=["sari"]))
        self.assertEqual(r_ok.status_code, status.HTTP_200_OK)
        self.assertEqual(r_ok.data["username"], "sari")
        self.assertNotIn("email", r_ok.data)

        r_inactive = self.client.get(reverse("profiles_api:public_profile", args=["nonaktif"]))
        self.assertEqual(r_inactive.status_code, status.HTTP_404_NOT_FOUND)

        r_unknown = self.client.get(reverse("profiles_api:public_profile", args=["tidakada"]))
        self.assertEqual(r_unknown.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_users_returns_null_photo_when_empty(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.get(reverse("profiles_api:profile_search"), {"q": "sari"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["users"]), 1)
        self.assertIsNone(r.data["users"][0]["photo"])

    def test_delete_account(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.delete(reverse("profiles_api:profile_delete"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())