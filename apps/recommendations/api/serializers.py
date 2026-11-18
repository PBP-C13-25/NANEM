"""Serializer API riwayat rekomendasi.

Serializer = penerjemah antara objek model dan JSON:
- ke luar (response): objek RecommendationHistory -> dictionary -> JSON;
- ke dalam (request): JSON -> data yang sudah divalidasi.

Input form rekomendasi TIDAK divalidasi di sini, tapi lewat RecommendationForm
yang sama dengan web (lihat api/views.py), supaya aturannya tidak dobel.
"""
from datetime import timedelta

from rest_framework import serializers

from ..models import RecommendationHistory

DEFAULT_PERIOD_DAYS = 90


class HistoryListSerializer(serializers.ModelSerializer):
    """Versi ringkas untuk daftar riwayat."""

    planting_medium_label = serializers.CharField(
        source="get_planting_medium_display", read_only=True
    )
    top_plant = serializers.SerializerMethodField()
    plant_count = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationHistory
        fields = (
            "id",
            "land_name",
            "land_area",
            "planting_medium",
            "planting_medium_label",
            "top_plant",
            "plant_count",
            "created_at",
        )

    def get_top_plant(self, obj):
        plants = obj.recommended_plants or []
        if not plants or not isinstance(plants[0], dict):
            return None
        return plants[0].get("plant_name")

    def get_plant_count(self, obj):
        return len(obj.recommended_plants or [])


class HistoryDetailSerializer(serializers.ModelSerializer):
    """Versi lengkap (snapshot) untuk detail satu riwayat."""

    planting_medium_label = serializers.CharField(
        source="get_planting_medium_display", read_only=True
    )
    environment = serializers.JSONField(source="environment_snapshot", read_only=True)
    plants = serializers.JSONField(source="recommended_plants", read_only=True)
    period_days = serializers.SerializerMethodField()
    period_start = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationHistory
        fields = (
            "id",
            "land_name",
            "latitude",
            "longitude",
            "land_area",
            "planting_medium",
            "planting_medium_label",
            "environment",
            "plants",
            "period_days",
            "period_start",
            "created_at",
        )

    def get_period_days(self, obj):
        # Sama dengan HistoryDetailView di web: cari di raw, lalu summary, lalu default 90.
        snapshot = obj.environment_snapshot or {}
        raw = snapshot.get("raw", {})
        summary = snapshot.get("summary", {})
        days = raw.get("period_days") or summary.get("period_days") or DEFAULT_PERIOD_DAYS
        return round(days)

    def get_period_start(self, obj):
        start = obj.created_at - timedelta(days=self.get_period_days(obj))
        return serializers.DateTimeField().to_representation(start)


class HistoryUpdateSerializer(serializers.ModelSerializer):
    """Ubah riwayat: HANYA nama lahan (hasil rekomendasi tidak boleh diubah).

    Field lain yang ikut dikirim klien diabaikan, karena tidak ada di `fields`.
    """

    class Meta:
        model = RecommendationHistory
        fields = ("id", "land_name")
        read_only_fields = ("id",)
