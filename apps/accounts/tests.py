from django.test import TestCase
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

# Create your tests here.

User = get_user_model()
GOOD_PW = "Kopi-Susu-Enak-92"


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("budi", password=GOOD_PW, first_name="Budi")
        self.other = User.objects.create_user("sari", password=GOOD_PW)
        self.admin = User.objects.create_user("boss", password=GOOD_PW, is_staff=True)


class RegisterTests(Base):
    url = reverse("accounts:register")

    def data(self, **kw):
        d = {"first_name": "Ani", "username": "ani", "password1": GOOD_PW, "password2": GOOD_PW}
        d.update(kw)
        return d

    def test_register_ok_hashed_and_logged_in(self):
        r = self.client.post(self.url, self.data())
        self.assertRedirects(r, "/home/", fetch_redirect_response=False)
        u = User.objects.get(username="ani")
        self.assertNotEqual(u.password, GOOD_PW)
        self.assertTrue(u.password.startswith("pbkdf2_"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.pk)

    def test_cannot_inject_staff_or_superuser(self):
        self.client.post(self.url, self.data(is_staff="on", is_superuser="on", is_active="off"))
        u = User.objects.get(username="ani")
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_superuser)
        self.assertTrue(u.is_active)

    def test_username_case_insensitive_unique(self):
        r = self.client.post(self.url, self.data(username="BUDI"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="BUDI").exists())

    def test_weak_passwords_rejected(self):
        for pw in ["12345678", "password", "short1", "anisetiawan1"]:
            r = self.client.post(self.url, self.data(username="anisetiawan", password1=pw, password2=pw))
            self.assertEqual(r.status_code, 200, pw)
        self.assertFalse(User.objects.filter(username="anisetiawan").exists())

    def test_password_mismatch(self):
        r = self.client.post(self.url, self.data(password2="lain-Banget-77"))
        self.assertEqual(r.status_code, 200)

    def test_logged_in_user_redirected_from_register(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 302)


class LoginLogoutTests(Base):
    url = reverse("accounts:login")

    def test_login_ok(self):
        r = self.client.post(self.url, {"username": "budi", "password": GOOD_PW})
        self.assertRedirects(r, "/home/", fetch_redirect_response=False)

    def test_session_key_rotates_on_login(self):
        self.client.get(self.url)
        before = self.client.session.session_key
        self.client.post(self.url, {"username": "budi", "password": GOOD_PW})
        self.assertNotEqual(before, self.client.session.session_key)

    def test_generic_error_same_for_unknown_and_wrong_password(self):
        a = self.client.post(self.url, {"username": "budi", "password": "salah"})
        b = self.client.post(self.url, {"username": "tidakada", "password": "salah"})
        self.assertEqual(a.context["form"].non_field_errors(), b.context["form"].non_field_errors())

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        r = self.client.post(self.url, {"username": "budi", "password": GOOD_PW})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_open_redirect_blocked(self):
        for nxt in ["https://evil.com/", "//evil.com/", "javascript:alert(1)"]:
            r = self.client.post(f"{self.url}?next={nxt}", {"username": "budi", "password": GOOD_PW})
            self.assertEqual(r.status_code, 302)
            self.assertEqual(r["Location"], "/home/", nxt)
            self.client.logout()

    def test_safe_next_allowed(self):
        r = self.client.post(f"{self.url}?next=/user/", {"username": "budi", "password": GOOD_PW})
        self.assertEqual(r["Location"], "/user/")

    def test_lockout_after_5_failures_even_with_right_password(self):
        for _ in range(5):
            self.client.post(self.url, {"username": "budi", "password": "salah"})
        r = self.client.post(self.url, {"username": "budi", "password": GOOD_PW})
        self.assertEqual(r.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lockout_case_insensitive_username(self):
        for _ in range(5):
            self.client.post(self.url, {"username": "BUDI", "password": "salah"})
        r = self.client.post(self.url, {"username": "budi", "password": GOOD_PW})
        self.assertEqual(r.status_code, 429)

    def test_success_resets_counter(self):
        for _ in range(4):
            self.client.post(self.url, {"username": "budi", "password": "salah"})
        self.client.post(self.url, {"username": "budi", "password": GOOD_PW})
        self.client.logout()
        for _ in range(4):
            self.client.post(self.url, {"username": "budi", "password": "salah"})
        r = self.client.post(self.url, {"username": "budi", "password": GOOD_PW})
        self.assertEqual(r.status_code, 302)

    def test_lock_on_one_user_does_not_block_another(self):
        for _ in range(5):
            self.client.post(self.url, {"username": "budi", "password": "salah"})
        r = self.client.post(self.url, {"username": "sari", "password": GOOD_PW})
        self.assertEqual(r.status_code, 302)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        self.assertEqual(c.post(reverse("accounts:logout")).status_code, 403)


class PasswordChangeTests(Base):
    url = reverse("accounts:password_change")
    new = "Teh-Manis-Dingin-55"

    def test_anonymous_redirected(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_change_keeps_session_and_new_password_works(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url, {"old_password": GOOD_PW, "new_password1": self.new, "new_password2": self.new})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/user/").status_code, 200)  # masih login
        self.client.logout()
        self.assertTrue(self.client.login(username="budi", password=self.new))

    def test_wrong_old_password(self):
        self.client.force_login(self.user)
        r = self.client.post(self.url, {"old_password": "salah", "new_password1": self.new, "new_password2": self.new})
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(GOOD_PW))


class AuthorizationTests(Base):
    def test_guest_redirected_everywhere(self):
        for p in ["/user/", "/regular/", "/adminonly/", "/owned/"]:
            r = self.client.get(p)
            self.assertEqual(r.status_code, 302, p)
            self.assertIn("/accounts/login/?next=" + p, r["Location"])

    def test_user_matrix(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/user/").status_code, 200)
        self.assertEqual(self.client.get("/regular/").status_code, 200)
        self.assertEqual(self.client.get("/adminonly/").status_code, 403)

    def test_admin_matrix(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/user/").status_code, 200)
        self.assertEqual(self.client.get("/adminonly/").status_code, 200)
        self.assertEqual(self.client.get("/regular/").status_code, 403)

    def test_deactivated_user_loses_access_immediately(self):
        self.client.force_login(self.admin)
        self.admin.is_active = False
        self.admin.save()
        r = self.client.get("/adminonly/")
        self.assertEqual(r.status_code, 302)  # sesi tidak valid lagi -> dianggap guest

    def test_demoted_admin_loses_access_immediately(self):
        self.client.force_login(self.admin)
        self.admin.is_staff = False
        self.admin.save()
        self.assertEqual(self.client.get("/adminonly/").status_code, 403)

    def test_owned_queryset_only_own_rows(self):
        ct = ContentType.objects.get_for_model(User)
        mine = LogEntry.objects.create(user=self.user, content_type=ct, object_id="1", object_repr="a", action_flag=1)
        theirs = LogEntry.objects.create(user=self.other, content_type=ct, object_id="1", object_repr="b", action_flag=1)
        self.client.force_login(self.user)
        body = self.client.get("/owned/").content.decode()
        self.assertIn(f"[{mine.pk}]", body)
        self.assertNotIn(f"[{theirs.pk}]", body)