"""Pembatas jumlah request per aksi (generic rate limit) berbasis cache Django.

Pola & struktur sengaja disamain sama throttle.py (anti brute-force login) --
bedanya di sini bisa dipakai buat aksi apapun (bukan cuma login), dan kuncinya
beda per `action` + per user/IP, bukan per username yang mau login.
"""
import hashlib

from django.core.cache import cache


def _key(request, action: str) -> str:
    # User login pakai user id (lebih akurat), guest pakai REMOTE_ADDR
    # (bukan X-Forwarded-For yang bisa dipalsukan).
    identity = (
        str(request.user.pk)
        if request.user.is_authenticated
        else request.META.get("REMOTE_ADDR", "")
    )
    raw = f"{action}|{identity}"
    return "ratelimit:" + hashlib.sha256(raw.encode()).hexdigest()


def is_rate_limited(request, action: str, max_attempts: int) -> bool:
    return cache.get(_key(request, action), 0) >= max_attempts


def hit(request, action: str, window_seconds: int) -> None:
    key = _key(request, action)
    # add() hanya set kalau belum ada -> window mulai dari request pertama
    cache.add(key, 0, window_seconds)
    try:
        cache.incr(key)
    except ValueError:  # key expired di antara add() dan incr()
        cache.set(key, 1, window_seconds)