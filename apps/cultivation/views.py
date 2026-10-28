from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.core.mixins import ActiveUserRequiredMixin, AdminRequiredMixin
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
        context["plant"] = prepare_plant_display(self.get_plant())
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