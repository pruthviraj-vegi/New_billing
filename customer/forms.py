from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone_number", "email", "address"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter full name",
                    "autofocus": True,
                }
            ),
            "phone_number": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter 10-digit phone number",
                    "maxlength": "10",
                    "pattern": "[0-9]{10}",
                }
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "Enter email address"}
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "placeholder": "Enter complete address",
                    "rows": "4",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        # Add required field indicators
        for field_name, field in self.fields.items():
            if field.required:
                field.label = f"{field.label} *"

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")

        # Check if phone number is exactly 10 digits
        if not phone_number.isdigit() or len(phone_number) != 10:
            raise forms.ValidationError(
                "Phone number must be exactly 10 digits (e.g., 9876543210)."
            )

        # Check for duplicate phone number, excluding current instance
        existing_customer = Customer.objects.filter(phone_number=phone_number)
        if self.instance:
            existing_customer = existing_customer.exclude(pk=self.instance.pk)

        if existing_customer.exists():
            raise forms.ValidationError(
                "This phone number is already in use by another customer."
            )

        return phone_number

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name or not name.strip():
            raise forms.ValidationError("Customer name is required.")
        return name.strip()

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and not "@" in email:
            raise forms.ValidationError("Please enter a valid email address.")
        return email.lower() if email else email
