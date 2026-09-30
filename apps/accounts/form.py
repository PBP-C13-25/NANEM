from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
    """Form register.

    Field dibatasi eksplisit (name + username + password). is_staff /
    is_superuser TIDAK ada di form, jadi tidak bisa di-inject lewat POST
    (mass assignment). Password divalidasi AUTH_PASSWORD_VALIDATORS dan
    di-hash oleh Django (PBKDF2 default).
    """

    first_name = forms.CharField(label="Nama", max_length=150, strip=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "username")

    def clean_username(self):
        username = self.cleaned_data["username"]
        # 'Budi' dan 'budi' dianggap username yang sama (cegah akun tiruan)
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Username sudah dipakai.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
        if commit:
            user.save()
        return user