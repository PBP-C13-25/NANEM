import tempfile
from io import BytesIO
from PIL import Image

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import PlantCollection
from .forms import PlantCollectionForm
from . import views

# Menggunakan folder sementara untuk penyimpanan file media saat pengujian
MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PlantCollectionTests(TestCase):

    def setUp(self):
        # Membuat unit penguji (Client) dan User
        self.client = Client()
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

        # Helper untuk membuat gambar tiruan (dummy image)
        self.dummy_image = self._generate_dummy_image()

        # Membuat objek PlantCollection awal untuk pengujian
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

    # ==========================================
    # 1. MODEL TESTS
    # ==========================================
    def test_plant_collection_model(self):
        """Menguji metode __str__ dan total_likes pada Model PlantCollection."""
        self.assertEqual(str(self.collection), 'Monstera Deliciosa')
        self.assertEqual(self.collection.total_likes(), 0)

        # Menambahkan like dan menguji total_likes
        self.collection.likes.add(self.user)
        self.assertEqual(self.collection.total_likes(), 1)

    # ==========================================
    # 2. FORM TESTS
    # ==========================================
    def test_plant_collection_form_valid(self):
        """Menguji bahwa form valid ketika diberikan input yang benar."""
        photo = self._generate_dummy_image()
        form_data = {
            'title': 'Aglonema',
            'description': 'Tanaman hias warna-warni.',
        }
        file_data = {
            'photo': photo
        }
        form = PlantCollectionForm(data=form_data, files=file_data)
        self.assertTrue(form.is_valid())

    def test_plant_collection_form_invalid(self):
        """Menguji form tidak valid saat field wajib dikosongkan."""
        form = PlantCollectionForm(data={'title': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('photo', form.errors)

    # ==========================================
    # 3. URL TESTS
    # ==========================================
    def test_urls_resolving(self):
        """Menguji resolusi URL ke View yang sesuai."""
        self.assertEqual(resolve(reverse('collection:index')).func.view_class, views.CollectionListView)
        self.assertEqual(resolve(reverse('collection:create')).func.view_class, views.CollectionCreateView)
        self.assertEqual(resolve(reverse('collection:detail', kwargs={'pk': self.collection.pk})).func.view_class, views.CollectionDetailView)
        self.assertEqual(resolve(reverse('collection:edit', kwargs={'pk': self.collection.pk})).func.view_class, views.CollectionUpdateView)
        self.assertEqual(resolve(reverse('collection:delete', kwargs={'pk': self.collection.pk})).func.view_class, views.CollectionDeleteView)
        self.assertEqual(resolve(reverse('collection:like', kwargs={'pk': self.collection.pk})).func.view_class, views.ToggleLikeView)

    # ==========================================
    # 4. VIEW TESTS
    # ==========================================
    def test_collection_list_view(self):
        """Menguji tampilan daftar koleksi tanaman."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('collection:index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "plant_collection/index.html")
        self.assertIn('my_posts', response.context)
        self.assertEqual(len(response.context['my_posts']), 1)

    def test_collection_detail_view(self):
        """Menguji tampilan detail koleksi."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('collection:detail', kwargs={'pk': self.collection.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "plant_collection/plant_detail.html")
        self.assertEqual(response.context['post'], self.collection)

    def test_collection_create_view(self):
        """Menguji pembuatan koleksi baru via POST request."""
        self.client.login(username='testuser', password='password123')
        
        # Test GET Request
        get_response = self.client.get(reverse('collection:create'))
        self.assertEqual(get_response.status_code, 200)
        self.assertFalse(get_response.context['is_edit'])

        # Test POST Request
        new_photo = self._generate_dummy_image()
        post_data = {
            'title': 'Kaktus Koboi',
            'description': 'Tahan terhadap cuaca panas.',
            'photo': new_photo
        }
        response = self.client.post(reverse('collection:create'), data=post_data)
        
        self.assertRedirects(response, reverse('collection:index')) 
        self.assertTrue(PlantCollection.objects.filter(title='Kaktus Koboi').exists())
        
        # Memastikan owner terpasang sesuai user yang sedang login
        created_item = PlantCollection.objects.get(title='Kaktus Koboi')
        self.assertEqual(created_item.owner, self.user) 

    def test_collection_update_view(self):
        """Menguji pembaruan data koleksi oleh pemiliknya."""
        self.client.login(username='testuser', password='password123')
        
        # Test GET Request
        get_response = self.client.get(reverse('collection:edit', kwargs={'pk': self.collection.pk}))
        self.assertEqual(get_response.status_code, 200)
        self.assertTrue(get_response.context['is_edit'])

        # Test POST Request
        updated_photo = self._generate_dummy_image()
        post_data = {
            'title': 'Monstera Deliciosa Updated',
            'description': 'Deskripsi diperbarui.',
            'photo': updated_photo
        }
        response = self.client.post(reverse('collection:edit', kwargs={'pk': self.collection.pk}), data=post_data)
        
        self.collection.refresh_from_db()
        self.assertRedirects(response, reverse('collection:detail', kwargs={'pk': self.collection.pk})) 
        self.assertEqual(self.collection.title, 'Monstera Deliciosa Updated')

    def test_collection_delete_view(self):
        """Menguji penghapusan koleksi oleh pemiliknya."""
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('collection:delete', kwargs={'pk': self.collection.pk}))
        
        self.assertRedirects(response, reverse('collection:index')) 
        self.assertFalse(PlantCollection.objects.filter(pk=self.collection.pk).exists())

    def test_toggle_like_view(self):
        """Menguji fungsi menyukai dan batal menyukai via endpoint JSON."""
        self.client.login(username='testuser', password='password123')
        url = reverse('collection:like', kwargs={'pk': self.collection.pk})

        # 1. Menambahkan Like (First POST)
        response1 = self.client.post(url)
        self.assertEqual(response1.status_code, 200)
        self.assertJSONEqual(response1.content, {'is_liked': True, 'like_count': 1})
        self.assertIn(self.user, self.collection.likes.all()) 

        # 2. Menghapus Like (Second POST)
        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, 200)
        self.assertJSONEqual(response2.content, {'is_liked': False, 'like_count': 0})
        self.assertNotIn(self.user, self.collection.likes.all()) 