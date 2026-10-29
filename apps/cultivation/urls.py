from django.urls import path

from . import views

app_name = "cultivation"

urlpatterns = [
    path("", views.GuideListView.as_view(), name="index"),
    path("kelola/", views.GuideManageView.as_view(), name="kelola_panduan"),
    path("<int:plant_id>/", views.GuideDetailView.as_view(), name="detail"),
    path("<int:plant_id>/tambah/", views.GuideCreateView.as_view(), name="create"),
    path("<int:plant_id>/edit/", views.GuideUpdateView.as_view(), name="update"),
    path("<int:plant_id>/hapus/", views.GuideDeleteView.as_view(), name="delete"),
]