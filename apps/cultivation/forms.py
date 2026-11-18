from django import forms

from .models import CultivationGuide


class CultivationGuideForm(forms.ModelForm):
    class Meta:
        model = CultivationGuide
        fields = (
            "planting_steps",
            "watering_frequency",
            "watering_note",
            "fertilizing_frequency",
            "fertilizing_note",
            "is_harvestable",
            "harvest_days_min",
            "harvest_days_max",
            "harvest_note",
        )
        labels = {
            "planting_steps": "Cara menanam",
            "watering_frequency": "Frekuensi penyiraman",
            "watering_note": "Catatan penyiraman",
            "fertilizing_frequency": "Frekuensi pemupukan",
            "fertilizing_note": "Jenis dan catatan pupuk",
            "is_harvestable": "Tanaman ini dipanen",
            "harvest_days_min": "Panen paling cepat (hari setelah tanam)",
            "harvest_days_max": "Panen paling lambat (hari setelah tanam)",
            "harvest_note": "Catatan panen",
        }
        help_texts = {
            "planting_steps": "Tulis satu langkah per baris.",
            "watering_note": "Opsional. Misalnya tanda media perlu disiram.",
            "fertilizing_note": "Opsional. Misalnya jenis pupuk dan dosisnya.",
            "harvest_note": "Opsional. Misalnya tanda siap panen.",
        }
        widgets = {
            "planting_steps": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": "Contoh:\nRendam benih selama 6 jam\nTebar benih di media tanam\nSiram secukupnya setiap pagi",
            }),
            "watering_note": forms.Textarea(attrs={"rows": 2}),
            "fertilizing_note": forms.Textarea(attrs={"rows": 2}),
            "harvest_note": forms.Textarea(attrs={"rows": 2}),
            "harvest_days_min": forms.NumberInput(attrs={"min": 1, "inputmode": "numeric"}),
            "harvest_days_max": forms.NumberInput(attrs={"min": 1, "inputmode": "numeric"}),
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

    def clean(self):
        cleaned_data = super().clean()
        minimum = cleaned_data.get("harvest_days_min")
        maximum = cleaned_data.get("harvest_days_max")

        if not cleaned_data.get("is_harvestable"):
            cleaned_data["harvest_days_min"] = None
            cleaned_data["harvest_days_max"] = None
            return cleaned_data

        if minimum is None and maximum is None and not cleaned_data.get("harvest_note", "").strip():
            self.add_error(
                "harvest_days_min",
                "Isi perkiraan hari panen atau tulis catatan panen.",
            )
        if minimum is not None and maximum is not None and minimum > maximum:
            self.add_error(
                "harvest_days_max",
                "Hari panen paling lambat tidak boleh lebih kecil dari yang paling cepat.",
            )
        return cleaned_data