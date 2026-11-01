from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import *


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Parol", widget=forms.PasswordInput)


class RegisterForm(forms.Form):
    name = forms.CharField(label="Ism Familiya", max_length=150, strip=True)
    # Default Django User.username has max_length=150.
    email = forms.EmailField(label="Email", max_length=150)
    password = forms.CharField(label="Parol", min_length=8, widget=forms.PasswordInput)
    confirm_password = forms.CharField(
        label="Parolni tasdiqlang", widget=forms.PasswordInput
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu email allaqachon mavjud.")
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Bu email allaqachon mavjud.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if len(password) < 8:
            raise forms.ValidationError("Parol kamida 8 belgidan iborat bo‘lsin.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirmation = cleaned.get("confirm_password")
        if password and confirmation and password != confirmation:
            self.add_error("confirm_password", "Parollar mos emas.")
        return cleaned


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'subject', 'message']

        


