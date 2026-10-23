from django.urls import path

from . import views


app_name = "plants"

urlpatterns = [
    path("", views.PlantCatalogView.as_view(), name="index"),
    path("<int:pk>/", views.PlantDetailView.as_view(), name="detail"),
]
