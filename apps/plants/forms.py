from django import forms

from .models import Plant


SUNLIGHT_CHOICES = [
    ("full_sun", "Matahari penuh"),
    ("partial_shade", "Teduh sebagian"),
    ("shade", "Teduh"),
]


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

NULLABLE_BOOLEAN_CHOICES = [
    ("", "Belum diketahui"),
    ("true", "Ya"),
    ("false", "Tidak"),
]


def coerce_nullable_boolean(value):
    if value in (True, "true"):
        return True
    if value in (False, "false"):
        return False
    return None


class PlantForm(forms.ModelForm):
    sunlight = forms.MultipleChoiceField(
        label="Kebutuhan cahaya",
        choices=SUNLIGHT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    watering = forms.ChoiceField(
        label="Kebutuhan air",
        choices=WATERING_CHOICES,
        required=False,
    )
    care_level = forms.ChoiceField(
        label="Tingkat perawatan",
        choices=CARE_LEVEL_CHOICES,
        required=False,
    )
    drought_tolerant = forms.TypedChoiceField(
        label="Tahan kekeringan",
        choices=NULLABLE_BOOLEAN_CHOICES,
        coerce=coerce_nullable_boolean,
        empty_value=None,
        required=False,
    )
    indoor = forms.TypedChoiceField(
        label="Dapat ditanam di dalam ruangan",
        choices=NULLABLE_BOOLEAN_CHOICES,
        coerce=coerce_nullable_boolean,
        empty_value=None,
        required=False,
    )

    class Meta:
        model = Plant
        fields = [
            "name",
            "scientific_name",
            "description",
            "image_url",
            "category",
            "supports_soil",
            "supports_hydroponic",
            "sunlight",
            "watering",
            "care_level",
            "drought_tolerant",
            "indoor",
            "space_needed",
            "temp_min",
            "temp_max",
            "humidity_min",
            "humidity_max",
            "rainfall_min",
            "rainfall_max",
        ]
        labels = {
            "name": "Nama tanaman",
            "scientific_name": "Nama ilmiah",
            "description": "Deskripsi",
            "image_url": "URL gambar",
            "category": "Kategori",
            "supports_soil": "Mendukung media tanah",
            "supports_hydroponic": "Mendukung hidroponik",
            "space_needed": "Kebutuhan ruang",
            "temp_min": "Suhu minimum (°C)",
            "temp_max": "Suhu maksimum (°C)",
            "humidity_min": "Kelembapan minimum (%)",
            "humidity_max": "Kelembapan maksimum (%)",
            "rainfall_min": "Curah hujan minimum (mm/hari)",
            "rainfall_max": "Curah hujan maksimum (mm/hari)",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "temp_min": forms.NumberInput(attrs={"step": "any"}),
            "temp_max": forms.NumberInput(attrs={"step": "any"}),
            "humidity_min": forms.NumberInput(attrs={"step": "any"}),
            "humidity_max": forms.NumberInput(attrs={"step": "any"}),
            "rainfall_min": forms.NumberInput(attrs={"step": "any"}),
            "rainfall_max": forms.NumberInput(attrs={"step": "any"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicate = Plant.objects.filter(name__iexact=name).exclude(
            pk=self.instance.pk
        )
        if duplicate.exists():
            raise forms.ValidationError(
                "Nama tanaman sudah digunakan. Gunakan nama yang berbeda."
            )
        return name

    def clean(self):
        cleaned_data = super().clean()

        for field_name in ("humidity_min", "humidity_max"):
            value = cleaned_data.get(field_name)
            if value is not None and not 0 <= value <= 100:
                self.add_error(
                    field_name,
                    "Kelembapan harus berada dalam rentang 0 sampai 100 persen.",
                )

        for minimum, maximum, label in (
            ("temp_min", "temp_max", "Suhu"),
            ("humidity_min", "humidity_max", "Kelembapan"),
            ("rainfall_min", "rainfall_max", "Curah hujan"),
        ):
            min_value = cleaned_data.get(minimum)
            max_value = cleaned_data.get(maximum)
            if (
                min_value is not None
                and max_value is not None
                and min_value > max_value
            ):
                self.add_error(
                    maximum,
                    f"{label} maksimum tidak boleh lebih kecil dari nilai minimum.",
                )

        if not (
            cleaned_data.get("supports_soil")
            or cleaned_data.get("supports_hydroponic")
        ):
            raise forms.ValidationError(
                "Pilih minimal satu media tanam: tanah atau hidroponik."
            )

        return cleaned_data
