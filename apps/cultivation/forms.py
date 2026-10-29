from django import forms

from .models import CultivationGuide


class CultivationGuideForm(forms.ModelForm):
    class Meta:
        model = CultivationGuide
        fields = (
            "planting_steps",
            "watering_frequency",
            "fertilizing",
            "harvest_time",
        )
        labels = {
            "planting_steps": "Cara menanam",
            "watering_frequency": "Frekuensi penyiraman",
            "fertilizing": "Pemupukan",
            "harvest_time": "Waktu panen",
        }
        help_texts = {
            "planting_steps": "Tulis satu langkah per baris.",
        }
        widgets = {
            "planting_steps": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": "Contoh:\nRendam benih selama 6 jam\nTebar benih di media tanam\nSiram secukupnya setiap pagi",
            }),
            "watering_frequency": forms.Textarea(attrs={"rows": 3}),
            "fertilizing": forms.Textarea(attrs={"rows": 3}),
            "harvest_time": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_planting_steps(self):
        lines = [
            line.strip()
            for line in self.cleaned_data["planting_steps"].splitlines()
            if line.strip()
        ]
        if not lines:
            raise forms.ValidationError("Isi minimal satu langkah menanam.")
        return "\n".join(lines)