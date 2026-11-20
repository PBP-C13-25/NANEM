"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.profiles.views import (
    api_delete_account,
    api_edit_profile,
    api_get_profile,
    api_get_public_profile,
    api_search_users,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path('accounts/', include("apps.accounts.urls")),
    path("profile/", include("apps.profiles.urls")),
    path("collection/", include("apps.plant_collection.urls")),
    path("catalog/", include("apps.plants.urls")),
    path("recommendation/", include("apps.recommendations.urls")),
    path("cultivation/", include("apps.cultivation.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),

    # API PATH
    path("api/", include("apps.accounts.api.urls")),
    path("api/", include("apps.recommendations.api.urls")),
    path("api/profile/", api_get_profile, name="api_get_profile"),
    path("api/profile/edit/", api_edit_profile, name="api_edit_profile"),
    path("api/profile/delete/", api_delete_account, name="api_delete_account"),
    path("api/profile/search/", api_search_users, name="api_search_users"),
    path("api/profile/<str:username>/", api_get_public_profile, name="api_get_public_profile"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)