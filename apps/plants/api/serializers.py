"""Representasi JSON tanaman; metadata riset tetap berada di file seed."""

from django.forms.models import model_to_dict
from rest_framework import serializers

from ..forms import PlantForm
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
        read_only_fields = ("id", "perenual_id", "created_at", "updated_at")

    def validate(self, attrs):
        # PATCH hanya mengganti field yang dikirim, lalu validasi keseluruhan
        # tanaman melalui form yang sama dengan CRUD web.
        data = model_to_dict(self.instance or Plant(), fields=PlantForm.Meta.fields)
        data.update(attrs)
        for field in ("indoor", "drought_tolerant"):
            value = data[field]
            data[field] = "" if value is None else ("true" if value else "false")

        self.plant_form = PlantForm(data=data, instance=self.instance)
        if not self.plant_form.is_valid():
            raise serializers.ValidationError({
                field: [error["message"] for error in errors]
                for field, errors in self.plant_form.errors.get_json_data().items()
            })
        return attrs

    def create(self, validated_data):
        return self.plant_form.save()

    def update(self, instance, validated_data):
        return self.plant_form.save()
