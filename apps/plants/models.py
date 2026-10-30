from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models
from django.db.models.functions import Lower


class Plant(models.Model):
    CATEGORY_CHOICES = [
        ("sayur", "Sayur"),
        ("buah", "Buah"),
        ("herbal", "Herbal"),
        ("hias", "Hias"),
    ]
    SPACE_NEEDED_CHOICES = [
        ("small", "Kecil"),
        ("medium", "Sedang"),
        ("large", "Besar"),
    ]
    SUNLIGHT_CHOICES = [
        ("full_sun", "Matahari penuh"),
        ("partial_shade", "Teduh sebagian"),
        ("shade", "Teduh"),
    ]

    # Django's auto-generated id is NANEM's primary key. This is only
    # external-source metadata used to make API imports idempotent.
    perenual_id = models.IntegerField(
        null=True,
        blank=True,
        unique=True,
        editable=False,
    )
    name = models.CharField(max_length=200)
    scientific_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=2048, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Temperature in Celsius, humidity in percent, rainfall in mm/day.
    temp_min = models.FloatField(null=True, blank=True)
    temp_max = models.FloatField(null=True, blank=True)
    humidity_min = models.FloatField(null=True, blank=True)
    humidity_max = models.FloatField(null=True, blank=True)
    rainfall_min = models.FloatField(null=True, blank=True)
    rainfall_max = models.FloatField(null=True, blank=True)

    supports_soil = models.BooleanField(default=True)
    supports_hydroponic = models.BooleanField(default=False)
    sunlight = models.JSONField(default=list, blank=True)
    watering = models.CharField(max_length=20, blank=True)
    care_level = models.CharField(max_length=20, blank=True)
    # Null means the API did not provide the value; it is different from False.
    drought_tolerant = models.BooleanField(null=True, blank=True)
    indoor = models.BooleanField(null=True, blank=True)
    space_needed = models.CharField(max_length=10, choices=SPACE_NEEDED_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="plants_plant_name_ci_unique",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        errors = {}

        for field_name in ("humidity_min", "humidity_max"):
            value = getattr(self, field_name)
            if value is not None and not 0 <= value <= 100:
                errors[field_name] = (
                    "Kelembapan harus berada dalam rentang 0 sampai 100 persen."
                )

        for field_name in ("rainfall_min", "rainfall_max"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                errors[field_name] = "Curah hujan tidak boleh bernilai negatif."

        for minimum, maximum, label in (
            ("temp_min", "temp_max", "Suhu"),
            ("humidity_min", "humidity_max", "Kelembapan"),
            ("rainfall_min", "rainfall_max", "Curah hujan"),
        ):
            min_value = getattr(self, minimum)
            max_value = getattr(self, maximum)
            if (
                min_value is not None
                and max_value is not None
                and min_value > max_value
            ):
                errors[maximum] = (
                    f"{label} maksimum tidak boleh lebih kecil dari nilai minimum."
                )

        if not (self.supports_soil or self.supports_hydroponic):
            errors[NON_FIELD_ERRORS] = (
                "Pilih minimal satu media tanam: tanah atau hidroponik."
            )

        allowed_sunlight = {value for value, _ in self.SUNLIGHT_CHOICES}
        if not isinstance(self.sunlight, list) or any(
            not isinstance(value, str) or value not in allowed_sunlight
            for value in self.sunlight
        ):
            errors["sunlight"] = "Pilihan kebutuhan cahaya tidak valid."

        if errors:
            raise ValidationError(errors)
