"""Pembatas percobaan login (anti brute-force) berbasis cache Django."""
import hashlib

from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _key(request, username: str) -> str:
    # REMOTE_ADDR sengaja dipakai (bukan X-Forwarded-For yang bisa dipalsukan).
    # Kalau di belakang reverse proxy, atur proxy/WSGI agar REMOTE_ADDR benar.
    ip = request.META.get("REMOTE_ADDR", "")
    raw = f"{ip}|{(username or '').strip().lower()}"
    return "login_fail:" + hashlib.sha256(raw.encode()).hexdigest()


def is_locked(request, username: str) -> bool:
    return cache.get(_key(request, username), 0) >= MAX_ATTEMPTS


def register_failure(request, username: str) -> None:
    key = _key(request, username)
    # add() hanya set kalau belum ada -> window lockout mulai dari kegagalan pertama
    cache.add(key, 0, LOCKOUT_SECONDS)
    try:
        cache.incr(key)
    except ValueError:  # key expired di antara add() dan incr()
        cache.set(key, 1, LOCKOUT_SECONDS)


def reset(request, username: str) -> None:
    cache.delete(_key(request, username))