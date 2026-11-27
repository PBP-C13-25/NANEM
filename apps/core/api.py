"""Pengaturan bersama untuk API (Django REST Framework).

API menerima DUA cara login (lihat REST_FRAMEWORK di config/settings.py):

1. Token (dipakai aplikasi Flutter, termasuk Flutter web di Chrome)
   Login lewat POST /api/auth/login/ -> dapat "token".
   Setiap request berikutnya mengirim header:  Authorization: Token <token>
   Tidak memakai cookie, jadi aman untuk CORS tanpa credentials.

2. Session (dipakai web, Browsable API, dan tes lama)
   Cookie `sessionid` yang sama dengan web, lewat MobileSessionAuthentication.

TokenAuthentication ditaruh PERTAMA, karena DRF memakai authenticate_header()
milik class pertama untuk menentukan jawaban guest: "Token" -> 401.
"""
from rest_framework.authentication import SessionAuthentication


class MobileSessionAuthentication(SessionAuthentication):
    """Session auth untuk API.

    1. Tanpa pengecekan CSRF.
       CSRF adalah serangan lewat BROWSER korban (situs lain diam-diam mengirim
       form ke NANEM memakai cookie korban). Untuk browser, perlindungan tetap
       ada karena cookie sesi memakai SESSION_COOKIE_SAMESITE = "Lax": browser
       tidak mengirim cookie itu pada POST dari situs lain, dan CORS tidak
       mengizinkan credentials. Halaman web biasa (bukan /api/) tetap memakai
       CSRF seperti sebelumnya.

    2. Guest yang belum login mendapat 401, bukan 403.
       SessionAuthentication bawaan tidak punya `authenticate_header`, jadi DRF
       menjawab 403 untuk guest. Dengan method ini, DRF menjawab 401
       ("belum login"), dan 403 tetap berarti "sudah login tapi tidak berhak".
       (Selama TokenAuthentication ada di urutan pertama, header miliknya yang
       dipakai; method ini tetap ada supaya aman kalau urutannya berubah.)
    """

    def enforce_csrf(self, request):
        return

    def authenticate_header(self, request):
        return "Session"
