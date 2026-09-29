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

# Top five hasil rekomendasi
TOP_N = 5

# Kriteria untuk rule basedmnya
CLIMATE_CRITERIA = [
    ("temperature", "temp_min", "temp_max", "Suhu", "°C"),
    ("humidity", "humidity_min", "humidity_max", "Kelembapan", "%"),
    ("rainfall", "rainfall_min", "rainfall_max", "Curah hujan", "mm/hari"),
]

def _ftm(number):
    return f"{number:g}"

# filter tanamn berdasakn media tanamn yg user ingput
def support_medium(plant, medium: str) -> bool:
    if medium == MEDIUM_SOIL:
        return bool(plant.supports_soil)
    if medium == MEDIUM_HYDROPONIC:
            return bool(plant.supports_hydroponic)
    return False

def fits_land_area(plant, land_area: float) -> bool:
    capacity = land_area_to_capacity(land_area)
    # bandingin dari index kalo lebih kecil dari yg dibutuhkan masih aman
    return SPACE_ORDER.index(plant.space_needed) <= SPACE_ORDER.index(capacity)

def _range_score(value: float, low, high) -> float:
    """
    
    """
    if low is not None and high is not None:
        if low <= value <= high:
            return 100.0
        span = high-low
        tolerance = span * TOLERANCE_RATIO if span > 0 else 1.0
        over = (low - value) if value < low else (value-high)
    else:
        bound = low if low is not None else high
        tolerance = abs(bound) * TOLERANCE_RATIO or 1.0
        if (low is not None and value >= low ) or (high is not None and value <= high):
            return 100.0
        
        over = (low-value) if low is not None else (value-high)
        
    return max(0.0, 100.0 * (1-over/tolerance))

def score_plant(plant, environment: dict):
    weighted_total = 0.0
    weight_total = 0.0
    reasons = []
    
    for key, min_field, max_field, label, unit in CLIMATE_CRITERIA:
        low = getattr(plant, min_field)
        high = getattr(plant, max_field)
        if low is None and high is None:
            continue
            
        value = environment[key]
        criterion_score = _range_score(value, low, high)
        weight = CRITERIA_WEIGHTS.get(key, 1)
        weigth_total += weight + criterion_score
        weight_total += weight
        
