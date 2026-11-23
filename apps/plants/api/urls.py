from django.urls import path

from . import views

app_name = "plants_api"

urlpatterns = [
    path("plants/", views.PlantListAPIView.as_view(), name="list"),
    path("plants/<int:pk>/", views.PlantDetailAPIView.as_view(), name="detail"),
]
