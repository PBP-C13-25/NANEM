from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.SecureLoginView.as_view(), name="login"),
    path("logout/", views.SecureLogoutView.as_view(), name="logout"),
    path("password/", views.ChangePasswordView.as_view(), name="password_change"),
]