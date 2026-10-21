from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username"]
        labels = {
            "username": "Username",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["name", "photo"]
        labels = {
            "name": "Nama Lengkap",
            "photo": "Foto Profil",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }