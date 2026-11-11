"""API (Django REST Framework) untuk akun: register, login, logout, me, ganti password.

Alurnya SENGAJA sama dengan view web di ../views.py:
- form yang dipakai sama (RegisterForm, AuthenticationForm, PasswordChangeForm);
- login dibatasi 5x gagal -> terkunci 15 menit (apps.core.throttle);
- login() dan update_session_auth_hash() dipanggil seperti di web,
  jadi session key berganti saat login (anti session fixation) dan
  session tidak putus setelah ganti password.
Autentikasi API memakai session yang sama dengan web (apps.core.api).
"""

from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import throttle

from ..form import RegisterForm
from .serializers import UserSerializer

GENERIC_LOGIN_ERROR = "Username atau password salah."


def _form_errors(form):
    """Ubah error Django form jadi {"field": ["pesan", ...]} untuk JSON.

    Error yang tidak menempel ke field tertentu ada di kunci "__all__".
    """
    return {
        field: [error["message"] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }


#* REGISTER
class RegisterAPIView(APIView):
    """POST /api/auth/register/

    Body: first_name, username, password1, password2.
    201 -> {"user": {...}} dan langsung login (sama seperti web).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            return Response(
                {"detail": "Kamu sudah login."}, status=status.HTTP_400_BAD_REQUEST
            )

        form = RegisterForm(data=request.data)
        if not form.is_valid():
            return Response(
                {"errors": _form_errors(form)}, status=status.HTTP_400_BAD_REQUEST
            )

        user = form.save()
        login(request, user)
        return Response(
            {"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED
        )


#* LOGIN
class LoginAPIView(APIView):
    """POST /api/auth/login/

    Body: username, password.
    200 -> {"user": {...}} | 400 salah | 429 terkunci 15 menit.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "")

        if throttle.is_locked(request, username):
            return Response(
                {"detail": "Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # AuthenticationForm yang sama dengan LoginView web: menolak akun nonaktif.
        form = AuthenticationForm(request, data=request.data)
        if not form.is_valid():
            throttle.register_failure(request, username)
            # Pesan generik: tidak membocorkan apakah username ada atau tidak.
            return Response(
                {"errors": {"__all__": [GENERIC_LOGIN_ERROR]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        throttle.reset(request, username)
        user = form.get_user()
        login(request, user)
        return Response({"user": UserSerializer(user).data})


#* LOGOUT
class LogoutAPIView(APIView):
    """POST /api/auth/logout/ -> 200, juga kalau sesi sudah habis."""

    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"detail": "Berhasil keluar."})


#* USER YANG SEDANG LOGIN
class MeAPIView(APIView):
    """GET /api/auth/me/ -> {"user": {...}} | 401 kalau belum login.

    Dipakai aplikasi saat dibuka untuk mengecek sesi masih berlaku.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})


#* GANTI PASSWORD
class ChangePasswordAPIView(APIView):
    """POST /api/auth/password/

    Body: old_password, new_password1, new_password2.
    200 -> sesi tetap aktif (update_session_auth_hash), password lama tidak berlaku.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        form = PasswordChangeForm(request.user, data=request.data)
        if not form.is_valid():
            return Response(
                {"errors": _form_errors(form)}, status=status.HTTP_400_BAD_REQUEST
            )

        user = form.save()
        update_session_auth_hash(request, user)
        return Response({"detail": "Password berhasil diubah."})
