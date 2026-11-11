"""Pengaturan bersama untuk API (Django REST Framework) yang dipakai aplikasi mobile.

Autentikasi API memakai SESSION yang sama dengan web: login sekali, lalu
cookie `sessionid` dikirim di setiap request. Dengan begitu alur API bisa
sama persis dengan web (misalnya hasil rekomendasi dititipkan di session
sebelum disimpan ke riwayat).
"""
from rest_framework.authentication import SessionAuthentication


class MobileSessionAuthentication(SessionAuthentication):
    """Session auth untuk aplikasi mobile.

    1. Tanpa pengecekan CSRF.
       CSRF adalah serangan lewat BROWSER korban (situs lain diam-diam mengirim
       form ke NANEM memakai cookie korban). Aplikasi Flutter bukan browser,
       dan tidak bisa mengirim header Referer/Origin yang diminta pengecekan
       CSRF Django di HTTPS. Untuk browser, perlindungan tetap ada karena
       cookie sesi memakai SESSION_COOKIE_SAMESITE = "Lax": browser tidak
       mengirim cookie itu pada POST dari situs lain. Halaman web biasa
       (bukan /api/) tetap memakai CSRF seperti sebelumnya.

    2. Guest yang belum login mendapat 401, bukan 403.
       SessionAuthentication bawaan tidak punya `authenticate_header`, jadi DRF
       menjawab 403 untuk guest. Dengan method ini, DRF menjawab 401
       ("belum login"), dan 403 tetap berarti "sudah login tapi tidak berhak".
    """

    def enforce_csrf(self, request):
        return

    def authenticate_header(self, request):
        return "Session"
