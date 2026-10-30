from django.urls import path
from .views import (
    ProfileDetailView, 
    ProfileEditView, 
    DeleteAccountView, 
    SearchUsersView, 
    PublicProfileView
)

app_name = 'profiles'

urlpatterns = [
    path('', ProfileDetailView.as_view(), name='profile'),
    path('edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('search/', SearchUsersView.as_view(), name='search'),
    path('<str:username>/', PublicProfileView.as_view(), name='public_profile'),
]