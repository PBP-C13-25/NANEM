from django.urls import path
from .views import (
    ProfileDetailView,
    ProfileEditView,
    DeleteAccountView,
    SearchUsersView,
    PublicProfileView,
    api_get_profile,
    api_edit_profile,
    api_delete_account,
    api_search_users,
    api_get_public_profile,
)

app_name = 'profiles'

urlpatterns = [
    # Web HTML Views
    path('', ProfileDetailView.as_view(), name='profile'),
    path('edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('search/', SearchUsersView.as_view(), name='search'),

    # API DRF Endpoints untuk Mobile
    path('api/profile/', api_get_profile, name='api_get_profile'),
    path('api/profile/edit/', api_edit_profile, name='api_edit_profile'),
    path('api/profile/delete/', api_delete_account, name='api_delete_account'),
    path('api/profile/search/', api_search_users, name='api_search_users'),
    path('api/profile/<str:username>/', api_get_public_profile, name='api_get_public_profile'),

    # Public Profile Web View
    path('<str:username>/', PublicProfileView.as_view(), name='public_profile'),
]