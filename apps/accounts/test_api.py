"""Tes API akun (register, login, logout, me, ganti password)."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

STRONG_PASSWORD = "KebunHijau#2026"


class AccountApiTestBase(APITestCase):
    def setUp(self):
        cache.clear()  # pembatas login disimpan di cache
        self.user = User.objects.create_user(
            username="jihan", password=STRONG_PASSWORD, first_name="Jihan"
        )
        self.register_url = reverse("accounts_api:register")
        self.login_url = reverse("accounts_api:login")
        self.logout_url = reverse("accounts_api:logout")
        self.me_url = reverse("accounts_api:me")
        self.password_url = reverse("accounts_api:password_change")

    def login(self, username="jihan", password=STRONG_PASSWORD):
        return self.client.post(
            self.login_url, {"username": username, "password": password}, format="json"
        )


class RegisterApiTests(AccountApiTestBase):
    def payload(self, **overrides):
        data = {
            "first_name": "Budi",
            "username": "budi",
            "password1": STRONG_PASSWORD,
            "password2": STRONG_PASSWORD,
        }
        data.update(overrides)
        return data

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(self.register_url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["username"], "budi")
        self.assertEqual(response.data["user"]["first_name"], "Budi")
        user = User.objects.get(username="budi")
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertEqual(self.client.get(self.me_url).status_code, status.HTTP_200_OK)

    def test_cannot_inject_staff_or_superuser(self):
        self.client.post(
            self.register_url,
            self.payload(is_staff=True, is_superuser=True),
            format="json",
        )

        user = User.objects.get(username="budi")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_username_is_case_insensitive_unique(self):
        response = self.client.post(
            self.register_url, self.payload(username="JIHAN"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data["errors"])

    def test_weak_password_rejected(self):
        response = self.client.post(
            self.register_url,
            self.payload(password1="12345678", password2="12345678"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password2", response.data["errors"])
        self.assertFalse(User.objects.filter(username="budi").exists())

    def test_password_mismatch(self):
        response = self.client.post(
            self.register_url, self.payload(password2="BedaSekali#2026"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password2", response.data["errors"])

    def test_logged_in_user_cannot_register_again(self):
        self.client.force_login(self.user)
        response = self.client.post(self.register_url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="budi").exists())


class LoginLogoutApiTests(AccountApiTestBase):
    def test_login_ok(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "jihan")
        self.assertFalse(response.data["user"]["is_staff"])
        self.assertEqual(self.client.get(self.me_url).status_code, status.HTTP_200_OK)

    def test_session_key_rotates_on_login(self):
        self.client.get(self.me_url)  # buat sesi guest dulu
        session = self.client.session
        session["penanda"] = "ada"
        session.save()
        before = session.session_key

        self.login()

        self.assertNotEqual(self.client.session.session_key, before)
        self.assertEqual(self.client.session.get("penanda"), "ada")

    def test_generic_error_for_wrong_password_and_unknown_user(self):
        wrong = self.login(password="salah-banget")
        unknown = self.login(username="tidakada")

        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wrong.data, unknown.data)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()

        self.assertEqual(self.login().status_code, status.HTTP_400_BAD_REQUEST)

    def test_lockout_after_5_failures_even_with_right_password(self):
        for _ in range(5):
            self.login(password="salah-banget")

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(self.client.get(self.me_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_success_resets_failure_counter(self):
        for _ in range(4):
            self.login(password="salah-banget")
        self.login()
        self.client.post(self.logout_url)

        for _ in range(4):
            self.login(password="salah-banget")

        self.assertEqual(self.login().status_code, status.HTTP_200_OK)

    def test_logout(self):
        self.login()

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(self.me_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_as_guest_is_ok(self):
        self.assertEqual(self.client.post(self.logout_url).status_code, status.HTTP_200_OK)

    def test_logout_requires_post(self):
        self.login()
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_me_as_guest_is_401(self):
        self.assertEqual(self.client.get(self.me_url).status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordApiTests(AccountApiTestBase):
    NEW_PASSWORD = "DaunMuda#2027"

    def test_change_keeps_session_and_new_password_works(self):
        self.login()

        response = self.client.post(
            self.password_url,
            {
                "old_password": STRONG_PASSWORD,
                "new_password1": self.NEW_PASSWORD,
                "new_password2": self.NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(self.me_url).status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW_PASSWORD))
        self.assertFalse(self.user.check_password(STRONG_PASSWORD))

    def test_wrong_old_password(self):
        self.login()

        response = self.client.post(
            self.password_url,
            {
                "old_password": "bukan-ini",
                "new_password1": self.NEW_PASSWORD,
                "new_password2": self.NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data["errors"])

    def test_guest_gets_401(self):
        response = self.client.post(self.password_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenAuthApiTests(AccountApiTestBase):
    """Alur aplikasi Flutter: login dapat token, lalu kirim header Authorization."""

    def token_client(self, token):
        # Client baru tanpa cookie session, supaya yang diuji benar-benar token.
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return client

    def test_login_returns_token_that_works_without_session(self):
        token = self.login().data["token"]

        response = self.token_client(token).get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "jihan")

    def test_login_again_returns_same_token(self):
        first = self.login().data["token"]
        self.client.logout()

        self.assertEqual(self.login().data["token"], first)

    def test_register_returns_token(self):
        response = self.client.post(
            self.register_url,
            {
                "first_name": "Budi",
                "username": "budi",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        token = response.data["token"]
        self.assertEqual(Token.objects.get(key=token).user.username, "budi")
        self.assertEqual(self.token_client(token).get(self.me_url).status_code, status.HTTP_200_OK)

    def test_failed_login_has_no_token(self):
        response = self.login(password="salah-banget")

        self.assertNotIn("token", response.data)
        self.assertFalse(Token.objects.exists())

    def test_logout_with_token_revokes_it(self):
        token = self.login().data["token"]
        client = self.token_client(token)

        self.assertEqual(client.post(self.logout_url).status_code, status.HTTP_200_OK)

        self.assertFalse(Token.objects.filter(key=token).exists())
        self.assertEqual(client.get(self.me_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_logout_keeps_token_of_other_device(self):
        token = self.login().data["token"]

        self.client.post(self.logout_url)  # logout web (session), bukan token

        self.assertEqual(self.token_client(token).get(self.me_url).status_code, status.HTTP_200_OK)

    def test_invalid_token_is_401(self):
        response = self.token_client("bukan-token-asli").get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_401_says_token(self):
        response = APIClient().get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["WWW-Authenticate"], "Token")

    def test_inactive_user_token_is_rejected(self):
        token = self.login().data["token"]
        self.user.is_active = False
        self.user.save()

        response = self.token_client(token).get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_rotates_token(self):
        old_token = self.login().data["token"]
        old_client = self.token_client(old_token)
        new_password = "DaunMuda#2027"

        response = old_client.post(
            self.password_url,
            {
                "old_password": STRONG_PASSWORD,
                "new_password1": new_password,
                "new_password2": new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_token = response.data["token"]
        self.assertNotEqual(new_token, old_token)
        self.assertEqual(old_client.get(self.me_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.token_client(new_token).get(self.me_url).status_code, status.HTTP_200_OK)

    def test_deleting_user_deletes_token(self):
        token = self.login().data["token"]

        self.user.delete()

        self.assertFalse(Token.objects.filter(key=token).exists())
