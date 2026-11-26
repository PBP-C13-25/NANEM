from django.urls import path

from . import views

app_name = "profiles_api"

urlpatterns = [
    path("profile/", views.api_get_profile, name="profile"),
    path("profile/edit/", views.api_edit_profile, name="profile_edit"),
    path("profile/delete/", views.api_delete_account, name="profile_delete"),
    path("profile/search/", views.api_search_users, name="profile_search"),
    path("users/<str:username>/", views.api_get_public_profile, name="public_profile"),
]