from rest_framework import serializers

from apps.plants.models import Plant

from ..models import CultivationGuide


class GuideSerializer(serializers.ModelSerializer):
    plant_id = serializers.IntegerField(read_only=True)
    planting_steps = serializers.ListField(
        source="step_list", child=serializers.CharField(), read_only=True
    )
    watering_frequency_label = serializers.CharField(
        source="get_watering_frequency_display", read_only=True
    )
    fertilizing_frequency_label = serializers.CharField(
        source="get_fertilizing_frequency_display", read_only=True
    )
    harvest_label = serializers.CharField(read_only=True)

    class Meta:
        model = CultivationGuide
        fields = (
            "id",
            "plant_id",
            "planting_steps",
            "watering_frequency",
            "watering_frequency_label",
            "watering_note",
            "fertilizing_frequency",
            "fertilizing_frequency_label",
            "fertilizing_note",
            "is_harvestable",
            "harvest_days_min",
            "harvest_days_max",
            "harvest_label",
            "harvest_note",
            "updated_at",
        )


class GuideListItemSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    has_guide = serializers.SerializerMethodField()
    guide_updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Plant
        fields = (
            "id",
            "name",
            "scientific_name",
            "category",
            "category_label",
            "has_guide",
            "guide_updated_at",
        )

    def get_has_guide(self, obj):
        return hasattr(obj, "cultivation_guide")

    def get_guide_updated_at(self, obj):
        guide = getattr(obj, "cultivation_guide", None)
        if guide is None:
            return None
        return serializers.DateTimeField().to_representation(guide.updated_at)
    