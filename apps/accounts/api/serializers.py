"""Serializer API akun.

Input register, login, dan ganti password TIDAK divalidasi di sini, tapi lewat
form yang sama dengan web (RegisterForm, AuthenticationForm, PasswordChangeForm),
supaya aturan password, username unik, dan proteksi is_staff tetap identik.
Serializer ini hanya untuk data user yang dikirim KE aplikasi.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "is_staff")
        read_only_fields = fields
