from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.profiles.models import UserProfile


class ProfileTestCases(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            email='test@example.com',
            first_name='Hafidz',
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpassword123',
            first_name='Jihan',
        )
        # akun non-aktif / staff untuk mengetes filter SearchUsersView
        self.inactive_user = User.objects.create_user(
            username='inactiveuser', password='testpassword123', is_active=False
        )
        self.admin_user = User.objects.create_user(
            username='adminuser',
            password='testpassword123',
            is_staff=True,
            is_superuser=True,
        )
        self.client = Client()

    def test_profile_detail_view_authenticated(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('profiles:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/profile.html')

    def test_admin_profile_detail_access(self):
        # tambahan: memastikan akun admin dapat membuka halaman profil dengan status 200
        self.client.login(username='adminuser', password='testpassword123')
        response = self.client.get(reverse('profiles:profile'))
        self.assertEqual(response.status_code, 200)

    def test_user_search_view(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('profiles:search'), {'q': 'other'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['query'], 'other')
        usernames = [u['username'] for u in data['users']]
        self.assertIn('otheruser', usernames)
        self.assertNotIn('inactiveuser', usernames)
        self.assertNotIn('adminuser', usernames)

    def test_profile_edit_get_and_post(self):
        self.client.login(username='testuser', password='testpassword123')

        # test GET edit profile
        response = self.client.get(reverse('profiles:profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/profile_edit.html')

        # test POST edit profile (mengubah first_name)
        response_post = self.client.post(
            reverse('profiles:profile_edit'),
            {
                'first_name': 'Hafidz Updated',
                'username': 'testuser',
            },
        )
        self.assertIn(response_post.status_code, [200, 302])

        # verifikasi data berubah di database
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Hafidz Updated')

    def test_public_profile_view_success_and_404(self):
        self.client.login(username='testuser', password='testpassword123')

        response = self.client.get(
            reverse(
                'profiles:public_profile', kwargs={'username': 'otheruser'}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/profile.html')

        response_404 = self.client.get(
            reverse(
                'profiles:public_profile',
                kwargs={'username': 'user_ngawur_gak_ada'},
            )
        )
        self.assertEqual(response_404.status_code, 404)

    def test_delete_account_view(self):
        self.client.login(username='testuser', password='testpassword123')
        user_pk = self.user.pk

        response = self.client.post(reverse('profiles:delete_account'))
        self.assertIn(response.status_code, [200, 302])

        self.assertFalse(User.objects.filter(pk=user_pk).exists())