# Ini logic rule basednya
from apps.plants.models import Plant

from ..konstan import (
    CRITERIA_WEIGHTS,
    MEDIUM_HYDROPONIC,
    MEDIUM_SOIL,
    SPACE_ORDER,
    TOLERANCE_RATIO,
    land_area_to_capacity,
)

# Top 10 hasil rekomendasi (5 tampil dulu, sisanya lewat tombol "Lihat lainnya")
TOP_N = 10

# Kriteria untuk rule basedmnya
CLIMATE_CRITERIA = [
    ("temperature", "temp_min", "temp_max", "Suhu", "°C"),
    ("humidity", "humidity_min", "humidity_max", "Kelembapan", "%"),
    ("rainfall", "rainfall_min", "rainfall_max", "Curah hujan", "mm/hari"),
]

def _fmt(number):
    return f"{number:g}"

# filter tanamn berdasakn media tanamn yg user ingput
def supports_medium(plant, medium: str) -> bool:
    if medium == MEDIUM_SOIL:
        return bool(plant.supports_soil)
    if medium == MEDIUM_HYDROPONIC:
        return bool(plant.supports_hydroponic)
    return False

def fits_land_area(plant, land_area: float) -> bool:
    if plant.space_needed not in SPACE_ORDER:
        return False
    capacity = land_area_to_capacity(land_area)
    # bandingin dari index kalo lebih kecil dari yg dibutuhkan masih aman
    return SPACE_ORDER.index(plant.space_needed) <= SPACE_ORDER.index(capacity)

def _range_score(value: float, low, high) -> float:
    if low is not None and high is not None:
        if low <= value <= high:
            return 100.0
        span = high - low
        tolerance = span * TOLERANCE_RATIO if span > 0 else 1.0
        over = (low - value) if value < low else (value - high)
    else:
        bound = low if low is not None else high
        tolerance = abs(bound) * TOLERANCE_RATIO or 1.0
        if (low is not None and value >= low) or (high is not None and value <= high):
            return 100.0
        over = (low - value) if low is not None else (value - high)

    return max(0.0, 100.0 * (1 - over / tolerance))


def score_plant(plant, environment: dict):
    weighted_total = 0.0
    weight_total = 0.0
    criteria_count = 0   # kriteria yg dimiliki tanaman ini
    matched_count = 0    # count kriteria yg msh dalam rentang syarat
    reasons = []

    for key, min_field, max_field, label, unit in CLIMATE_CRITERIA:
        low = getattr(plant, min_field)
        high = getattr(plant, max_field)
        if low is None and high is None:
            continue

        criteria_count += 1
        value = environment[key]
        criterion_score = _range_score(value, low, high)
        if criterion_score >= 100:
            matched_count += 1
        weight = CRITERIA_WEIGHTS.get(key, 1)
        weighted_total += weight * criterion_score
        weight_total += weight

        if low is not None and high is not None:
            target = f"target {_fmt(low)}-{_fmt(high)} {unit}"
        elif low is not None:
            target = f"target minimal {_fmt(low)} {unit}"
        else:
            target = f"target maksimal {_fmt(high)} {unit}"
        reasons.append({
            "text": f"{label}: {round(criterion_score)}% cocok ({_fmt(value)} {unit}, "
                    f"{target})",
            "matched": criterion_score >= 100,
        })

    if weight_total == 0:
        return None

    overall = round(weighted_total / weight_total)
    return {
        "score": overall,
        "criteria_count": criteria_count,
        "matched_count": matched_count,
        "reasons": reasons,
    }

CARE_LEVEL_LABELS = {
    "low": "Mudah",
    "medium": "Sedang",
    "moderate": "Sedang",
    "high": "Sulit",
}


def _care_level_label(plant):
    """Label care_level untuk badge. Nilai di luar daftar: pakai label choices / nilai aslinya."""
    raw = (plant.care_level or "").strip()
    if not raw:
        return ""
    if raw.lower() in CARE_LEVEL_LABELS:
        return CARE_LEVEL_LABELS[raw.lower()]
    display = getattr(plant, "get_care_level_display", None)
    return display() if callable(display) else raw


def recommend(environment: dict, medium: str, land_area: float) -> list:
    """
    ini bakal return hasil rekomendasi tanaman
    """

    candidates = []

    for plant in Plant.objects.all():
        if not supports_medium(plant, medium):
            continue
        if not fits_land_area(plant, land_area):
            continue

        scored = score_plant(plant, environment)
        if scored is None:
            continue

        candidates.append(
            {
                "plant_id": plant.pk,
                "plant_name": plant.name,
                "scientific_name": plant.scientific_name,
                "match_percentage": scored["score"],
                "criteria_count": scored["criteria_count"],
                "matched_count": scored["matched_count"],
                "total_criteria": len(CLIMATE_CRITERIA),
                "reasons": scored["reasons"],
                # info tambahan untuk badge (tidak memengaruhi skor)
                "care_level": plant.care_level or "",
                "care_level_label": _care_level_label(plant),
                "indoor": plant.indoor,
                # Untuk filter
                "category": plant.category or "",
            }
        )

    candidates.sort(key=lambda c: (-c["match_percentage"], -c["matched_count"], c["plant_name"]))
    return candidates[:TOP_N]