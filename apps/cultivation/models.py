from django.core.validators import MinValueValidator
from django.db import models

from apps.plants.models import Plant


WATERING_FREQUENCY_CHOICES = [
    ("daily", "Setiap hari"),
    ("every_2_3_days", "2-3 hari sekali"),
    ("weekly", "Seminggu sekali"),
    ("biweekly", "Dua minggu sekali"),
    ("when_dry", "Saat media bagian atas kering"),
]

FERTILIZING_FREQUENCY_CHOICES = [
    ("weekly", "Seminggu sekali"),
    ("biweekly", "Dua minggu sekali"),
    ("monthly", "Sebulan sekali"),
    ("every_3_months", "Tiga bulan sekali"),
    ("as_needed", "Sesuai fase tumbuh"),
    ("none", "Tidak perlu rutin"),
]


def format_days(days):
    if days > 365:
        return f"{round(days / 365, 1):g} tahun"
    return f"{days} hari"


class CultivationGuide(models.Model):
    plant = models.OneToOneField(
        Plant,
        on_delete=models.CASCADE,
        related_name="cultivation_guide",
    )
    planting_steps = models.TextField()
    watering_frequency = models.CharField(
        max_length=20,
        choices=WATERING_FREQUENCY_CHOICES,
        default="when_dry",
    )
    watering_note = models.TextField(blank=True)
    fertilizing_frequency = models.CharField(
        max_length=20,
        choices=FERTILIZING_FREQUENCY_CHOICES,
        default="as_needed",
    )
    fertilizing_note = models.TextField(blank=True)
    is_harvestable = models.BooleanField(default=True)
    harvest_days_min = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    harvest_days_max = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    harvest_note = models.TextField(blank=True)
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Panduan {self.plant.name}"

    @property
    def step_list(self):
        return [line.strip() for line in self.planting_steps.splitlines() if line.strip()]

    @property
    def harvest_label(self):
        if not self.is_harvestable:
            return "Tidak ada waktu panen"
        minimum, maximum = self.harvest_days_min, self.harvest_days_max
        if minimum and maximum and minimum != maximum:
            if maximum <= 365:
                return f"{minimum}-{maximum} hari setelah tanam"
            return f"{format_days(minimum)}-{format_days(maximum)} setelah tanam"
        if minimum or maximum:
            return f"Sekitar {format_days(minimum or maximum)} setelah tanam"
        return "Lihat catatan panen"