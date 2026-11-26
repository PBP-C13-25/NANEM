from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..forms import ProfileEditForm, UserEditForm
from ..models import UserProfile
from .serializers import (
    PublicUserProfileSerializer,
    UserProfileSerializer,
    UserSearchSerializer,
)


def _form_errors(*forms):
    merged = {}
    for form in forms:
        for field, errors in form.errors.get_json_data().items():
            messages = [err["message"] for err in errors]
            if field in merged:
                merged[field].extend(messages)
            else:
                merged[field] = messages
    return merged


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_get_profile(request):
    """GET /api/profile/ -> mengambil profil pengguna yang sedang login."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    serializer = UserProfileSerializer(profile, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def api_edit_profile(request):
    """PATCH /api/profile/edit/ -> memperbarui data user dan UserProfile."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    user_data = {
        "first_name": request.data.get("first_name", user.first_name),
        "username": request.data.get("username", user.username),
    }

    user_form = UserEditForm(data=user_data, instance=user)
    profile_form = ProfileEditForm(
        data=request.data,
        files=request.FILES,
        instance=profile,
    )

    if not (user_form.is_valid() and profile_form.is_valid()):
        return Response(
            {"errors": _form_errors(user_form, profile_form)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    errors = {}
    validated_name = None
    if "name" in request.data and request.data.get("name") is not None:
        validated_name = str(request.data.get("name")).strip()
        if len(validated_name) > 100:
            errors["name"] = ["Maksimal 100 karakter."]
    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    user_form.save()

    clear_photo = str(request.data.get("clear_photo", "")).strip().lower() in {
        "true",
        "1",
        "yes",
    }
    uploaded_photo = request.FILES.get("photo")
    old_photo = profile.photo if (clear_photo or uploaded_photo is not None) else None

    updated_profile = profile_form.save(commit=False)
    if validated_name is not None:
        updated_profile.name = validated_name
    if clear_photo:
        updated_profile.photo = None
    updated_profile.save()

    if old_photo and old_photo.name and old_photo.name != getattr(updated_profile.photo, "name", None):
        old_photo.delete(save=False)

    serializer = UserProfileSerializer(updated_profile, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def api_delete_account(request):
    """DELETE /api/profile/delete/ -> menghapus akun pengguna yang sedang login."""
    user = request.user
    logout(request)
    user.delete()
    return Response({"detail": "Akun berhasil dihapus."}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_search_users(request):
    """GET /api/profile/search/?q= -> mencari pengguna aktif berdasarkan username."""
    query = request.GET.get("q", "").strip()
    users = []
    if query:
        users = (
            User.objects.filter(username__icontains=query, is_active=True)
            .select_related("profile")
            .order_by("username")[:20]
        )

    serializer = UserSearchSerializer(users, many=True, context={"request": request})
    return Response({"query": query, "users": serializer.data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_get_public_profile(request, username):
    """GET /api/users/<username>/ -> mengambil profil publik pengguna lain (tanpa email)."""
    target_user = get_object_or_404(User, username=username, is_active=True)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    serializer = PublicUserProfileSerializer(profile, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)