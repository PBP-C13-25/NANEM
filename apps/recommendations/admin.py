from django.contrib import admin
from .models import RecommendationHistory

# Register your models here.
@admin.register(RecommendationHistory)
class RecommendationHistoryAdmin(admin.ModelAdmin):
    list_display = ("land_name", "user", "planting_medium", "land_area", "created_at")
    readonly_fields = ("environment_snapshot", "recommended_plants", "created_at")