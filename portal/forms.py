"""Minimal email-based forms backed by Django's built-in user model."""

from django import forms
from django.contrib.auth import get_user_model


User = get_user_model()


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


class RegistrationForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    confirm_password = forms.CharField(
        label="Confirm password", widget=forms.PasswordInput
    )

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirmation = cleaned.get("confirm_password")
        if password and confirmation and password != confirmation:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned

    def save(self):
        email = self.cleaned_data["email"]
        return User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password"],
        )
