from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class ProfileTestCases(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123', email='test@example.com')
        self.other_user = User.objects.create_user(username='otheruser', password='testpassword123')
        self.client = Client()

    def test_profile_detail_view_authenticated(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('profiles:profile'))
        self.assertEqual(response.status_code, 200)

    def test_user_search_view(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('profiles:search'), {'q': 'other'})
        self.assertEqual(response.status_code, 200)

    def test_profile_edit_get_and_post(self):
        self.client.login(username='testuser', password='testpassword123')
        
        # test GET edit profile
        response = self.client.get(reverse('profiles:profile_edit'))
        self.assertEqual(response.status_code, 200)

        # test POST edit profile
        response_post = self.client.post(reverse('profiles:profile_edit'), {
            'bio': 'Halo ini bio baru',
            'location': 'Jakarta'
        })
        self.assertIn(response_post.status_code, [200, 302])

    def test_public_profile_view(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('profiles:public_profile', kwargs={'username': 'otheruser'}))
        self.assertEqual(response.status_code, 200)

    def test_delete_account_view(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('profiles:delete_account'))
        self.assertIn(response.status_code, [200, 302])