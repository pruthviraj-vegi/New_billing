from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Product,
    ProductVariant,
    Category,
    Color,
    Size,
    ClothType,
    SupplierInvoice,
    InventoryLog,
)


class ProductForm(forms.ModelForm):
    """Form for creating a product"""

    class Meta:
        model = Product
        exclude = ["status"]

        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Enter product name", }
            ),
            "brand": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Enter brand name", "autofocus": True}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter product description",
                }
            ),
            "category": forms.Select(
                attrs={"class": "form-input", "placeholder": "Select category"}
            ),
            "cloth_type": forms.Select(
                attrs={"class": "form-input", "placeholder": "Select cloth type"}
            ),
            "hsn_code": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter HSN code (4-8 digits)",
                }
            ),
            "gst_percentage": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Enter GST percentage"}
            ),
        }

        def clean_hsn_code(self):
            hsn_code = self.cleaned_data.get("hsn_code")
            if hsn_code:
                # Remove any spaces or special characters
                hsn_code = "".join(filter(str.isdigit, hsn_code))
                if len(hsn_code) < 4 or len(hsn_code) > 8:
                    raise forms.ValidationError("HSN code must be 4-8 digits")
            return hsn_code


class VariantForm(forms.ModelForm):
    """Form for creating a variant"""

    supplier_invoice = forms.ModelChoiceField(
        queryset=SupplierInvoice.objects.all().order_by("-created_at"),
        required=False,
        widget=forms.Select(attrs={"class": "form-input"}),
        help_text="Select the supplier invoice for this variant (optional)",
    )

    class Meta:
        model = ProductVariant
        exclude = [
            "product",
            "barcode",
            "damaged_quantity",
            "status",
            "created_by",
        ]
        widgets = {
            "supplier": forms.Select(
                attrs={"class": "form-input", "placeholder": "Select supplier"}
            ),
            "extra_attributes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter extra attributes",
                    "rows": 3,
                }
            ),
            "quantity": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Enter quantity"}
            ),
            "minimum_quantity": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Enter minimum quantity"}
            ),
            "discount_percentage": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter discount percentage",
                }
            ),
            "gst_percentage": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Enter GST percentage"}
            ),
            "purchase_price": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Enter purchase price"}
            ),
            "mrp": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Enter selling price"}
            ),
            "size": forms.Select(
                attrs={"class": "form-input", "placeholder": "Select size"}
            ),
            "color": forms.Select(
                attrs={"class": "form-input", "placeholder": "Select color"}
            ),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than 0")
        return quantity

    def clean_purchase_price(self):
        purchase_price = self.cleaned_data.get("purchase_price")
        if purchase_price is not None and purchase_price <= 0:
            raise forms.ValidationError("Purchase price must be greater than 0")
        return purchase_price

    def clean_mrp(self):
        mrp = self.cleaned_data.get("mrp")
        if mrp is not None and mrp <= 0:
            raise forms.ValidationError("Selling price must be greater than 0")
        return mrp

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories"""

    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter category name",
                    "autofocus": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "Enter category description",
                }
            ),
        }


class ColorForm(forms.ModelForm):
    """Form for creating and editing colors"""

    class Meta:
        model = Color
        fields = ["name", "hex_code"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter color name",
                    "autofocus": True,
                }
            ),
            "hex_code": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "#FF0000",
                    "pattern": "#[0-9A-Fa-f]{6}",
                }
            ),
        }

    def clean_hex_code(self):
        hex_code = self.cleaned_data.get("hex_code")
        if hex_code:
            if not hex_code.startswith("#"):
                hex_code = "#" + hex_code
            if len(hex_code) != 7 or not all(
                c in "0123456789ABCDEFabcdef" for c in hex_code[1:]
            ):
                raise ValidationError(
                    "Please enter a valid hex color code (e.g., #FF0000)"
                )
        return hex_code


class SizeForm(forms.ModelForm):
    """Form for creating and editing sizes"""

    class Meta:
        model = Size
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter size name",
                    "autofocus": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "Enter size description",
                }
            ),
        }


class ClothTypeForm(forms.ModelForm):
    """Form for creating and editing cloth types"""

    class Meta:
        model = ClothType
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter cloth type name",
                    "autofocus": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "Enter cloth type description",
                }
            ),
        }


class StockInForm(forms.ModelForm):
    """Form specifically for stock in operations"""

    class Meta:
        model = InventoryLog
        fields = [
            "quantity_change",
            "purchase_price",
            "mrp",
            "supplier_invoice",
            "notes",
        ]
        widgets = {
            "quantity_change": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "step": "0.01",
                    "autofocus": True,
                    "placeholder": "Enter quantity",
                }
            ),
            "purchase_price": forms.NumberInput(
                attrs={"class": "form-input", "step": "0.01"}
            ),
            "mrp": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "supplier_invoice": forms.Select(attrs={"class": "form-input"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter only active supplier invoices
        self.fields["supplier_invoice"].queryset = SupplierInvoice.objects.filter(
            is_deleted=False
        )
        # Make supplier_invoice optional
        self.fields["supplier_invoice"].required = False
        # Make purchase price required for stock in
        self.fields["purchase_price"].required = True

    def clean(self):
        cleaned_data = super().clean()
        quantity_change = cleaned_data.get("quantity_change")
        purchase_price = cleaned_data.get("purchase_price")
        mrp = cleaned_data.get("mrp")

        # Allow zero values for all fields
        if quantity_change is not None and quantity_change <= 0:
            raise forms.ValidationError("Stock in quantity cannot be negative.")

        if purchase_price is not None and purchase_price < 0:
            raise forms.ValidationError("Purchase price cannot be negative.")

        if mrp is not None and mrp < 0:
            raise forms.ValidationError("Selling price cannot be negative.")

        return cleaned_data


class InventoryAdjustmentForm(forms.ModelForm):
    """Unified form for inventory adjustments (in, out, damage)"""

    class Meta:
        model = InventoryLog
        fields = [
            "quantity_change",
            "notes",
        ]
        widgets = {
            "quantity_change": forms.NumberInput(
                attrs={"class": "form-input", "step": "0.01", "autofocus": True}
            ),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.adjustment_type = kwargs.pop("adjustment_type", "adjustment_in")
        super().__init__(*args, **kwargs)

        # Set labels based on adjustment type
        labels = {
            "adjustment_in": {
                "quantity_change": "Quantity to Add",
                "notes": "Reason for Adjustment",
            },
            "adjustment_out": {
                "quantity_change": "Quantity to Remove",
                "notes": "Reason for Adjustment",
            },
            "damage": {
                "quantity_change": "Quantity to Mark as Damaged",
                "notes": "Damage Details",
            },
        }

        # Apply appropriate labels
        if self.adjustment_type in labels:
            for field_name, label in labels[self.adjustment_type].items():
                if field_name in self.fields:
                    self.fields[field_name].label = label

    def clean(self):
        cleaned_data = super().clean()
        quantity_change = cleaned_data.get("quantity_change")

        if quantity_change is not None and quantity_change <= 0:
            error_messages = {
                "adjustment_in": "Adjustment in quantity must be positive.",
                "adjustment_out": "Adjustment out quantity must be positive.",
                "damage": "Damage quantity must be positive.",
            }
            raise forms.ValidationError(
                error_messages.get(self.adjustment_type, "Quantity must be positive.")
            )

        return cleaned_data


# Convenience classes for backward compatibility
class AdjustmentInForm(InventoryAdjustmentForm):
    """Form for adjustment in operations"""

    def __init__(self, *args, **kwargs):
        kwargs["adjustment_type"] = "adjustment_in"
        super().__init__(*args, **kwargs)


class AdjustmentOutForm(InventoryAdjustmentForm):
    """Form for adjustment out operations"""

    def __init__(self, *args, **kwargs):
        kwargs["adjustment_type"] = "adjustment_out"
        super().__init__(*args, **kwargs)


class DamageForm(InventoryAdjustmentForm):
    """Form for damage operations"""

    def __init__(self, *args, **kwargs):
        kwargs["adjustment_type"] = "damage"
        super().__init__(*args, **kwargs)
