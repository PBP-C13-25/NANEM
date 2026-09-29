from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .konstan import MEDIUM_CHOICES

# Create your models here.
class RecommendationHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendation_histories",
    )
    land_name = models.CharField(max_length=100)
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    land_area = models.FloatField(
        help_text="Luas lahan dalam meter persegi (m2).",
        validators=[MinValueValidator(0.01)],
    )
    planting_medium = models.CharField(max_length=20, choices=MEDIUM_CHOICES)

    environment_snapshot = models.JSONField(default=dict)
    recommended_plants = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "recommendation histories"

    def __str__(self):
        return f"{self.land_name} ({self.user})"
