from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "username"]
        labels = {
            "first_name": "Nama",
            "username": "Username",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["photo"]
        labels = {
            "photo": "Foto Profil",
        }
        widgets = {
            "photo": forms.FileInput(attrs={"class": "hidden-file-input", "id": "realPhotoInput"}),
        }

    def clean(self):
        self.cleaned_data = super().clean()
        photo = self.cleaned_data.get('photo')

        if photo.size > 2*1024*1024:
            raise forms.ValidationError("Ukuran foto melebihi batas (maks 2mb)")

        return photo