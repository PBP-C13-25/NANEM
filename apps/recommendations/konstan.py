# Media tanam
MEDIUM_SOIL = "soil"
MEDIUM_HYDROPONIC = "hydroponic"

MEDIUM_CHOICES = [
    (MEDIUM_SOIL, "Tanah"),
    (MEDIUM_HYDROPONIC, "Hidroponik"),
]

# Luas lahan
SPACE_ORDER = ["small", "medium", "large"]
LAND_AREA_SMALL_MAX = 5.0   # m2
LAND_AREA_MEDIUM_MAX = 20.0 # m2
# diatas ini berati kapasitas large

def land_area_to_capacity(land_area: float) -> str:
    if land_area <= LAND_AREA_SMALL_MAX:
        return "small"
    if land_area <= LAND_AREA_MEDIUM_MAX:
        return "medium"
    return "large"

# Untuk nentuin prioritas mana yg lebih penting
CRITERIA_WEIGHTS = {
    "temperature": 1,
    "humidity": 1,
    "rainfall": 1,
}

# Tolerasi ini untuk sebarapa jauh di luar rentang [min, max] tanaman sebelum skor kriteria dia jadi 0%
# Dihitung dari persentase lebar rentang tanamn  or nilai batas kalau cuma ada satu field yg ada
TOLERANCE_RATIO = 0.2

TEMPERATURE_BANDS = [(18, "Sejuk"), (28, "Sedang"), (float("inf"), "Panas")]
HUMIDITY_BANDS = [(40, "Kering"), (70, "Sedang"), (float("inf"), "Lembap")]
RAINFALL_BANDS = [(2, "Rendah"), (6, "Sedang"), (float("inf"), "Tinggi")]

def _band_label(value: float, bands) -> str:
    for upper, label in bands:
        if value <= upper:
            return label
    return bands[-1][1]

# Ringkasan analisis lahan
def summarize_environment(environment: dict) -> dict:
    return {
        "temperature_label": _band_label(environment["temperature"], TEMPERATURE_BANDS),
        "humidity_label": _band_label(environment["humidity"], HUMIDITY_BANDS),
        "rainfall_label": _band_label(environment["rainfall"], RAINFALL_BANDS),
    }