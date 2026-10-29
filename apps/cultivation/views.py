from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from apps.core.mixins import ActiveUserRequiredMixin, AdminRequiredMixin
from apps.plants.forms import WATERING_CHOICES
from apps.plants.models import Plant
from apps.plants.views import prepare_plant_display

from .forms import CultivationGuideForm
from .models import CultivationGuide


class PlantMixin:
    def get_plant(self):
        if not hasattr(self, "_plant"):
            self._plant = get_object_or_404(Plant, pk=self.kwargs["plant_id"])
        return self._plant

    def get_success_url(self):
        return reverse("cultivation:detail", args=[self.get_plant().pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plant = prepare_plant_display(self.get_plant())
        plant.water_label = dict(WATERING_CHOICES).get(plant.watering) or "Belum ditentukan"
        context["plant"] = plant
        return context

class GuideListView(ActiveUserRequiredMixin, ListView):
    model = CultivationGuide
    template_name = "cultivation/list.html"
    context_object_name = "guides"
    paginate_by = 6

    def get_queryset(self):
        queryset = CultivationGuide.objects.select_related("plant")
        self.filters = {
            "q": self.request.GET.get("q", "").strip(),
            "category": self.request.GET.get("category", "").strip(),
            "medium": self.request.GET.get("medium", "").strip(),
            "sort": self.request.GET.get("sort", "name").strip(),
        }

        if self.filters["q"]:
            queryset = queryset.filter(
                Q(plant__name__icontains=self.filters["q"])
                | Q(plant__scientific_name__icontains=self.filters["q"])
            )

        if self.filters["category"] in dict(Plant.CATEGORY_CHOICES):
            queryset = queryset.filter(plant__category=self.filters["category"])
        else:
            self.filters["category"] = ""

        if self.filters["medium"] == "soil":
            queryset = queryset.filter(plant__supports_soil=True)
        elif self.filters["medium"] == "hydroponic":
            queryset = queryset.filter(plant__supports_hydroponic=True)
        else:
            self.filters["medium"] = ""

        sort_fields = {"name": "plant__name", "name_desc": "-plant__name", "newest": "-updated_at"}
        if self.filters["sort"] not in sort_fields:
            self.filters["sort"] = "name"
        return queryset.order_by(sort_fields[self.filters["sort"]], "plant__name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for guide in context["guides"]:
            prepare_plant_display(guide.plant)

        query = self.request.GET.copy()
        query.pop("page", None)
        context.update(
            filters=self.filters,
            category_choices=Plant.CATEGORY_CHOICES,
            query_string=query.urlencode(),
        )
        return context


class GuideDetailView(ActiveUserRequiredMixin, PlantMixin, TemplateView):
    template_name = "cultivation/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["guide"] = CultivationGuide.objects.filter(plant=self.get_plant()).first()
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