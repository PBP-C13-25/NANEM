from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.ProfileDetailView.as_view(), name="profile"),
    path("edit/", views.ProfileEditView.as_view(), name="profile_edit"),
]