from django.urls import path

from . import views

app_name = "collection_api"

urlpatterns = [
    path("", views.CollectionListAPIView.as_view(), name="index"),
    path("create/", views.CollectionCreateAPIView.as_view(), name="create"),
    path("<int:pk>/", views.CollectionDetailAPIView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.CollectionUpdateAPIView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.CollectionDeleteAPIView.as_view(), name="delete"),
    path("<int:pk>/like/", views.ToggleLikeAPIView.as_view(), name="like"),
]