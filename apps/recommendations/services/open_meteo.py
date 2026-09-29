"""
Nilainya RATA-RATA dari ~90 hari terakhir + hari ini, 
supaya mencerminkan musim yang sedang berjalan, 
bukan sekadar cuaca beberapa hari terakhir yang bisa saja
anomali (misal kebetulan hujan terus padahal biasanya kering).
"""

import logging
from datetime import datetime, timezone

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 8
PAST_DAYS = 90 # 3 bln
CACHE_SECONDS = 30 * 60

class OpenMeteoError(Exception):
    """Kalo gagal ngambl or baca data dari Open-Meteo."""


def _mean(values):
    values = [v for v in values if v is not None]
    if not values:
        raise OpenMeteoError("Data cuaca kosong.")
    return sum(values) / len(values)


def fetch_environment(latitude: float, longitude: float) -> dict:
    """Bakal Return {"temperature", "humidity", "rainfall", "period_days", ...}.

    Hasil di-cache biar hemat panggilan API
    """
    cache_key = f"open_meteo:{round(latitude, 2)}:{round(longitude, 2)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation",
        "past_days": PAST_DAYS,
        "forecast_days": 1,
        "timezone": "auto",
    }

    try:
        response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Open-Meteo request gagal: %s", exc)
        raise OpenMeteoError("Tidak bisa menghubungi Open-Meteo.") from exc

    if not isinstance(payload, dict) or payload.get("error"):
        raise OpenMeteoError("Open-Meteo menolak permintaan.")

    # map ke dict
    try:
        hourly = payload["hourly"]
        temps = hourly["temperature_2m"]
        humidities = hourly["relative_humidity_2m"]
        precipitation = hourly["precipitation"]
        valid_precip = [p for p in precipitation if p is not None]
        days = max(len(valid_precip) / 24, 1)
        environment = {
            "temperature": round(_mean(temps), 1),
            "humidity": round(_mean(humidities), 1),
            "rainfall": round(sum(valid_precip) / days, 1), # curah hujan per hari = total hujan / jumlah hari data
            "period_days": round(days),
            "source": "open-meteo",
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    except (KeyError, TypeError) as exc:
        logger.warning("Format respons Open-Meteo tidak sesuai: %s", exc)
        raise OpenMeteoError("Format data Open-Meteo tidak sesuai.") from exc

    cache.set(cache_key, environment, CACHE_SECONDS)
    return environment
