from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
)
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from apps.core import throttle
from .form import RegisterForm


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        # login() otomatis ganti session key -> cegah session fixation
        login(self.request, user)
        messages.success(self.request, "Akun berhasil dibuat.")
        return redirect(settings.LOGIN_REDIRECT_URL)


class SecureLoginView(LoginView):
    """Login + pembatas percobaan (5x gagal -> terkunci 15 menit).

    - Pesan error generik (tidak membocorkan username ada/tidak)
    - Parameter ?next= sudah divalidasi Django (anti open-redirect)
    - User yang sudah login di-redirect keluar dari halaman login
    """

    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "")
        if throttle.is_locked(request, username):
            form = self.get_form()
            form.add_error(
                None, "Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit."
            )
            return self.render_to_response(
                self.get_context_data(form=form), status=429
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        throttle.reset(self.request, form.cleaned_data.get("username", ""))
        return super().form_valid(form)

    def form_invalid(self, form):
        throttle.register_failure(self.request, self.request.POST.get("username", ""))
        return super().form_invalid(form)


class SecureLogoutView(LogoutView):
    """Logout hanya lewat POST (Django 5+), dilindungi CSRF."""

    next_page = reverse_lazy("accounts:login")


class ChangePasswordView(PasswordChangeView):
    """Wajib login (bawaan). Session tidak putus setelah ganti password
    karena update_session_auth_hash dipanggil otomatis oleh Django."""

    template_name = "accounts/change_password.html"
    success_url = reverse_lazy("accounts:password_change")

    def form_valid(self, form):
        messages.success(self.request, "Password berhasil diubah.")
        return super().form_valid(form)