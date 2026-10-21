from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView

from apps.core.mixins import OwnedQuerysetMixin, RegularUserRequiredMixin

from .konstan import MEDIUM_CHOICES, summarize_environment
from .forms import HistoryLandNameForm, RecommendationForm
from .models import RecommendationHistory
from .services.engine import recommend
from .services.open_meteo import OpenMeteoError, fetch_environment

# Create your views here.
SESSION_KEY = "recommendation_result"

def _can_save(user):
    """
    simpan history cuma bisa unutk user yg ter autentikasih
    """
    
    return user.is_authenticated and user.is_active and not user.is_staff

#* INPUT REKOMENDASI
class RecommendationFormView(FormView):
    """
    user guest bisa untuk menggunakan rekomendaso
    """
    template_name = "recommendations/index.html"
    form_class = RecommendationForm
    success_url = reverse_lazy("recommendations:result")

    def form_valid(self, form):
        data = form.cleaned_data
        latitude, longitude = data["latitude"], data["longitude"]

        try:
            environment = fetch_environment(latitude, longitude)
        except OpenMeteoError:
            form.add_error(
                None, "Data cuaca belum bisa diambil. Coba lagi beberapa saat lagi."
            )
            return self.form_invalid(form)

        plants = recommend(environment, data["planting_medium"], data["land_area"])

        self.request.session[SESSION_KEY] = {
            "land_name": data["land_name"],
            "latitude": latitude,
            "longitude": longitude,
            "land_area": data["land_area"],
            "planting_medium": data["planting_medium"],
            "environment": {
                "raw": environment,
                "summary": summarize_environment(environment),
            },
            "plants": plants,
        }
        return super().form_valid(form)

#* HASIL REKOMENDASI
class RecommendationResultView(TemplateView):
    template_name = "recommendations/result.html"

    def get(self, request, *args, **kwargs):
        if SESSION_KEY not in request.session:
            return redirect("recommendations:index")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = self.request.session[SESSION_KEY]
        context.update(
            result=result,
            medium_label=dict(MEDIUM_CHOICES)[result["planting_medium"]],
            can_save=_can_save(self.request.user),
            saved_history_id=result.get("saved_history_id"),
        )
        return context


#* SAVE HASIL REKOMENDASI
class SaveHistoryView(RegularUserRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        result = request.session.get(SESSION_KEY)
        if not result:
            messages.error(request, "Tidak ada hasil rekomendasi untuk disimpan.")
            return redirect("recommendations:index")

        saved_id = result.get("saved_history_id")
        if saved_id and RecommendationHistory.objects.filter(
            pk=saved_id, user=request.user
        ).exists():
            return redirect("recommendations:history_detail", pk=saved_id)

        history = RecommendationHistory.objects.create(
            user=request.user,
            land_name=result["land_name"],
            latitude=result["latitude"],
            longitude=result["longitude"],
            land_area=result["land_area"],
            planting_medium=result["planting_medium"],
            environment_snapshot=result["environment"],
            recommended_plants=result["plants"],
        )
        result["saved_history_id"] = history.pk
        request.session[SESSION_KEY] = result  
        messages.success(request, "Rekomendasi disimpan ke riwayat.")
        return redirect("recommendations:history_detail", pk=history.pk)

#* ALL HISTORY DATA
class HistoryListView(RegularUserRequiredMixin, OwnedQuerysetMixin, ListView):
    model = RecommendationHistory
    template_name = "recommendations/history_list.html"
    context_object_name = "histories"
    paginate_by = 10


class HistoryDetailView(RegularUserRequiredMixin, OwnedQuerysetMixin, DetailView):
    model = RecommendationHistory
    template_name = "recommendations/history_detail.html"
    context_object_name = "history"


#* UNTUK UPDATE HISTORY
# (land name only)
class HistoryUpdateView(RegularUserRequiredMixin, OwnedQuerysetMixin, UpdateView):
    model = RecommendationHistory
    form_class = HistoryLandNameForm
    template_name = "recommendations/history_update.html"
    context_object_name = "history"

    def get_success_url(self):
        next_url = self.request.POST.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_url
        return reverse("recommendations:history_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Nama lahan diperbarui.")
        return super().form_valid(form)


#* DELETE HISTORY
class HistoryDeleteView(RegularUserRequiredMixin, OwnedQuerysetMixin, DeleteView):
    model = RecommendationHistory
    template_name = "recommendations/history_confirm_delete.html"
    context_object_name = "history"
    success_url = reverse_lazy("recommendations:history_list")

    def form_valid(self, form):
        messages.success(self.request, "Riwayat dihapus.")
        return super().form_valid(form)
