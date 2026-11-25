"""API katalog untuk mobile, memakai session autentikasi bersama proyek."""

from django.db.models import Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission, SAFE_METHODS

from ..models import Plant
from .serializers import PlantSerializer


class PlantPagination(PageNumberPagination):
    page_size = 6


class PlantPermission(BasePermission):
    """User aktif dapat membaca, hanya staff aktif dapat mengubah tanaman."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated and user.is_active
            and (request.method in SAFE_METHODS or user.is_staff)
        )


class PlantAPIMixin:
    permission_classes = [PlantPermission]
    serializer_class = PlantSerializer

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(exc, ValidationError):
            errors = response.data
            if isinstance(errors, dict) and "non_field_errors" in errors:
                errors.setdefault("__all__", []).extend(errors.pop("non_field_errors"))
            response.data = {"errors": errors}
        return response


class PlantListAPIView(PlantAPIMixin, generics.ListCreateAPIView):
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
        return queryset.select_related("cultivation_guide").order_by(*sort_fields.get(sort, sort_fields["name"]))


class PlantDetailAPIView(PlantAPIMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Plant.objects.all()
