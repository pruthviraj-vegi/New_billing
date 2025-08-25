# ------------------------------------------------------------------
# File: accounts/forms.py
# ------------------------------------------------------------------
from django import forms
from django.contrib.auth.forms import UserChangeForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import CustomUser


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("full_name", "phone_number", "email", "role", "is_active")
