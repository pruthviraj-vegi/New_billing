# ------------------------------------------------------------------
# File: accounts/forms.py
# ------------------------------------------------------------------
from django import forms
from django.contrib.auth.forms import UserChangeForm, AuthenticationForm, UserCreationForm
from django.contrib.auth import authenticate
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("full_name", "phone_number", "email", "role", "is_active")
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter full name",
                    "autofocus": True,
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter phone number",
                    "maxlength": "15",
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "Enter email address"}
            ),
            "role": forms.Select(
                attrs={"class": "form-select"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password fields from UserCreationForm since we're using phone_number as username
        self.fields.pop('password1', None)
        self.fields.pop('password2', None)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")

        # Check for duplicate phone number, excluding current instance
        existing_user = CustomUser.objects.filter(phone_number=phone_number)
        if self.instance and self.instance.pk:
            existing_user = existing_user.exclude(pk=self.instance.pk)

        if existing_user.exists():
            raise forms.ValidationError(
                "This phone number is already in use by another user."
            )

        return phone_number

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")
        if not full_name or not full_name.strip():
            raise forms.ValidationError("Full name is required.")
        return full_name.strip()


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("full_name", "phone_number", "email", "role", "is_active")
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter full name",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter phone number",
                    "maxlength": "15",
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "Enter email address"}
            ),
            "role": forms.Select(
                attrs={"class": "form-select"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-checkbox"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password field from UserChangeForm
        self.fields.pop('password', None)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")

        # Check for duplicate phone number, excluding current instance
        existing_user = CustomUser.objects.filter(phone_number=phone_number)
        if self.instance and self.instance.pk:
            existing_user = existing_user.exclude(pk=self.instance.pk)

        if existing_user.exists():
            raise forms.ValidationError(
                "This phone number is already in use by another user."
            )

        return phone_number

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")
        if not full_name or not full_name.strip():
            raise forms.ValidationError("Full name is required.")
        return full_name.strip()
