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
from django.urls import re_path
from django.views.static import serve
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


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

<<<<<<< HEAD

    # API PATH
    path("api/", include("apps.accounts.api.urls")),
    path("api/", include("apps.recommendations.api.urls")),
    path("api/", include("apps.plant_collection.api.urls")),
=======
    # API PATH
    path("api/", include("apps.accounts.api.urls")),
    path("api/", include("apps.recommendations.api.urls")),
    path("api/", include("apps.plant_collection.api.urls")) 

>>>>>>> 799ea0d55f9a521507aadab7ce89857cdd75d03c
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
