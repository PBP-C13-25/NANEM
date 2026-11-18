from django.urls import path
from .views import (
    ProfileDetailView, 
    ProfileEditView, 
    DeleteAccountView, 
    SearchUsersView, 
    PublicProfileView,
    api_get_profile 
)

app_name = 'profiles'

urlpatterns = [
    path('', ProfileDetailView.as_view(), name='profile'),
    path('edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('search/', SearchUsersView.as_view(), name='search'),
    
    # Endpoint API DRF untuk Mobile (Pindahkan ke ATAS sebelum <str:username>)
    path('api/profile/', api_get_profile, name='api_get_profile'),
    
    path('<str:username>/', PublicProfileView.as_view(), name='public_profile'),
]