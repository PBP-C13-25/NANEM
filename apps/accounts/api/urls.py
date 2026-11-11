from django.urls import path

from . import views

app_name = "accounts_api"

urlpatterns = [
    path("auth/register/", views.RegisterAPIView.as_view(), name="register"),
    path("auth/login/", views.LoginAPIView.as_view(), name="login"),
    path("auth/logout/", views.LogoutAPIView.as_view(), name="logout"),
    path("auth/me/", views.MeAPIView.as_view(), name="me"),
    path("auth/password/", views.ChangePasswordAPIView.as_view(), name="password_change"),
]
