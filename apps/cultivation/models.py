from django.db import models

from apps.plants.models import Plant


class CultivationGuide(models.Model):
    plant = models.OneToOneField(
        Plant,
        on_delete=models.CASCADE,
        related_name="cultivation_guide",
    )
    planting_steps = models.TextField()
    watering_frequency = models.TextField()
    fertilizing = models.TextField()
    harvest_time = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Panduan {self.plant.name}"

    @property
    def step_list(self):
        return [line.strip() for line in self.planting_steps.splitlines() if line.strip()]