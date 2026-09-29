from django.contrib import messages
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

    def get_object(self):
        return self.request.user.profile


class ProfileEditView(RegularUserRequiredMixin, View):
    template_name = "profiles/profile_edit.html"

    def get(self, request):
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
        context = {
            'user_form': user_form,
            'profile_form': profile_form,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile berhasil diperbarui.")
            return redirect('profiles:profile')

        context = {
            'user_form': user_form,
            'profile_form': profile_form,
        }
        return render(request, self.template_name, context)