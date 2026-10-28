from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView

from apps.core.mixins import RegularUserRequiredMixin
from .forms import ProfileEditForm, UserEditForm
from .models import UserProfile


class ProfileDetailView(RegularUserRequiredMixin, DetailView):
    model = UserProfile
    template_name = "profiles/profile.html"

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)  
        return profile


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