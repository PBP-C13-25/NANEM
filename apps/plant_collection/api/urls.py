from django.urls import path

from . import views

app_name = "collection_api"

urlpatterns = [
    path("collections/", views.CollectionListCreateAPIView.as_view(), name="list"), # GET, POST
    path("collections/<int:pk>/", views.CollectionDetailAPIView.as_view(), name="detail"), # GET, PATCH, DELETE
    path("collections/<int:pk>/like/", views.ToggleLikeAPIView.as_view(), name="like") # POST
]  