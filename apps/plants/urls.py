from django.urls import path

from . import views


app_name = "plants"

urlpatterns = [
    path("", views.PlantCatalogView.as_view(), name="index"),
    path("manage/", views.PlantManageListView.as_view(), name="manage"),
    path("manage/add/", views.PlantCreateView.as_view(), name="create"),
    path(
        "manage/<int:pk>/edit/",
        views.PlantUpdateView.as_view(),
        name="update",
    ),
    path(
        "manage/<int:pk>/delete/",
        views.PlantDeleteView.as_view(),
        name="delete",
    ),
]
