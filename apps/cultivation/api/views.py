from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.plants.models import Plant

from ..forms import CultivationGuideForm
from ..models import CultivationGuide
from .serializers import GuideListItemSerializer, GuideSerializer


def _form_errors(form):
    return {
        field: [error["message"] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }


def _form_data(request, guide=None):
    data = {}
    if guide is not None:
        data = {field: getattr(guide, field) for field in CultivationGuideForm.Meta.fields}
    for key in request.data:
        data[key] = request.data.get(key)
    steps = data.get("planting_steps")
    if isinstance(steps, (list, tuple)):
        data["planting_steps"] = "\n".join(str(step) for step in steps)
    return data


class GuideDetailAPIView(APIView):
    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get(self, request, plant_id):
        plant = get_object_or_404(Plant, pk=plant_id)
        guide = CultivationGuide.objects.filter(plant=plant).first()
        return Response(
            {
                "plant": {"id": plant.pk, "name": plant.name},
                "guide": GuideSerializer(guide).data if guide else None,
            }
        )

    def post(self, request, plant_id):
        plant = get_object_or_404(Plant, pk=plant_id)
        if CultivationGuide.objects.filter(plant=plant).exists():
            return Response(
                {"detail": "Panduan untuk tanaman ini sudah ada. Gunakan PATCH untuk mengubahnya."},
                status=status.HTTP_409_CONFLICT,
            )
        form = CultivationGuideForm(data=_form_data(request))
        if not form.is_valid():
            return Response({"errors": _form_errors(form)}, status=status.HTTP_400_BAD_REQUEST)
        form.instance.plant = plant
        guide = form.save()
        return Response({"guide": GuideSerializer(guide).data}, status=status.HTTP_201_CREATED)

    def patch(self, request, plant_id):
        guide = get_object_or_404(CultivationGuide, plant_id=plant_id)
        form = CultivationGuideForm(data=_form_data(request, guide), instance=guide)
        if not form.is_valid():
            return Response({"errors": _form_errors(form)}, status=status.HTTP_400_BAD_REQUEST)
        guide = form.save()
        return Response({"guide": GuideSerializer(guide).data})

    def put(self, request, plant_id):
        return self.patch(request, plant_id)

    def delete(self, request, plant_id):
        guide = get_object_or_404(CultivationGuide, plant_id=plant_id)
        guide.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GuideListAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        plants = Plant.objects.select_related("cultivation_guide").order_by("name", "pk")

        query = request.query_params.get("q", "").strip()
        if query:
            plants = plants.filter(
                Q(name__icontains=query) | Q(scientific_name__icontains=query)
            )

        status_filter = request.query_params.get("status", "").strip()
        if status_filter == "ada":
            plants = plants.filter(cultivation_guide__isnull=False)
        elif status_filter == "belum":
            plants = plants.filter(cultivation_guide__isnull=True)

        total = Plant.objects.count()
        with_guide = CultivationGuide.objects.count()
        return Response(
            {
                "summary": {
                    "total": total,
                    "with_guide": with_guide,
                    "without_guide": total - with_guide,
                },
                "plants": GuideListItemSerializer(plants, many=True).data,
            }
        )