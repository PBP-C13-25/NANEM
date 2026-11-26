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

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("Username tidak boleh kosong.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Username sudah digunakan oleh pengguna lain.")
        return username


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

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "size") and photo.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Ukuran foto melebihi batas (maks 2MB).")
        return photo