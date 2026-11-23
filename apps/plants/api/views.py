"""API katalog untuk mobile, memakai session autentikasi bersama proyek."""

from django.db.models import Q
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from ..models import Plant
from .serializers import PlantSerializer


class PlantPagination(PageNumberPagination):
    page_size = 6


class PlantListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PlantSerializer
    pagination_class = PlantPagination

    def get_queryset(self):
        queryset = Plant.objects.all()
        params = self.request.query_params
        query = params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(scientific_name__icontains=query)
            )

        for parameter, field, choices in (
            ("category", "category", Plant.CATEGORY_CHOICES),
            ("space", "space_needed", Plant.SPACE_NEEDED_CHOICES),
        ):
            value = params.get(parameter, "").strip()
            if value in dict(choices):
                queryset = queryset.filter(**{field: value})

        medium = params.get("medium", "").strip()
        if medium == "soil":
            queryset = queryset.filter(supports_soil=True)
        elif medium == "hydroponic":
            queryset = queryset.filter(supports_hydroponic=True)

        sunlight = params.get("sunlight", "").strip()
        if sunlight in dict(Plant.SUNLIGHT_CHOICES):
            # Sama seperti katalog web; kompatibel dengan SQLite dan PostgreSQL.
            matching_ids = [
                plant.pk for plant in queryset.only("pk", "sunlight")
                if sunlight in (plant.sunlight or [])
            ]
            queryset = queryset.filter(pk__in=matching_ids)

        sort_fields = {
            "name": ("name", "pk"),
            "name_desc": ("-name", "pk"),
            "category": ("category", "name", "pk"),
            "updated": ("-updated_at", "name", "pk"),
        }
        sort = params.get("sort", "name").strip()
        return queryset.order_by(*sort_fields.get(sort, sort_fields["name"]))


class PlantDetailAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PlantSerializer
    queryset = Plant.objects.all()
