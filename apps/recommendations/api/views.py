"""API (Django REST Framework) untuk modul Rekomendasi & Riwayat.

Alurnya SENGAJA dibuat sama dengan view web di ../views.py:
- generate rekomendasi -> hasil dititipkan di session (SESSION_KEY yang sama);
- simpan riwayat -> mengambil hasil terakhir dari session, bukan dari klien;
- riwayat hanya bisa diakses pemiliknya (milik orang lain = 404).

Bedanya cuma bentuk jawabannya: JSON + status code, bukan HTML + redirect.
"""
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import ratelimit

from ..forms import RecommendationForm
from ..konstan import summarize_environment
from ..models import RecommendationHistory
from ..services.engine import recommend
from ..services.open_meteo import OpenMeteoError, fetch_environment
from ..views import SESSION_KEY, _can_save
from .serializers import (
    HistoryDetailSerializer,
    HistoryListSerializer,
    HistoryUpdateSerializer,
)

# Sama dengan RecommendationFormView: maksimal 10 submit per 60 detik.
RATE_ACTION = "recommend_submit"
RATE_MAX_ATTEMPTS = 10
RATE_WINDOW_SECONDS = 60


def _form_errors(form):
    """Ubah error Django form jadi {"field": ["pesan", ...]} untuk JSON."""
    return {
        field: [error["message"] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }


#* GENERATE REKOMENDASI (guest & user)
class RecommendationAPIView(APIView):
    """POST /api/recommendations/

    Body: land_name, latitude, longitude, land_area, planting_medium.
    200 -> {"result": {...}, "can_save": bool}
    400 -> {"errors": {...}} | 429 rate limit | 503 Open-Meteo gagal
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # Validasi memakai form yang SAMA dengan web, supaya aturannya identik.
        form = RecommendationForm(data=request.data)
        if not form.is_valid():
            return Response(
                {"errors": _form_errors(form)}, status=status.HTTP_400_BAD_REQUEST
            )

        if ratelimit.is_rate_limited(request, RATE_ACTION, RATE_MAX_ATTEMPTS):
            return Response(
                {"detail": "Terlalu banyak percobaan, coba lagi sebentar lagi."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        ratelimit.hit(request, RATE_ACTION, RATE_WINDOW_SECONDS)

        data = form.cleaned_data
        try:
            environment = fetch_environment(data["latitude"], data["longitude"])
        except OpenMeteoError:
            return Response(
                {"detail": "Data cuaca belum bisa diambil. Coba lagi beberapa saat lagi."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        plants = recommend(environment, data["planting_medium"], data["land_area"])

        result = {
            "land_name": data["land_name"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "land_area": data["land_area"],
            "planting_medium": data["planting_medium"],
            "environment": {
                "raw": environment,
                "summary": summarize_environment(environment),
            },
            "plants": plants,
        }
        # Dititipkan di session seperti web, supaya bisa disimpan lewat POST /api/history/.
        request.session[SESSION_KEY] = result

        return Response({"result": result, "can_save": _can_save(request.user)})


#* DAFTAR & SIMPAN RIWAYAT (user)
class HistoryListAPIView(APIView):
    """GET  /api/history/?q=  -> {"histories": [...]}
    POST /api/history/        -> simpan hasil rekomendasi terakhir dari session
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        histories = RecommendationHistory.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        q = request.query_params.get("q", "").strip()
        if q:
            histories = histories.filter(land_name__icontains=q)

        serializer = HistoryListSerializer(histories, many=True)
        return Response({"histories": serializer.data})

    def post(self, request):
        result = request.session.get(SESSION_KEY)
        if not result:
            return Response(
                {"detail": "Tidak ada hasil rekomendasi untuk disimpan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Hasil yang sama sudah pernah disimpan -> jangan buat riwayat baru.
        saved_id = result.get("saved_history_id")
        if saved_id and RecommendationHistory.objects.filter(
            pk=saved_id, user=request.user
        ).exists():
            return Response({"id": saved_id, "created": False}, status=status.HTTP_200_OK)

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
        request.session[SESSION_KEY] = result  # tandai session berubah
        return Response({"id": history.pk, "created": True}, status=status.HTTP_201_CREATED)


#* DETAIL, UBAH NAMA LAHAN, HAPUS (pemilik)
class HistoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """GET    /api/history/<id>/  -> detail lengkap
    PATCH  /api/history/<id>/  -> {"land_name": "..."} (field lain diabaikan)
    DELETE /api/history/<id>/  -> 204
    Riwayat milik orang lain -> 404 (sama seperti OwnedQuerysetMixin di web).
    """

    permission_classes = [IsAuthenticated]
    # PUT sengaja tidak dibuka: yang boleh diubah cuma nama lahan (PATCH).
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return RecommendationHistory.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return HistoryUpdateSerializer
        return HistoryDetailSerializer
