from django.urls import path

from apps.cultivation.views import landing_page, kelola_panduan

app_name = "cultivation"

urlpatterns = [
    path("", landing_page, name="landing_page"),
    path("kelola/", kelola_panduan, name="kelola_panduan"),
]