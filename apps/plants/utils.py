SUNLIGHT_LABELS = {
    "full_sun": "Matahari penuh",
    "partial_shade": "Teduh sebagian",
    "shade": "Teduh",
}

SPACE_LABELS = {"small": "Kecil", "medium": "Sedang", "large": "Besar"}

WATERING_CHOICES = [
    ("", "Belum ditentukan"),
    ("Minimum", "Jarang"),
    ("Average", "Sedang"),
    ("Frequent", "Sering"),
]

CARE_LEVEL_CHOICES = [
    ("", "Belum ditentukan"),
    ("Low", "Mudah"),
    ("Medium", "Sedang"),
    ("High", "Sulit"),
]


def prepare_plant_display(plant):
    media = []
    if plant.supports_soil:
        media.append("Tanah")
    if plant.supports_hydroponic:
        media.append("Hidroponik")
    plant.media_label = ", ".join(media) or "Belum ditentukan"
    plant.sunlight_label = ", ".join(
        SUNLIGHT_LABELS.get(value, value.replace("_", " ").title())
        for value in (plant.sunlight or [])
    ) or "Belum ditentukan"
    plant.space_label = SPACE_LABELS.get(plant.space_needed, "Belum ditentukan")
    return plant