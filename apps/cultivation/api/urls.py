from django.urls import path

from . import views

app_name = "cultivation_api"

urlpatterns = [
    path("plants/<int:plant_id>/guide/", views.GuideDetailAPIView.as_view(), name="guide"),
    path("guides/", views.GuideListAPIView.as_view(), name="guide_list"),
]
