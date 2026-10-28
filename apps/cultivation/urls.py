from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "cultivation"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="plants:index"), name="index"),
    path("<int:plant_id>/", views.GuideDetailView.as_view(), name="detail"),
    path("<int:plant_id>/tambah/", views.GuideCreateView.as_view(), name="create"),
    path("<int:plant_id>/edit/", views.GuideUpdateView.as_view(), name="update"),
    path("<int:plant_id>/hapus/", views.GuideDeleteView.as_view(), name="delete"),
]