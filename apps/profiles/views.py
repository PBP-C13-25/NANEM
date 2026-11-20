from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.plant_collection.models import PlantCollection
from .forms import ProfileEditForm, UserEditForm
from .models import UserProfile
from .serializers import UserProfileSerializer, UserSearchSerializer


class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = UserProfile
    template_name = "profiles/profile.html"
    context_object_name = 'userprofile'

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_collections'] = PlantCollection.objects.filter(owner=self.request.user).order_by('-created_at')
        return context


class PublicProfileView(LoginRequiredMixin, DetailView):
    model = UserProfile
    template_name = "profiles/profile.html"
    context_object_name = 'userprofile'

    def get_object(self, queryset=None):
        target_user = get_object_or_404(User, username=self.kwargs.get('username'))
        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.object
        context['user_collections'] = PlantCollection.objects.filter(owner=profile.user).order_by('-created_at')
        return context


class ProfileEditView(LoginRequiredMixin, View):
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

            if 'photo-clear' in request.POST:
                if profile.photo:
                    profile.photo.delete(save=False)
                profile.photo = None

            profile_form.save()
            messages.success(request, "Profile berhasil diperbarui.")
            return redirect('profiles:profile')

        context = {
            'user_form': user_form,
            'profile_form': profile_form,
        }
        return render(request, self.template_name, context)


class DeleteAccountView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Akun kamu berhasil dihapus.")
        return redirect('/')


class SearchUsersView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        users = []
        if query:
            users = (
                User.objects
                .filter(username__icontains=query, is_active=True)
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


# endpoint DRF untuk mobile (flutter)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_get_profile(request):
    """Mengambil data profil pengguna yang sedang login."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    serializer = UserProfileSerializer(profile, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def api_edit_profile(request):
    """Memperbarui data user dan UserProfile (termasuk upload/hapus foto)."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # validasi username dulu sebelum menyimpan perubahan
    raw_username = request.data.get('username')
    validated_username = None
    if raw_username is not None:
        validated_username = str(raw_username).strip()
        if not validated_username:
            return Response({'detail': 'Username tidak boleh kosong.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=validated_username).exclude(pk=user.pk).exists():
            return Response({'detail': 'Username sudah digunakan oleh pengguna lain.'}, status=status.HTTP_400_BAD_REQUEST)

    validated_first_name = None
    if 'first_name' in request.data and request.data.get('first_name') is not None:
        validated_first_name = str(request.data.get('first_name')).strip()

    validated_profile_name = None
    if 'name' in request.data and request.data.get('name') is not None:
        validated_profile_name = str(request.data.get('name')).strip()

    clear_photo = str(request.data.get('clear_photo', '')).strip().lower() in ['true', '1', 'yes']
    uploaded_photo = request.FILES.get('photo')

    # simpan perubahan User
    user_changed = False
    if validated_username is not None:
        user.username = validated_username
        user_changed = True
    if validated_first_name is not None:
        user.first_name = validated_first_name
        user_changed = True
    if user_changed:
        user.save()

    # simpan perubahan UserProfile
    profile_changed = False
    if validated_profile_name is not None:
        profile.name = validated_profile_name
        profile_changed = True

    if clear_photo:
        if profile.photo:
            profile.photo.delete(save=False)
        profile.photo = None
        profile_changed = True
    elif uploaded_photo is not None:
        if profile.photo:
            profile.photo.delete(save=False)
        profile.photo = uploaded_photo
        profile_changed = True

    if profile_changed:
        profile.save()

    serializer = UserProfileSerializer(profile, context={'request': request})
    return Response(
        {
            'message': 'Profil berhasil diperbarui.',
            'profile': serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_delete_account(request):
    """Menghapus akun pengguna yang sedang login."""
    user = request.user
    logout(request)
    user.delete()
    return Response({'message': 'Akun berhasil dihapus.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_search_users(request):
    """Mencari pengguna aktif berdasarkan username."""
    query = request.GET.get('q', '').strip()
    users = []
    if query:
        users = (
            User.objects
            .filter(username__icontains=query, is_active=True)
            .select_related('profile')
            .order_by('username')[:20]
        )

    serializer = UserSearchSerializer(users, many=True, context={'request': request})
    return Response({'query': query, 'users': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_get_public_profile(request, username):
    """Mengambil data profil publik pengguna lain berdasarkan username."""
    target_user = get_object_or_404(User, username=username, is_active=True)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    serializer = UserProfileSerializer(profile, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)