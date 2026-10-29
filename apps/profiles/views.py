from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView

from apps.core.mixins import RegularUserRequiredMixin
from apps.plant_collection.models import PlantCollection
from .forms import ProfileEditForm, UserEditForm
from .models import UserProfile


class ProfileDetailView(RegularUserRequiredMixin, DetailView):
    model = UserProfile
    template_name = "profiles/profile.html"
    context_object_name = 'userprofile'

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ambil koleksi tanaman milik user yang sedang login
        context['user_collections'] = PlantCollection.objects.filter(owner=self.request.user).order_by('-created_at' if hasattr(PlantCollection, 'created_at') else '-pk')
        return context


class PublicProfileView(RegularUserRequiredMixin, DetailView):
    model = UserProfile
    template_name = "profiles/profile.html"
    context_object_name = 'userprofile'

    def get_object(self, queryset=None):
        # mengambil user berdasarkan username dari URL, lalu ambil/buat profilnya
        target_user = get_object_or_404(User, username=self.kwargs.get('username'))
        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_object()
        # ambil koleksi tanaman milik user target dari public profile
        context['user_collections'] = PlantCollection.objects.filter(owner=profile.user).order_by('-created_at' if hasattr(PlantCollection, 'created_at') else '-pk')
        return context


class ProfileEditView(RegularUserRequiredMixin, View):
    template_name = "profiles/profile_edit.html"

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=profile)

        context = {
            'user_form': user_form,
            'profile_form': profile_form,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()

            # logika untuk menghapus foto jika checkbox 'Hapus' dicentang
            if 'photo-clear' in request.POST:
                if profile.photo:
                    profile.photo.delete(save=False)  # hapus file fisik dari storage/media
                profile.photo = None  # mengosongkan kolom photo di database

            profile_form.save()
            messages.success(request, "Profile berhasil diperbarui.")
            return redirect('profiles:profile')

        context = {
            'user_form': user_form,
            'profile_form': profile_form,
        }
        return render(request, self.template_name, context)


class DeleteAccountView(RegularUserRequiredMixin, View):
    def post(self, request):
        user = request.user
        logout(request)  # logout sesi user terlebih dahulu
        user.delete()    # hapus akun dari database (UserProfile ikut terhapus otomatis karena CASCADE)
        messages.success(request, "Akun kamu berhasil dihapus.")
        return redirect('/')  # redirect ke halaman utama


@user_passes_test(lambda u: u.is_authenticated and u.is_active and not u.is_staff)
def search_users(request):
    """Mengembalikan hasil pencarian user dalam format JSON (dipakai live search di halaman koleksi)."""
    query = request.GET.get('q', '').strip()
    users = []
    if query:
        # cari user berdasarkan username yang mengandung kata kunci (case insensitive)
        users = (
            User.objects
            .filter(username__icontains=query)
            .select_related('profile')
            .order_by('username')[:20]
        )

    data = []
    for u in users:
        profile = getattr(u, 'profile', None)
        photo = getattr(profile, 'photo', None)
        data.append({
            'username': u.username,
            'initial': (u.first_name or u.username)[:1].upper(),
            'photo': photo.url if photo else '',
            'url': reverse('profiles:public_profile', args=[u.username]),
        })

    return JsonResponse({'query': query, 'users': data})