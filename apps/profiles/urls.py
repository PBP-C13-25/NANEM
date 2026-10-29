from django.urls import path
from .views import (
    ProfileDetailView, 
    ProfileEditView, 
    DeleteAccountView, 
    search_users, 
    PublicProfileView
)

app_name = 'profiles'

urlpatterns = [
    path('', ProfileDetailView.as_view(), name='profile'),
    path('edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('search/', search_users, name='search'),
    path('<str:username>/', PublicProfileView.as_view(), name='public_profile'),
]