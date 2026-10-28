from django.db.models import Q
from django.views.generic import ListView

from apps.core.mixins import ActiveUserRequiredMixin

from .models import Plant


SUNLIGHT_LABELS = {
    "full_sun": "Matahari penuh",
    "partial_shade": "Teduh sebagian",
    "shade": "Teduh",
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
