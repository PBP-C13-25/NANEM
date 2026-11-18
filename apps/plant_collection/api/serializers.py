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

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(pk=request.user.pk).exists()
        return False