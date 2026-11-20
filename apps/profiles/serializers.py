from rest_framework import serializers
from django.contrib.auth.models import User
from apps.plant_collection.models import PlantCollection
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    collections = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ['username', 'first_name', 'email', 'name', 'photo', 'collections']

    def get_collections(self, obj):
        request = self.context.get('request')
        qs = PlantCollection.objects.filter(owner=obj.user).order_by('-created_at')
        results = []
        for item in qs:
            image_url = None
            item_image = getattr(item, 'image', None)
            if item_image:
                raw_url = item_image.url
                image_url = request.build_absolute_uri(raw_url) if request else raw_url

            created_at_val = getattr(item, 'created_at', None)
            results.append({
                'id': item.id,
                'title': getattr(item, 'title', getattr(item, 'name', '')),
                'image': image_url,
                'created_at': created_at_val.isoformat() if created_at_val else None,
            })
        return results


class UserSearchSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    initial = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'name', 'initial', 'photo']

    def get_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.name if profile and profile.name else obj.first_name

    def get_photo(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.photo:
            request = self.context.get('request')
            return request.build_absolute_uri(profile.photo.url) if request else profile.photo.url
        return ''

    def get_initial(self, obj):
        return (obj.first_name or obj.username)[:1].upper()