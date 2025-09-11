# ==================================================================
#
#       COMPLETE DJANGO PROJECT STRUCTURE & CODE
#
# This file contains the final, complete code for all the apps
# we have designed together.
#
# Structure:
# 1. Main Project Files (settings.py, urls.py)
# 2. Accounts App (Authentication & Roles)
# 3. Supplier Management App
# 4. Inventory App
# 5. Billing App
#
# ==================================================================


# ==================================================================
# 1. MAIN PROJECT FILES
# ==================================================================

# ------------------------------------------------------------------
# File: myproject/settings.py (Key settings to add)
# ------------------------------------------------------------------
"""
# Add your new apps to INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Your new apps
    'accounts',
    'inventory',
    'supplier_management',
    'billing',
]

# Tell Django to use your custom user model
AUTH_USER_MODEL = "accounts.CustomUser"
"""

# ------------------------------------------------------------------
# File: myproject/urls.py (Main project URL configuration)
# ------------------------------------------------------------------
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Include the accounts app's URLs
    path('accounts/', include('accounts.urls')),
    
    # Also include Django's built-in auth URLs for login/logout
    path('accounts/', include('django.contrib.auth.urls')),

    # You will add URLs for your other apps here later
    # path('inventory/', include('inventory.urls')),
    # path('billing/', include('billing.urls')),
]

# This is needed to serve media files (like product images) during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""


# ==================================================================
# 2. ACCOUNTS APP (Authentication & Roles)
# ==================================================================

# ------------------------------------------------------------------
# File: accounts/managers.py
# ------------------------------------------------------------------
from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    def email_validator(self, email):
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError(_("Please provide a valid email address"))

    def create_user(
        self, full_name, phone_number, password, email=None, **extra_fields
    ):
        if not full_name:
            raise ValueError(_("Users must submit a full name"))
        if not phone_number:
            raise ValueError(_("Users must submit a phone number"))

        if email:
            email = self.normalize_email(email)
            self.email_validator(email)

        user = self.model(
            full_name=full_name, phone_number=phone_number, email=email, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, full_name, phone_number, password, email=None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "OWNER")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superusers must have is_staff=True"))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superusers must have is_superuser=True"))

        return self.create_user(
            full_name, phone_number, password, email, **extra_fields
        )


# ------------------------------------------------------------------
# File: accounts/models.py
# ------------------------------------------------------------------
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        CASHIER = "CASHIER", "Cashier"

    full_name = models.CharField(max_length=255)
    email = models.EmailField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Email Address (Optional)"),
    )
    phone_number = models.CharField(
        max_length=15, unique=True, verbose_name=_("Phone Number")
    )
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CASHIER)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["full_name"]
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    @property
    def is_owner(self):
        return self.role == self.Roles.OWNER

    @property
    def is_manager(self):
        return self.role in [self.Roles.OWNER, self.Roles.MANAGER]


# ------------------------------------------------------------------
# File: accounts/forms.py
# ------------------------------------------------------------------
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("full_name", "phone_number", "email", "role")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("full_name", "phone_number", "email", "role", "is_active")


# ------------------------------------------------------------------
# File: accounts/views.py
# ------------------------------------------------------------------
from django.urls import reverse_lazy
from django.views import generic
from .forms import CustomUserCreationForm


class SignUpView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("register_success")
    template_name = "accounts/register.html"


# ------------------------------------------------------------------
# File: accounts/urls.py
# ------------------------------------------------------------------
from django.urls import path
from .views import SignUpView
from django.views.generic.base import TemplateView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path(
        "signup/success/",
        TemplateView.as_view(template_name="accounts/register_success.html"),
        name="register_success",
    ),
]


# ==================================================================
# 3. SUPPLIER MANAGEMENT APP
# ==================================================================

# ------------------------------------------------------------------
# File: supplier_management/models.py
# ------------------------------------------------------------------
from django.db import models
from django.conf import settings
from django.db.models import Sum

User = settings.AUTH_USER_MODEL


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    gstin = models.CharField(
        max_length=15, blank=True, help_text="Supplier's GST Identification Number."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def balance_due(self):
        total_invoiced = (
            self.invoices.filter(status__in=["UNPAID", "PARTIALLY_PAID"]).aggregate(
                total=Sum("total_amount")
            )["total"]
            or 0
        )
        total_paid_on_invoices = (
            self.invoices.filter(status__in=["UNPAID", "PARTIALLY_PAID"]).aggregate(
                total=Sum("paid_amount")
            )["total"]
            or 0
        )
        return total_invoiced - total_paid_on_invoices


class SupplierInvoice(models.Model):
    class InvoiceType(models.TextChoices):
        GST_APPLICABLE = "GST_APPLICABLE", "GST Applicable"
        LOCAL_PURCHASE = "LOCAL_PURCHASE", "Local Purchase"

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
    invoice_date = models.DateField()
    invoice_type = models.CharField(
        max_length=20, choices=InvoiceType.choices, default=InvoiceType.GST_APPLICABLE
    )
    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("supplier", "invoice_number")
        ordering = ["-invoice_date"]

    def __str__(self):
        return f"Invoice {self.invoice_number} from {self.supplier.name}"


class SupplierPayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        UPI = "UPI", "UPI"

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="payments_made"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    unallocated_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.unallocated_amount = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.amount} paid to {self.supplier.name} via {self.get_method_display()}"


class SupplierPaymentAllocation(models.Model):
    payment = models.ForeignKey(
        SupplierPayment, on_delete=models.CASCADE, related_name="allocations"
    )
    invoice = models.ForeignKey(
        SupplierInvoice, on_delete=models.CASCADE, related_name="allocations"
    )
    amount_allocated = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("payment", "invoice")

    def __str__(self):
        return f"{self.amount_allocated} of Payment {self.payment.id} allocated to Invoice {self.invoice.invoice_number}"


# ==================================================================
# 4. INVENTORY APP
# ==================================================================

# ------------------------------------------------------------------
# File: inventory/models.py
# ------------------------------------------------------------------
from django.db import models
from django.conf import settings
from django.db import transaction
from supplier_management.models import Supplier, SupplierInvoice

User = settings.AUTH_USER_MODEL


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    class ProductStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        DISCONTINUED = "DISCONTINUED", "Discontinued"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    suppliers = models.ManyToManyField(Supplier, blank=True, related_name="products")
    status = models.CharField(
        max_length=20, choices=ProductStatus.choices, default=ProductStatus.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to="product_images/", help_text="The product image file."
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Alternative text for the image for accessibility.",
    )
    is_featured = models.BooleanField(
        default=False, help_text="Is this the main image for the product?"
    )

    class Meta:
        ordering = ["-is_featured"]

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductVariant(models.Model):
    class VariantStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DISCONTINUED = "DISCONTINUED", "Discontinued"

    class Meta:
        unique_together = ("product", "size", "color")

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    barcode = models.CharField(max_length=100, unique=True, db_index=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    extra_attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=VariantStatus.choices, default=VariantStatus.ACTIVE
    )
    reorder_level = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        parts = []
        if self.size:
            parts.append(f"Size: {self.size}")
        if self.color:
            parts.append(f"Color: {self.color}")
        if self.extra_attributes:
            for key, value in self.extra_attributes.items():
                parts.append(f"{key.capitalize()}: {value}")
        variant_str = ", ".join(parts)
        if not variant_str:
            return f"{self.product.name} - [{self.barcode}]"
        return f"{self.product.name} ({variant_str}) - [{self.barcode}]"


class InventoryLog(models.Model):
    class TransactionTypes(models.TextChoices):
        STOCK_IN = "STOCK_IN", "Stock In"
        SALE = "SALE", "Sale"
        RETURN = "RETURN", "Customer Return"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        INITIAL = "INITIAL", "Initial Stock"

    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="inventory_logs"
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    supplier_invoice = models.ForeignKey(
        SupplierInvoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_logs",
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionTypes.choices)
    quantity_change = models.IntegerField()
    new_quantity = models.PositiveIntegerField()
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.variant} changed by {self.quantity_change} on {self.timestamp.strftime('%Y-%m-%d')}"


# ==================================================================
# 5. BILLING APP
# ==================================================================

# ------------------------------------------------------------------
# File: billing/models.py
# ------------------------------------------------------------------
from django.db import models
from django.conf import settings
from django.db.models import Sum
from inventory.models import ProductVariant, InventoryLog
from accounts.models import CustomUser

User = settings.AUTH_USER_MODEL


class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    store_credit_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone_number})"

    @property
    def total_due(self):
        total = (
            self.invoices.filter(status__in=["UNPAID", "PARTIALLY_PAID"]).aggregate(
                total=Sum("grand_total")
            )["total"]
            or 0
        )
        paid = (
            self.invoices.filter(status__in=["UNPAID", "PARTIALLY_PAID"]).aggregate(
                total=Sum("paid_amount")
            )["total"]
            or 0
        )
        return total - paid


class Invoice(models.Model):
    class InvoiceStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"

    class Invoice_type(models.TextChoices):
        GST_APPLICABLE = "GST_APPLICABLE", "GST Applicable"
        GST_EXEMPT = "GST_EXEMPT", "GST Exempt"
        UNLEDGERED = "UNLEDGERED", "Unledgered"

    invoice_number = models.CharField(max_length=50, unique=True)
    gst_invoice_number = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.UNPAID
    )
    tax_treatment = models.CharField(
        max_length=20, choices=Invoice_type.choices, default=Invoice_type.GST_APPLICABLE
    )
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.gst_invoice_number or self.invoice_number)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.name} on Invoice {self.invoice.invoice_number}"


class SoldItemBatch(models.Model):
    invoice_item = models.ForeignKey(
        InvoiceItem, on_delete=models.CASCADE, related_name="batch_allocations"
    )
    purchase_log = models.ForeignKey(
        InventoryLog,
        on_delete=models.PROTECT,
        related_name="sales_allocations",
        limit_choices_to={
            "transaction_type__in": [
                InventoryLog.TransactionTypes.STOCK_IN,
                InventoryLog.TransactionTypes.INITIAL,
            ]
        },
    )
    quantity_sold = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity_sold} units from batch {self.purchase_log.id} for {self.invoice_item}"


class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CREDIT_CARD = "CREDIT_CARD", "Credit Card"
        UPI = "UPI", "UPI"
        STORE_CREDIT = "STORE_CREDIT", "Store Credit"

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    unallocated_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.unallocated_amount = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.amount} paid by {self.customer.name} via {self.get_method_display()}"


class PaymentAllocation(models.Model):
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="allocations"
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="allocations"
    )
    amount_allocated = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("payment", "invoice")

    def __str__(self):
        return f"{self.amount_allocated} of Payment {self.payment.id} allocated to Invoice {self.invoice.invoice_number}"


class CreditNote(models.Model):
    class RefundType(models.TextChoices):
        STORE_CREDIT = "STORE_CREDIT", "Store Credit"
        CASH_REFUND = "CASH_REFUND", "Cash Refund"

    credit_note_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="credit_notes"
    )
    original_invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True
    )
    total_refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    refund_type = models.CharField(max_length=20, choices=RefundType.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Credit Note {self.credit_note_number} for {self.customer.name}"


class CreditNoteItem(models.Model):
    credit_note = models.ForeignKey(
        CreditNote, on_delete=models.CASCADE, related_name="items"
    )
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.name} on Credit Note {self.credit_note.credit_note_number}"


# ==================================================================
# 6. TEMPLATES
# ==================================================================

# ------------------------------------------------------------------
# File: templates/accounts/register.html
# ------------------------------------------------------------------
"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Register New User</title>
    <style>
        body { font-family: sans-serif; max-width: 500px; margin: auto; padding: 20px; }
        form { display: flex; flex-direction: column; gap: 15px; }
        .form-field { display: flex; flex-direction: column; }
        button { padding: 10px; cursor: pointer; }
    </style>
</head>
<body>
    <h2>Register a New Staff Member</h2>
    <form method="post">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Register</button>
    </form>
</body>
</html>
"""

# ------------------------------------------------------------------
# File: templates/accounts/register_success.html
# ------------------------------------------------------------------
"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Registration Successful</title>
    <style>
        body { font-family: sans-serif; max-width: 500px; margin: auto; padding: 20px; text-align: center; }
    </style>
</head>
<body>
    <h2>Registration Successful!</h2>
    <p>The new user has been created.</p>
    <p><a href="{% url 'signup' %}">Register another user</a></p>
</body>
</html>
"""
