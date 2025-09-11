# ==================================================================
# File: supplier_management/models.py
# This file contains the complete models for managing suppliers,
# their invoices (both GST and Local), and their payments.
# ==================================================================

from django.db import models
from django.conf import settings
from base.manager import SoftDeleteModel, phone_regex
from django.utils import timezone
from base.utility import StringProcessor
from django.utils.text import slugify
from datetime import datetime
from django.db.models import Sum
from decimal import Decimal

User = settings.AUTH_USER_MODEL

# Create your models here.


class Supplier(SoftDeleteModel):
    """
    Represents a supplier. This model holds their contact information
    and will be used to track their overall account balance.
    """

    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True, validators=[phone_regex])
    gstin = models.CharField(
        max_length=15, blank=True, help_text="Supplier's GST Identification Number."
    )
    address = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="supplier_created_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = StringProcessor(self.name).toTitle()
        self.contact_person = StringProcessor(self.contact_person).toTitle()
        self.email = StringProcessor(self.email).toLowercase()
        self.phone = StringProcessor(self.phone).cleaned_string
        self.gstin = StringProcessor(self.gstin).toUppercase()
        self.address = StringProcessor(self.address).toTitle()

        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        total_invoiced = (
            self.invoices.aggregate(total=Sum("total_amount"))["total"] or 0
        )
        total_paid_on_invoices = (
            self.payments_made.aggregate(total=Sum("amount"))["total"] or 0
        )
        return total_invoiced - total_paid_on_invoices


class SupplierInvoice(SoftDeleteModel):
    """
    Represents a purchase invoice from a supplier. This is the core model
    for tracking purchases and linking them to your inventory.
    """

    class InvoiceType(models.TextChoices):
        GST_APPLICABLE = "GST_APPLICABLE", "GST Applicable"
        LOCAL_PURCHASE = "LOCAL_PURCHASE", "Local Purchase"

    class GstType(models.TextChoices):
        CGST_SGST = "CGST_SGST", "CGST/SGST"
        IGST = "IGST", "IGST"

    class InvoiceStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="invoices"
    )
    invoice_number = models.CharField(
        max_length=100, help_text="The invoice number from the supplier."
    )
    invoice_date = models.DateTimeField(default=timezone.now)

    invoice_type = models.CharField(
        max_length=20, choices=InvoiceType.choices, default=InvoiceType.GST_APPLICABLE
    )

    gst_type = models.CharField(
        max_length=20,
        choices=GstType.choices,
        null=True,
        blank=True,
        help_text="Specify GST type if applicable.",
        default=GstType.IGST,
    )
    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="The total amount before taxes.",
    )

    # CHANGED: As per your request, only storing cgst_amount. SGST is assumed to be the same.
    cgst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="For CGST/SGST type, SGST is assumed to be the same as this amount.",
    )
    igst_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    adjustment_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )

    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="The grand total amount including all taxes.",
    )
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="supplier_invoice_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("supplier", "invoice_number")
        ordering = ["-invoice_date"]

    def __str__(self):
        return f"Invoice {self.invoice_number} from {self.supplier.name}"

    def save(self, *args, **kwargs):
        self.invoice_number = StringProcessor(self.invoice_number).toUppercase()
        self.notes = StringProcessor(self.notes).toTitle()

        super().save(*args, **kwargs)


class SupplierPayment(SoftDeleteModel):
    """
    Records a payment made TO a supplier. This payment is linked to the
    supplier's account, not to a single invoice, allowing for bulk payments.
    """

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        UPI = "UPI", "UPI"

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="payments_made"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank transaction reference number.",
    )
    unallocated_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    payment_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="supplier_payment_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.unallocated_amount = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.amount} paid to {self.supplier.name} via {self.get_method_display()}"


class SupplierPaymentAllocation(SoftDeleteModel):
    """
    The "bridge" model. This links a specific payment to a specific invoice,
    recording how much of that payment was used to clear that invoice.
    """

    payment = models.ForeignKey(
        SupplierPayment, on_delete=models.CASCADE, related_name="allocations"
    )
    invoice = models.ForeignKey(
        SupplierInvoice, on_delete=models.CASCADE, related_name="allocations"
    )
    amount_allocated = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="supplier_payment_allocation_created_by",
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Removed unique_together constraint to allow multiple allocations
        # from the same payment to the same invoice
        pass

    def __str__(self):
        return f"{self.amount_allocated} of Payment {self.payment.id} allocated to Invoice {self.invoice.invoice_number}"


class MediaFile(models.Model):
    """
    Represents a media file. This model is used to store the media files for the supplier invoices.
    """

    supplier_invoice = models.ForeignKey(
        SupplierInvoice, on_delete=models.CASCADE, related_name="media_files"
    )
    media_file = models.FileField(upload_to="supplier_invoices/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.file.name

    def save(self, *args, **kwargs):
        if self.media_file:
            new_filename = f"{slugify(self.supplier_invoice.invoice_number)}-{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            self.media_file.name = new_filename
        super().save(*args, **kwargs)
