"""Routes used only by authorization tests, never by the application."""
from django.contrib.admin.models import LogEntry
from django.http import HttpResponse
from django.urls import include, path
from django.views import View
from django.views.generic import ListView

from apps.core.mixins import (
    ActiveUserRequiredMixin,
    AdminRequiredMixin,
    OwnedQuerysetMixin,
    RegularUserRequiredMixin,
)


class UserView(ActiveUserRequiredMixin, View):
    def get(self, request):
        return HttpResponse("Authenticated")


class RegularView(RegularUserRequiredMixin, UserView):
    pass


class AdminView(AdminRequiredMixin, UserView):
    pass


class OwnedView(ActiveUserRequiredMixin, OwnedQuerysetMixin, ListView):
    model = LogEntry

    def render_to_response(self, context, **response_kwargs):
        return HttpResponse("".join(f"[{obj.pk}]" for obj in context["object_list"]))


urlpatterns = [
    path("", include("config.urls")),
    path("user/", UserView.as_view()),
    path("regular/", RegularView.as_view()),
    path("adminonly/", AdminView.as_view()),
    path("owned/", OwnedView.as_view()),
]
