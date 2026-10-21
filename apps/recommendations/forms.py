from django import forms

from .konstan import MEDIUM_CHOICES
from .models import RecommendationHistory


class RecommendationForm(forms.Form):
    land_name = forms.CharField(label="Nama lahan", max_length=100, strip=True)
    latitude = forms.FloatField(label="Latitude", min_value=-90, max_value=90)
    longitude = forms.FloatField(label="Longitude", min_value=-180, max_value=180)
    land_area = forms.FloatField(
        label="Luas lahan (m²)", min_value=0.01,
        help_text="Dipakai untuk menyaring tanaman yang butuh ruang lebih besar dari lahanmu.",
    )
    planting_medium = forms.ChoiceField(label="Media tanam", choices=MEDIUM_CHOICES)


#* Update form nama
class HistoryLandNameForm(forms.ModelForm):
    class Meta:
        model = RecommendationHistory
        fields = ("land_name",)
        labels = {"land_name": "Nama lahan"}
