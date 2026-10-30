from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from apps.core.mixins import ActiveUserRequiredMixin, AdminRequiredMixin
from apps.plants.forms import CARE_LEVEL_CHOICES, WATERING_CHOICES
from apps.plants.models import Plant
from apps.plants.views import prepare_plant_display

from .forms import CultivationGuideForm
from .models import CultivationGuide

NOT_SET = "Belum ditentukan"


def format_number(value):
    return f"{value:g}".replace(".", ",")


def format_range(minimum, maximum, unit):
    if minimum is not None and maximum is not None:
        return f"{format_number(minimum)}-{format_number(maximum)} {unit}"
    if minimum is not None:
        return f"Minimal {format_number(minimum)} {unit}"
    if maximum is not None:
        return f"Maksimal {format_number(maximum)} {unit}"
    return NOT_SET


def format_yes_no(value):
    if value is None:
        return "Belum diketahui"
    return "Ya" if value else "Tidak"


def build_plant_facts(plant):
    return [
        ("Media", plant.media_label),
        ("Cahaya", plant.sunlight_label),
        ("Ruang", plant.get_space_needed_display()),
        ("Kebutuhan air", dict(WATERING_CHOICES).get(plant.watering) or NOT_SET),
        ("Tingkat perawatan", dict(CARE_LEVEL_CHOICES).get(plant.care_level) or NOT_SET),
        ("Tahan kekeringan", format_yes_no(plant.drought_tolerant)),
        ("Suhu", format_range(plant.temp_min, plant.temp_max, "°C")),
        ("Kelembapan", format_range(plant.humidity_min, plant.humidity_max, "%")),
        ("Curah hujan", format_range(plant.rainfall_min, plant.rainfall_max, "mm/hari")),
    ]

class PlantMixin:
    def get_plant(self):
        if not hasattr(self, "_plant"):
            self._plant = get_object_or_404(Plant, pk=self.kwargs["plant_id"])
        return self._plant

    def get_success_url(self):
        return reverse("cultivation:detail", args=[self.get_plant().pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plant"] = prepare_plant_display(self.get_plant())
        return context


class GuideManageView(AdminRequiredMixin, ListView):
    model = Plant
    template_name = "cultivation/kelola.html"
    context_object_name = "plants"
    paginate_by = 10

    def get_queryset(self):
        queryset = Plant.objects.select_related("cultivation_guide")
        self.filters = {
            "q": self.request.GET.get("q", "").strip(),
            "category": self.request.GET.get("category", "").strip(),
            "status": self.request.GET.get("status", "").strip(),
        }

        if self.filters["q"]:
            queryset = queryset.filter(
                Q(name__icontains=self.filters["q"])
                | Q(scientific_name__icontains=self.filters["q"])
            )

        if self.filters["category"] in dict(Plant.CATEGORY_CHOICES):
            queryset = queryset.filter(category=self.filters["category"])
        else:
            self.filters["category"] = ""

        if self.filters["status"] == "ada":
            queryset = queryset.filter(cultivation_guide__isnull=False)
        elif self.filters["status"] == "belum":
            queryset = queryset.filter(cultivation_guide__isnull=True)
        else:
            self.filters["status"] = ""

        return queryset.order_by("name", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        query.pop("page", None)
        total = Plant.objects.count()
        with_guide = CultivationGuide.objects.count()
        context.update(
            filters=self.filters,
            category_choices=Plant.CATEGORY_CHOICES,
            query_string=query.urlencode(),
            total_count=total,
            with_guide_count=with_guide,
            without_guide_count=total - with_guide,
        )
        return context


class GuideDetailView(ActiveUserRequiredMixin, PlantMixin, TemplateView):
    template_name = "cultivation/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["guide"] = CultivationGuide.objects.filter(plant=self.get_plant()).first()
        context["facts"] = build_plant_facts(context["plant"])
        return context


class GuideCreateView(AdminRequiredMixin, PlantMixin, CreateView):
    model = CultivationGuide
    form_class = CultivationGuideForm
    template_name = "cultivation/form.html"

    def redirect_if_exists(self):
        plant = self.get_plant()
        if CultivationGuide.objects.filter(plant=plant).exists():
            messages.info(self.request, f"Panduan {plant.name} sudah ada, silakan edit.")
            return redirect("cultivation:update", plant_id=plant.pk)
        return None

    def get(self, request, *args, **kwargs):
        return self.redirect_if_exists() or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.redirect_if_exists() or super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.plant = self.get_plant()
        response = super().form_valid(form)
        messages.success(self.request, f"Panduan {self.get_plant().name} berhasil ditambahkan.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class GuideUpdateView(AdminRequiredMixin, PlantMixin, UpdateView):
    model = CultivationGuide
    form_class = CultivationGuideForm
    template_name = "cultivation/form.html"

    def get_object(self, queryset=None):
        return get_object_or_404(CultivationGuide, plant_id=self.kwargs["plant_id"])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Panduan {self.get_plant().name} berhasil diperbarui.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context


class GuideDeleteView(AdminRequiredMixin, PlantMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        guide = get_object_or_404(CultivationGuide, plant_id=kwargs["plant_id"])
        plant_name = guide.plant.name
        guide.delete()
        messages.success(request, f"Panduan {plant_name} berhasil dihapus.")
        return redirect(self.get_success_url())