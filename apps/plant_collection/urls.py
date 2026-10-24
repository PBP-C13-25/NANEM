from . import views
from django.urls import path

from . import views

app_name = "collection"

urlpatterns = [
    path("", views.collection_page, name="index"),
    path("create/", views.plant_create, name="plant_create"),
    path("plants/<int:pk>/", views.plant_detail, name="plant_detail"),
    path("plants/<int:pk>/update/", views.plant_update, name="plant_update"),
    path("plants/<int:pk>/delete/", views.plant_delete, name="plant_delete"),
    path("plants/<int:pk>/comment/", views.add_comment, name="add_comment"),
]

