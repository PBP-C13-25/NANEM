from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.mixins import ActiveUserRequiredMixin, AdminRequiredMixin

from .forms import PlantForm
from .models import Plant


SUNLIGHT_LABELS = {
    "full_sun": "Matahari penuh",
    "partial_shade": "Teduh sebagian",
    "shade": "Teduh",
}

PLANT_COMPLETENESS_FIELDS = {
    "scientific_name": "nama ilmiah",
    "description": "deskripsi",
    "image_url": "gambar",
    "temp_min": "suhu minimum",
    "temp_max": "suhu maksimum",
    "humidity_min": "kelembapan minimum",
    "humidity_max": "kelembapan maksimum",
    "rainfall_min": "curah hujan minimum",
    "rainfall_max": "curah hujan maksimum",
    "sunlight": "cahaya",
    "watering": "kebutuhan air",
    "care_level": "tingkat perawatan",
    "drought_tolerant": "toleransi kekeringan",
    "indoor": "dukungan indoor",
    "space_needed": "kebutuhan ruang",
}


def prepare_plant_display(plant):
    media = []
    if plant.supports_soil:
        media.append("Tanah")
    if plant.supports_hydroponic:
        media.append("Hidroponik")
    plant.media_label = ", ".join(media) or "Belum ditentukan"
    plant.sunlight_label = ", ".join(
        SUNLIGHT_LABELS.get(value, value.replace("_", " ").title())
        for value in (plant.sunlight or [])
    ) or "Belum ditentukan"
    return plant


def get_missing_plant_fields(plant):
    missing = []
    for field_name, label in PLANT_COMPLETENESS_FIELDS.items():
        value = getattr(plant, field_name)
        if value is None or value == "" or value == []:
            missing.append(label)
    if not (plant.supports_soil or plant.supports_hydroponic):
        missing.append("media tanam")
    return missing


def prepare_plant_manage_display(plant):
    prepare_plant_display(plant)
    plant.missing_fields = get_missing_plant_fields(plant)
    plant.data_status = "incomplete" if plant.missing_fields else "complete"
    plant.data_status_label = (
        f"Kurang {len(plant.missing_fields)} field"
        if plant.missing_fields
        else "Lengkap"
    )
    return plant


class PlantCatalogView(ActiveUserRequiredMixin, ListView):
    model = Plant
    template_name = "plants/catalog.html"
    context_object_name = "plants"
    paginate_by = 6

    def get_queryset(self):
        queryset = Plant.objects.all()
        self.filters = {
            "q": self.request.GET.get("q", "").strip(),
            "category": self.request.GET.get("category", "").strip(),
            "medium": self.request.GET.get("medium", "").strip(),
            "sunlight": self.request.GET.get("sunlight", "").strip(),
            "space": self.request.GET.get("space", "").strip(),
            "sort": self.request.GET.get("sort", "name").strip(),
        }

        if self.filters["q"]:
            queryset = queryset.filter(
                Q(name__icontains=self.filters["q"])
                | Q(scientific_name__icontains=self.filters["q"])
            )

        categories = dict(Plant.CATEGORY_CHOICES)
        if self.filters["category"] in categories:
            queryset = queryset.filter(category=self.filters["category"])
        else:
            self.filters["category"] = ""

        if self.filters["medium"] == "soil":
            queryset = queryset.filter(supports_soil=True)
        elif self.filters["medium"] == "hydroponic":
            queryset = queryset.filter(supports_hydroponic=True)
        else:
            self.filters["medium"] = ""

        if self.filters["sunlight"] in SUNLIGHT_LABELS:
            matching_ids = [
                plant.pk
                for plant in queryset.only("pk", "sunlight")
                if self.filters["sunlight"] in (plant.sunlight or [])
            ]
            queryset = queryset.filter(pk__in=matching_ids)
        else:
            self.filters["sunlight"] = ""

        spaces = dict(Plant.SPACE_NEEDED_CHOICES)
        if self.filters["space"] in spaces:
            queryset = queryset.filter(space_needed=self.filters["space"])
        else:
            self.filters["space"] = ""

        sort_fields = {"name": "name", "name_desc": "-name", "category": "category"}
        if self.filters["sort"] not in sort_fields:
            self.filters["sort"] = "name"
        return queryset.order_by(sort_fields[self.filters["sort"]], "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for plant in context["plants"]:
            prepare_plant_display(plant)

        query = self.request.GET.copy()
        query.pop("page", None)
        context.update(
            filters=self.filters,
            category_choices=Plant.CATEGORY_CHOICES,
            sunlight_choices=SUNLIGHT_LABELS.items(),
            space_choices=Plant.SPACE_NEEDED_CHOICES,
            query_string=query.urlencode(),
        )
        return context


class PlantManageListView(AdminRequiredMixin, ListView):
    model = Plant
    template_name = "plants/manage_list.html"
    context_object_name = "plants"
    paginate_by = 10

    def get_queryset(self):
        queryset = Plant.objects.all()
        self.filters = {
            "q": self.request.GET.get("q", "").strip(),
            "category": self.request.GET.get("category", "").strip(),
            "medium": self.request.GET.get("medium", "").strip(),
            "status": self.request.GET.get("status", "").strip(),
            "sort": self.request.GET.get("sort", "name").strip(),
        }

        if self.filters["q"]:
            queryset = queryset.filter(
                Q(name__icontains=self.filters["q"])
                | Q(scientific_name__icontains=self.filters["q"])
            )

        categories = dict(Plant.CATEGORY_CHOICES)
        if self.filters["category"] in categories:
            queryset = queryset.filter(category=self.filters["category"])
        else:
            self.filters["category"] = ""

        if self.filters["medium"] == "soil":
            queryset = queryset.filter(supports_soil=True)
        elif self.filters["medium"] == "hydroponic":
            queryset = queryset.filter(supports_hydroponic=True)
        else:
            self.filters["medium"] = ""

        if self.filters["status"] in {"complete", "incomplete"}:
            matching_ids = [
                plant.pk
                for plant in queryset
                if bool(get_missing_plant_fields(plant))
                == (self.filters["status"] == "incomplete")
            ]
            queryset = queryset.filter(pk__in=matching_ids)
        else:
            self.filters["status"] = ""

        sort_fields = {
            "name": ("name", "pk"),
            "name_desc": ("-name", "pk"),
            "category": ("category", "name", "pk"),
            "updated": ("-updated_at", "name", "pk"),
        }
        if self.filters["sort"] not in sort_fields:
            self.filters["sort"] = "name"
        return queryset.order_by(*sort_fields[self.filters["sort"]])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for plant in context["plants"]:
            prepare_plant_manage_display(plant)

        all_plants = list(Plant.objects.all())
        complete_count = sum(
            not get_missing_plant_fields(plant) for plant in all_plants
        )
        query = self.request.GET.copy()
        query.pop("page", None)
        context.update(
            filters=self.filters,
            category_choices=Plant.CATEGORY_CHOICES,
            total_count=len(all_plants),
            complete_count=complete_count,
            incomplete_count=len(all_plants) - complete_count,
            query_string=query.urlencode(),
        )
        return context


class PlantCreateView(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = Plant
    form_class = PlantForm
    template_name = "plants/plant_form.html"
    success_url = reverse_lazy("plants:manage")
    success_message = "Tanaman %(name)s berhasil ditambahkan."


class PlantUpdateView(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Plant
    form_class = PlantForm
    template_name = "plants/plant_form.html"
    success_url = reverse_lazy("plants:manage")
    success_message = "Data %(name)s berhasil diperbarui."


class PlantDeleteView(AdminRequiredMixin, DeleteView):
    model = Plant
    template_name = "plants/plant_confirm_delete.html"
    success_url = reverse_lazy("plants:manage")

    def form_valid(self, form):
        plant_name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f"Tanaman {plant_name} berhasil dihapus.")
        return response
