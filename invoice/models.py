from django.db import models
from django.conf import settings
from decimal import Decimal
from customer.models import Customer
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.models import ProductVariant

User = settings.AUTH_USER_MODEL


class Invoice(models.Model):
    class TaxTreatment(models.TextChoices):
        GST_BILL = "GST_BILL", "GST Bill"
        CASH_BILL = "CASH_BILL", "Cash Bill"

    class InvoiceType(models.TextChoices):
        CASH = "CASH", "Cash"
        CREDIT = "CREDIT", "Credit"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CHEQUE = "CHEQUE", "Cheque"
        CASH_ON_DELIVERY = "CASH_ON_DELIVERY", "Cash on Delivery"
        CREDIT_CARD = "CREDIT_CARD", "Credit Card"
        DEBIT_CARD = "DEBIT_CARD", "Debit Card"
        UPI = "UPI", "UPI"
        ONLINE_PAYMENT = "ONLINE_PAYMENT", "Online Payment"
        OTHER = "OTHER", "Other"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    cart_no = models.CharField(max_length=50, null=True, blank=True)
    invoice_number = models.CharField(
        max_length=50, unique=True
    )  # Remove null=True for auto-generation
    invoice_tax = models.CharField(
        max_length=20, choices=TaxTreatment.choices, default=TaxTreatment.GST_BILL
    )
    invoice_type = models.CharField(
        max_length=20, choices=InvoiceType.choices, default=InvoiceType.CASH
    )
    payment_status = models.CharField(
        max_length=25, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Total invoice amount before discount",
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Discount given to customer",
    )
    advance_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Amount received in advance (only for credit invoices)",
    )
    payment_method = models.CharField(
        max_length=25, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Amount paid against this invoice",
    )
    invoice_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_invoices",
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modified_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "payment_status"]),
            models.Index(fields=["invoice_date"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["invoice_tax"]),
            models.Index(fields=["invoice_number"]),
        ]

    def __str__(self):
        return self.invoice_number or f"Invoice-{self.id}"

    def clean(self):
        # Validate discount doesn't exceed amount
        if self.discount_amount and self.discount_amount > self.amount:
            raise ValidationError("Discount amount cannot exceed invoice amount")

        if self.discount_amount and self.discount_amount < 0:
            raise ValidationError("Discount amount cannot be negative")

        # Validate advance doesn't exceed total payable
        if self.advance_amount and self.advance_amount > self.total_payable:
            raise ValidationError("Advance amount cannot exceed total payable amount")

        if self.advance_amount and self.advance_amount < 0:
            raise ValidationError("Advance amount cannot be negative")

        # Validate total payments don't exceed total payable
        total_received = self.advance_amount or 0 + self.paid_amount or 0
        if total_received and total_received > self.total_payable:
            raise ValidationError(
                "Total received amount cannot exceed total payable amount"
            )

    def save(self, *args, **kwargs):
        # Auto-generate invoice number if not provided
        if not self.invoice_number:
            prefix = "GST" if self.invoice_tax == self.TaxTreatment.GST_BILL else "CASH"

            # Get the last invoice number for this tax treatment
            last_invoice = (
                Invoice.objects.filter(
                    invoice_tax=self.invoice_tax, invoice_number__startswith=prefix
                )
                .order_by("-id")
                .first()
            )

            if last_invoice and last_invoice.invoice_number:
                try:
                    # Extract number from last invoice (e.g., "GST-005" -> 5)
                    last_num = int(last_invoice.invoice_number.split("-")[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1

            self.invoice_number = f"{prefix}-{next_num:03d}"

        # Automatically set advance_amount to 0 and payment_status to PAID for cash invoices
        if self.invoice_type == self.InvoiceType.CASH:
            self.advance_amount = 0
            self.payment_status = self.PaymentStatus.PAID

        # Auto-update payment status for credit invoices
        if self.invoice_type == self.InvoiceType.CREDIT:
            self._update_payment_status()

        super().save(*args, **kwargs)

    @property
    def total_payable(self):
        """Total amount customer owes after discount"""
        return self.amount - self.discount_amount

    @property
    def net_amount_due(self):
        """Amount still owed after advance payments"""
        return self.total_payable - self.advance_amount

    @property
    def remaining_amount(self):
        """Final amount still owed by customer"""
        return self.net_amount_due - self.paid_amount

    @property
    def total_received(self):
        """Total amount received from customer (advance + payments)"""
        return self.advance_amount + self.paid_amount

    @property
    def is_fully_paid(self):
        """Check if invoice is fully paid"""
        return self.remaining_amount <= 0

    @property
    def is_overdue(self):
        """Check if credit invoice is overdue"""
        if (
            self.invoice_type == self.InvoiceType.CREDIT
            and self.due_date
            and not self.is_fully_paid
        ):
            return timezone.now().date() > self.due_date.date()
        return False

    def _update_payment_status(self):
        """Internal method to update payment status"""
        if self.total_received >= self.total_payable:
            self.payment_status = self.PaymentStatus.PAID
        elif self.total_received > 0:
            self.payment_status = self.PaymentStatus.PARTIALLY_PAID
        else:
            self.payment_status = self.PaymentStatus.UNPAID

    def update_payment_status(self):
        """Public method to update payment status and save"""
        self._update_payment_status()
        self.save(update_fields=["payment_status"])

    def make_payment(self, amount, payment_method=None):
        """Add a payment to this invoice"""
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")

        if amount > self.remaining_amount:
            raise ValidationError("Payment amount exceeds remaining balance")

        self.paid_amount += Decimal(str(amount))
        if payment_method:
            self.payment_method = payment_method

        self.save()
        return self.remaining_amount


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="invoice_items"
    )
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="invoice_items"
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,  # Allow fractional quantities (0.250 kg)
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    mrp = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        editable=False,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Maximum Retail Price / Actual Price",
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Actual selling price per unit (after discount)",
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Cost price per unit (for profit calculation)",
    )
    # Metadata
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["invoice", "product_variant"]),
            models.Index(fields=["product_variant"]),
        ]
        # Prevent duplicate items on same invoice
        unique_together = ["invoice", "product_variant"]

    def __str__(self):
        # Cache the related data to avoid multiple DB hits
        return f"#{self.invoice_id} - {self.quantity} × {self.product_variant_id}"

    def save(self, *args, **kwargs):
        """Auto-calculate totals before saving"""
        # self.calculate_totals()
        super().save(*args, **kwargs)

        # Auto-create FIFO tracking after saving
        self._create_fifo_tracking()

    def _create_fifo_tracking(self):
        """Create FIFO tracking records for this invoice item"""
        try:
            # Check if FIFO tracking already exists
            existing_tracking = self.fifo_tracking.exists()
            if existing_tracking:
                return

            # Create FIFO tracking using the dedicated model
            from .models import FIFOTracking

            FIFOTracking.allocate_fifo_stock(self, self.quantity)

        except Exception as e:
            # Log error but don't fail the save
            print(f"Error creating FIFO tracking: {e}")
            pass

    @property
    def discount_amount_per_unit(self):
        """Discount amount per unit"""
        return self.mrp - self.unit_price

    @property
    def discount_percentage(self):
        """Discount percentage based on MRP vs Selling Price"""
        if self.mrp > 0:
            return ((self.mrp - self.unit_price) / self.mrp) * 100
        return Decimal("0")

    @property
    def total_discount_amount(self):
        """Total discount amount for this line item"""
        return self.discount_amount_per_unit * self.quantity

    @property
    def gross_amount(self):
        """Total at MRP (before discount)"""
        return self.quantity * self.mrp

    @property
    def net_amount(self):
        """Total at selling price (after discount)"""
        return self.quantity * self.unit_price

    @property
    def tax_rate(self):
        """Get tax rate from product"""
        return self.product_variant.product.tax

    @property
    def calculated_tax_amount(self):
        """Tax amount based on net amount and product tax rate"""
        if self.tax_rate > 0:
            return (self.net_amount * self.tax_rate) / 100
        return Decimal("0")

    @property
    def total_amount(self):
        """Final total including tax"""
        return self.net_amount + self.calculated_tax_amount

    @property
    def profit_amount_per_unit(self):
        """Profit per unit"""
        return self.unit_price - self.purchase_price

    @property
    def total_profit(self):
        """Total profit for this line item"""
        return self.profit_amount_per_unit * self.quantity

    @property
    def profit_margin_percentage(self):
        """Profit margin as percentage of selling price"""
        if self.unit_price > 0:
            return (self.profit_amount_per_unit / self.unit_price) * 100
        return Decimal("0")

    @property
    def markup_percentage(self):
        """Markup percentage on purchase price"""
        if self.purchase_price > 0:
            return (self.profit_amount_per_unit / self.purchase_price) * 100
        return Decimal("0")

    # def calculate_totals(self):
    #     """Calculate and update cached total fields"""
    #     self.line_total = self.gross_amount
    #     self.tax_amount = self.calculated_tax_amount

    # Manager methods for better queries
    @classmethod
    def get_invoice_items_with_details(cls, invoice_id):
        """Optimized query to get invoice items with related data"""
        return cls.objects.select_related(
            "product_variant__product", "product_variant__product__category", "invoice"
        ).filter(invoice_id=invoice_id)

    def get_product_name(self):
        """Get product name without hitting DB if already cached"""
        if hasattr(self, "_cached_product_name"):
            return self._cached_product_name
        return self.product_variant.product.name

    def cache_product_details(self):
        """Cache frequently accessed product details"""
        self._cached_product_name = self.product_variant.product.name
        self._cached_variant_name = self.product_variant.name
        return self


class SaleInvoiceLog(models.Model):
    """
    Tracks which supplier invoice stock was sold for FIFO calculations.
    This model links customer sales to supplier purchases without modifying existing models.
    """

    invoice_item = models.ForeignKey(
        InvoiceItem,
        on_delete=models.CASCADE,
        related_name="sale_invoice_log",
        help_text="The invoice item being tracked",
    )
    # Supplier purchase side - links to InventoryLog entry
    inventory_log = models.ForeignKey(
        "inventory.InventoryLog",
        on_delete=models.CASCADE,
        related_name="sale_invoice_log",
        help_text="Inventory log entry (STOCK_IN, INITIAL) from which this stock was allocated",
    )
    product_variant = models.ForeignKey(
        "inventory.ProductVariant",
        on_delete=models.CASCADE,
        related_name="sale_invoice_log",
        help_text="Product variant being tracked",
    )
    quantity_allocated = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Quantity allocated from this inventory log entry",
    )
    purchase_price_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Purchase price per unit from inventory log",
    )

    allocated_at = models.DateTimeField(auto_now_add=True)
    purchase_date = models.DateTimeField(
        help_text="Date of purchase (from inventory log timestamp)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sale_invoice_log",
    )

    class Meta:
        ordering = ["-allocated_at"]
        indexes = [
            models.Index(fields=["inventory_log", "product_variant"]),
            models.Index(fields=["invoice_item"]),
        ]
        # Prevent duplicate tracking for same invoice item
        unique_together = ["invoice_item", "inventory_log"]

    def __str__(self):
        return f"{self.quantity_allocated} sold from {self.inventory_log.supplier_invoice.invoice_number}"

    def save(self, *args, **kwargs):
        # Cache purchase date for FIFO ordering
        if not self.purchase_date:
            self.purchase_date = self.inventory_log.timestamp
            
        # Cache purchase price
        if not self.purchase_price_per_unit:
            self.purchase_price_per_unit = self.inventory_log.purchase_price or Decimal('0')
            
        super().save(*args, **kwargs)
