from django import forms
from .models import PlantCollection

class PlantCollectionForm(forms.ModelForm):
    class Meta:
        model = PlantCollection
        fields = ['title', 'photo', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Judul Tanaman'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Ceritakan tentang tanaman ini...'}),
        }