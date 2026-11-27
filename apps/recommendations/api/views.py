"""API (Django REST Framework) untuk modul Rekomendasi & Riwayat.

Alurnya SENGAJA dibuat sama dengan view web di ../views.py:
- generate rekomendasi -> hasil dititipkan di session (SESSION_KEY yang sama);
- simpan riwayat -> mengambil hasil terakhir dari session, bukan dari klien;
- riwayat hanya bisa diakses pemiliknya (milik orang lain = 404).

Bedanya cuma bentuk jawabannya: JSON + status code, bukan HTML + redirect.

Untuk klien TOKEN (Flutter) tidak ada session yang terbawa antar request,
jadi hasil rekomendasi juga dikirim sebagai `result_token`: hasil yang
DITANDATANGANI server (django.core.signing, kunci SECRET_KEY). Saat simpan,
klien mengirim balik result_token; server memeriksa tanda tangannya, jadi isi
hasil (tanaman, cuaca) tetap tidak bisa dipalsukan klien.
"""
from django.core import signing
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
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

# result_token: ditandatangani dengan salt khusus, berlaku 1 hari.
RESULT_TOKEN_SALT = "recommendations.result"
RESULT_TOKEN_MAX_AGE = 60 * 60 * 24


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
    200 -> {"result": {...}, "can_save": bool, "result_token": "..."}
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
        # Dititipkan di session seperti web (untuk klien session), dan dikirim
        # sebagai result_token (untuk klien token). Keduanya bisa dipakai di
        # POST /api/history/.
        request.session[SESSION_KEY] = result
        result_token = signing.dumps(result, salt=RESULT_TOKEN_SALT, compress=True)

        return Response(
            {
                "result": result,
                "can_save": _can_save(request.user),
                "result_token": result_token,
            }
        )


#* DAFTAR & SIMPAN RIWAYAT (user)
class HistoryListAPIView(APIView):
    """GET  /api/history/?q=  -> {"histories": [...]}
    POST /api/history/        -> simpan hasil rekomendasi

    POST:
    - body {"result_token": "..."} (klien token/Flutter) -> hasil dari token;
    - tanpa body (klien session/web) -> hasil terakhir dari session.
    201 {"id", "created": true} | 200 {"id", "created": false} kalau hasil yang
    sama sudah tersimpan | 400 kalau tidak ada hasil / token rusak / kedaluwarsa.
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
        if "result_token" in request.data:
            return self._save_from_token(request)
        return self._save_from_session(request)

    def _save_from_token(self, request):
        try:
            result = signing.loads(
                str(request.data.get("result_token", "")),
                salt=RESULT_TOKEN_SALT,
                max_age=RESULT_TOKEN_MAX_AGE,
            )
        except signing.SignatureExpired:
            return self._token_error("Hasil rekomendasi sudah kedaluwarsa. Buat rekomendasi lagi.")
        except signing.BadSignature:
            return self._token_error("Hasil rekomendasi tidak valid.")

        # Tidak ada session untuk menandai "sudah disimpan", jadi cek riwayat
        # dengan isi yang persis sama (mencegah simpan dobel karena tombol
        # ditekan dua kali). Kalau riwayatnya dihapus, bisa disimpan lagi.
        existing = (
            RecommendationHistory.objects.filter(
                user=request.user,
                land_name=result["land_name"],
                latitude=result["latitude"],
                longitude=result["longitude"],
                land_area=result["land_area"],
                planting_medium=result["planting_medium"],
                environment_snapshot=result["environment"],
                recommended_plants=result["plants"],
            )
            .order_by("-created_at")
            .first()
        )
        if existing:
            return Response({"id": existing.pk, "created": False}, status=status.HTTP_200_OK)

        history = self._create_history(request.user, result)
        return Response({"id": history.pk, "created": True}, status=status.HTTP_201_CREATED)

    def _save_from_session(self, request):
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

        history = self._create_history(request.user, result)
        result["saved_history_id"] = history.pk
        request.session[SESSION_KEY] = result  # tandai session berubah
        return Response({"id": history.pk, "created": True}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _create_history(user, result):
        return RecommendationHistory.objects.create(
            user=user,
            land_name=result["land_name"],
            latitude=result["latitude"],
            longitude=result["longitude"],
            land_area=result["land_area"],
            planting_medium=result["planting_medium"],
            environment_snapshot=result["environment"],
            recommended_plants=result["plants"],
        )

    @staticmethod
    def _token_error(message):
        return Response(
            {"errors": {"result_token": [message]}},
            status=status.HTTP_400_BAD_REQUEST,
        )


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

    def handle_exception(self, exc):
        # Error PATCH dibungkus {"errors": {...}} seperti endpoint API lainnya.
        response = super().handle_exception(exc)
        if isinstance(exc, ValidationError):
            response.data = {"errors": response.data}
        return response

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return HistoryUpdateSerializer
        return HistoryDetailSerializer
