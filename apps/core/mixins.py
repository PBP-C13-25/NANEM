"""
Mixin authorization yang dipakai SEMUA module (Bob, Nicholas, Hafidz, Zhafira).

Aturan dari PRD:
  - Guest  : hanya Recommendation (tanpa mixin apa pun)
  - User   : Catalog, Detail, Guide, History, Profile, Collection
  - Admin  : CRUD Plant + CRUD Cultivation Guide

Urutan MRO PENTING: taruh mixin ini PALING KIRI di definisi class.
    class PlantCreateView(AdminRequiredMixin, CreateView): ...
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class ActiveUserRequiredMixin(LoginRequiredMixin):
    """Harus login + akun aktif.

    - Belum login  -> redirect ke LOGIN_URL (?next=...)
    - Sudah login  -> lolos (Django sudah menolak user is_active=False
                      di level authentication backend)
    Dipakai untuk: Catalog, Plant Detail, Cultivation Guide (read).
    """

    raise_exception = False


class RegularUserRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """Registered user BIASA (bukan admin).

    PRD: History, Profile, Collection bukan fitur personal admin.
    - Belum login  -> redirect ke login
    - Admin        -> 403
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_active and not user.is_staff


class AdminRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """Hanya admin (is_staff). Dipakai untuk CRUD Plant & Cultivation Guide.

    - Belum login       -> redirect ke login
    - Login tapi bukan admin -> 403 (bukan redirect, biar tidak looping)
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_active and user.is_staff


class OwnedQuerysetMixin:
    """Object-level authorization: user hanya bisa akses data MILIKNYA.

    Filter queryset berdasarkan pemilik, jadi object milik orang lain
    otomatis 404 (bukan 403) -> tidak bocor bahwa ID tersebut ada.
    Mencegah IDOR pada History & Collection.

        class HistoryDeleteView(RegularUserRequiredMixin,
                                OwnedQuerysetMixin, DeleteView):
            model = RecommendationHistory

    Wajib dipakai bersama mixin login di atas (login dicek duluan).
    Jika field pemilik bukan `user`, set `owner_field`.
    """

    owner_field = "user"

    def get_queryset(self):
        return super().get_queryset().filter(**{self.owner_field: self.request.user})