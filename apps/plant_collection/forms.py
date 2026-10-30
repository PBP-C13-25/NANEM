from django import forms
from .models import PlantCollection
from django.core.exceptions import ValidationError

class PlantCollectionForm(forms.ModelForm):
    class Meta:
        model = PlantCollection
        fields = ['title', 'photo', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Judul Tanaman'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Ceritakan tentang tanaman ini...'}),
        }
        error_messages = {
                    'title': {
                        'required': 'Judul tanaman wajib diisi!',
                    },
                    'photo': {
                        'required': 'Wajib melampirkan foto tanaman!',
                        'invalid': 'File yang dilampirkan harus berupa gambar.',
                    },
                    'description': {
                        'required': 'Deskripsi tanaman wajib diisi!',
                    },
                }
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            # 5MB = 5 * 1024 * 1024 bytes
            max_size = 5 * 1024 * 1024
            if photo.size > max_size:
                raise ValidationError("Ukuran file foto tidak boleh lebih dari 5MB.")
        return photo
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '')
        words = description.split()
        if len(words) > 10:
            raise ValidationError("Deskripsi tidak boleh lebih dari 10 kata.")
        return description
    
        