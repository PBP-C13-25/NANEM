import tempfile
from io import BytesIO
from PIL import Image

from django.test import override_settings
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from ..models import PlantCollection
from . import views

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PlantCollectionAPITests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='password123'
        )

        self.dummy_image = self._generate_dummy_image()

        self.collection = PlantCollection.objects.create(
            owner=self.user,
            title='Monstera Deliciosa',
            description='Tanaman hias daun lebar.',
            photo=self.dummy_image
        )

    def _generate_dummy_image(self):
        """Helper untuk membuat file gambar dummy sederhana."""
        file = BytesIO()
        image = Image.new('RGB', (100, 100), 'green')
        image.save(file, 'jpeg')
        file.seek(0)
        return SimpleUploadedFile('test_photo.jpg', file.read(), content_type='image/jpeg')

    # 1. URL RESOLVING TESTS
    def test_api_urls_resolving(self):
        """Menguji resolusi URL API ke setiap APIView yang sesuai."""
        self.assertEqual(resolve(reverse('collection_api:list')).func.view_class, views.CollectionListCreateAPIView)
        self.assertEqual(resolve(reverse('collection_api:detail', kwargs={'pk': self.collection.pk})).func.view_class, views.CollectionDetailAPIView)
        self.assertEqual(resolve(reverse('collection_api:like', kwargs={'pk': self.collection.pk})).func.view_class, views.ToggleLikeAPIView)

    # 2. VIEW ENDPOINT TESTS
    def test_collection_list_api(self):
        """Menguji pengambilan daftar koleksi tanaman (list)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('collection_api:list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Monstera Deliciosa')
        self.assertEqual(response.data[0]['owner_username'], 'testuser')

    def test_collection_list_filter_by_owner(self):
        """Menguji filter query parameter ?owner= pada endpoint list."""
        PlantCollection.objects.create(
            owner=self.other_user,
            title='Lidah Mertua',
            description='Tanaman pembersih udara.',
            photo=self._generate_dummy_image()
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('collection_api:list'), {'owner': self.other_user.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Lidah Mertua')
        self.assertEqual(response.data[0]['owner'], self.other_user.pk)

    def test_collection_detail_api(self):
        """Menguji pengambilan detail koleksi (detail)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('collection_api:detail', kwargs={'pk': self.collection.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.collection.pk)
        self.assertEqual(response.data['title'], 'Monstera Deliciosa')

    def test_collection_create_api(self):
        """Menguji pembuatan koleksi baru (POST ke list)."""
        self.client.force_authenticate(user=self.user)
        post_data = {
            'title': 'Kaktus Koboi',
            'description': 'Tahan terhadap cuaca panas.',
            'photo': self._generate_dummy_image()
        }
        response = self.client.post(reverse('collection_api:list'), data=post_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PlantCollection.objects.filter(title='Kaktus Koboi').exists())

        created_item = PlantCollection.objects.get(title='Kaktus Koboi')
        self.assertEqual(created_item.owner, self.user)

    def test_collection_create_api_invalid(self):
        """Menguji gagal create saat field wajib kosong & format error dibungkus 'errors'."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('collection_api:list'), data={'title': ''}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('title', response.data['errors'])
        self.assertIn('photo', response.data['errors'])

    def test_collection_create_description_max_words(self):
        """Menguji validasi deskripsi maksimal 10 kata."""
        self.client.force_authenticate(user=self.user)
        long_description = "satu dua tiga empat lima enam tujuh delapan sembilan sepuluh sebelas"
        post_data = {
            'title': 'Kaktus Mini',
            'description': long_description,
            'photo': self._generate_dummy_image()
        }
        response = self.client.post(reverse('collection_api:list'), data=post_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('description', response.data['errors'])

    def test_collection_update_api(self):
        """Menguji pembaruan data koleksi oleh pemiliknya (PATCH/PUT ke detail)."""
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('collection_api:detail', kwargs={'pk': self.collection.pk})

        # Uji PATCH (partial update)
        patch_response = self.client.patch(detail_url, data={'title': 'Monstera Deliciosa Updated'}, format='multipart')
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.title, 'Monstera Deliciosa Updated')

        # Uji PUT (full update dengan foto baru)
        put_data = {
            'title': 'Monstera Full Put',
            'description': 'Deskripsi baru.',
            'photo': self._generate_dummy_image()
        }
        put_response = self.client.put(detail_url, data=put_data, format='multipart')
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.title, 'Monstera Full Put')

    def test_collection_delete_api(self):
        """Menguji penghapusan koleksi oleh pemiliknya (DELETE ke detail)."""
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('collection_api:detail', kwargs={'pk': self.collection.pk})
        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PlantCollection.objects.filter(pk=self.collection.pk).exists())

    def test_toggle_like_api(self):
        """Menguji fungsi menyukai dan batal menyukai (like)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('collection_api:like', kwargs={'pk': self.collection.pk})

        # 1. Menambahkan Like
        response1 = self.client.post(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data, {'is_liked': True, 'like_count': 1})
        self.assertTrue(self.collection.likes.filter(pk=self.user.pk).exists())

        # 2. Menghapus Like
        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data, {'is_liked': False, 'like_count': 0})
        self.assertFalse(self.collection.likes.filter(pk=self.user.pk).exists())

    # 3. AUTHORIZATION & PERMISSION TESTS
    def test_authorization_guest_denied(self):
        """Tamu (belum login) mendapat status 401 Unauthorized."""
        detail_url = reverse('collection_api:detail', kwargs={'pk': self.collection.pk})

        edit_response = self.client.patch(detail_url, data={'title': 'Guest Hack'}, format='multipart')
        self.assertEqual(edit_response.status_code, status.HTTP_401_UNAUTHORIZED)

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authorization_other_user_not_found(self):
        """User lain (bukan owner) mendapat status 404 Not Found saat mencoba edit/hapus."""
        self.client.force_authenticate(user=self.other_user)
        detail_url = reverse('collection_api:detail', kwargs={'pk': self.collection.pk})

        # Coba PATCH sebagai user lain -> 404 Not Found
        edit_response = self.client.patch(detail_url, data={'title': 'Hack'}, format='multipart')
        self.assertEqual(edit_response.status_code, status.HTTP_404_NOT_FOUND)

        # Coba DELETE sebagai user lain -> 404 Not Found
        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)