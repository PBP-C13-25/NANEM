"""Representasi JSON tanaman; metadata riset tetap berada di file seed."""

from rest_framework import serializers

from ..models import Plant


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = (
            "id", "perenual_id", "name", "scientific_name", "description",
            "image_url", "category", "temp_min", "temp_max", "humidity_min",
            "humidity_max", "rainfall_min", "rainfall_max", "supports_soil",
            "supports_hydroponic", "sunlight", "watering", "care_level",
            "drought_tolerant", "indoor", "space_needed", "created_at", "updated_at",
        )
        read_only_fields = fields
