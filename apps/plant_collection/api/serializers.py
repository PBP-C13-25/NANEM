from rest_framework import serializers
from ..models import PlantCollection

class PlantCollectionSerializer(serializers.ModelSerializer):
    owner_username = serializers.ReadOnlyField(source='owner.username')
    total_likes = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = PlantCollection
        fields = [
            'id',
            'owner',
            'owner_username',
            'title',
            'description',
            'photo',
            'total_likes',
            'is_liked',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']

    def validate_description(self, value):
        if value and len(value.split()) > 10:
            raise serializers.ValidationError("Deskripsi maksimal terdiri dari 10 kata.")
        return value
    
    def validate_photo(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Ukuran foto maksimal 5MB.")
        return value
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return any(u.pk == request.user.pk for u in obj.likes.all())
        return False