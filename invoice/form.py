from django import forms
from .models import Invoice
from django.utils import timezone
from datetime import timedelta


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "customer",
            "created_by",
            "amount",
            "discount_amount",
            "invoice_type",
            "advance_amount",
            "payment_method",
            "invoice_date",
            "due_date",
            "notes",
        ]
        widgets = {
            "customer": forms.Select(
                attrs={"class": "form-select", "placeholder": "Select customer"}
            ),
            "created_by": forms.Select(attrs={"class": "form-select"}),
            "invoice_type": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "readonly": True,
                }
            ),
            "discount_amount": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                    "required": False,
                }
            ),
            "advance_amount": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                    "readonly": True,
                    "required": False,
                }
            ),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "invoice_date": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"}
            ),
            "due_date": forms.DateTimeInput(
                attrs={
                    "class": "form-input",
                    "type": "datetime-local",
                    "default": timezone.now(),
                    "readonly": True,
                    "required": False,
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "placeholder": "Enter any additional notes",
                    "rows": "3",
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

        # Make due_date not required by default (will be handled in clean method)
        self.fields["due_date"].required = False

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        discount_amount = cleaned_data.get("discount_amount")
        advance_amount = cleaned_data.get("advance_amount")
        invoice_type = cleaned_data.get("invoice_type")
        due_date = cleaned_data.get("due_date")

        # Handle empty fields by setting them to 0
        if discount_amount is None or discount_amount == "":
            cleaned_data["discount_amount"] = 0
        if advance_amount is None or advance_amount == "":
            cleaned_data["advance_amount"] = 0

        # For cash invoices, set due_date to None, advance_amount to 0, and payment_status to PAID
        if invoice_type == Invoice.InvoiceType.CASH:
            cleaned_data["due_date"] = None
            cleaned_data["advance_amount"] = 0
            # Note: payment_status will be set in the model's save method
        # For credit invoices, due_date is required
        elif invoice_type == Invoice.InvoiceType.CREDIT and not due_date:
            raise forms.ValidationError("Due date is required for credit invoices")

        # Validate discount doesn't exceed amount
        if (
            amount
            and cleaned_data["discount_amount"]
            and cleaned_data["discount_amount"] > amount
        ):
            raise forms.ValidationError("Discount amount cannot exceed invoice amount")

        return cleaned_data

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount and amount < 0:
            raise forms.ValidationError("Amount cannot be negative")
        return amount

    def clean_discount_amount(self):
        discount_amount = self.cleaned_data.get("discount_amount")
        if discount_amount is None or discount_amount == "":
            return 0
        if discount_amount < 0:
            raise forms.ValidationError("Discount amount cannot be negative")
        return discount_amount

    def clean_advance_amount(self):
        advance_amount = self.cleaned_data.get("advance_amount")
        if advance_amount is None or advance_amount == "":
            return 0
        if advance_amount < 0:
            raise forms.ValidationError("Advance amount cannot be negative")
        return advance_amount

    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        if due_date is None or due_date == "":
            return timezone.now() + timedelta(days=30)
        return due_date
