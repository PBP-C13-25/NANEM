from django.contrib.auth.models import User
from rest_framework import serializers

from apps.plant_collection.models import PlantCollection
from ..models import UserProfile


def _serialize_collections(user, request):
    qs = PlantCollection.objects.filter(owner=user).order_by("-created_at")
    results = []
    for item in qs:
        photo_url = None
        if item.photo:
            raw_url = item.photo.url
            photo_url = request.build_absolute_uri(raw_url) if request else raw_url

        results.append(
            {
                "id": item.id,
                "title": item.title,
                "photo": photo_url,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )
    return results


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    photo = serializers.SerializerMethodField()
    collections = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ["username", "first_name", "email", "name", "photo", "collections"]

    def get_photo(self, obj):
        if not obj.photo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url

    def get_collections(self, obj):
        return _serialize_collections(obj.user, self.context.get("request"))


class PublicUserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    photo = serializers.SerializerMethodField()
    collections = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ["username", "first_name", "name", "photo", "collections"]

    def get_photo(self, obj):
        if not obj.photo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url

    def get_collections(self, obj):
        return _serialize_collections(obj.user, self.context.get("request"))


class UserSearchSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    initial = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["username", "first_name", "name", "initial", "photo"]

    def get_name(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.name:
            return profile.name
        return obj.first_name

    def get_photo(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.photo:
            request = self.context.get("request")
            return request.build_absolute_uri(profile.photo.url) if request else profile.photo.url
        return None

    def get_initial(self, obj):
        return (obj.first_name or obj.username)[:1].upper()