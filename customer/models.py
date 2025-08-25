from django.db import models
from django.conf import settings
from base.stringProcess import StringProcessor
from base.manager import SoftDeleteModel, phone_regex

User = settings.AUTH_USER_MODEL


class Customer(SoftDeleteModel):
    """Customer model for storing customer information."""

    name = models.CharField(
        max_length=255, null=True, blank=True, help_text="Customer's full name"
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_regex],
        help_text="Customer's phone number (unique)",
    )
    email = models.EmailField(
        blank=True, null=True, help_text="Customer's email address"
    )
    address = models.TextField(blank=True, null=True, help_text="Customer's address")
    store_credit_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Customer's store credit balance",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
        help_text="User who created this customer record",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return a string representation of the customer."""
        name_part = self.name or "Unknown"
        phone_part = self.phone_number or "No Phone"

        if self.address:
            return f"{name_part} ({self.address}) {phone_part}"
        return f"{name_part} {phone_part}"

    @property
    def display_name(self):
        """Return formatted display name."""
        return self.name or "Unknown Customer"

    @property
    def short_address(self):
        """Return shortened address for display."""
        if not self.address:
            return "No Address"
        return self.address[:50] + "..." if len(self.address) > 50 else self.address

    @property
    def has_credit(self):
        """Check if customer has store credit."""
        return self.store_credit_balance > 0

    @property
    def credit_status(self):
        """Return credit status as string."""
        if self.store_credit_balance > 0:
            return f"Credit: ₹{self.store_credit_balance}"
        return "No Credit"

    def add_credit(self, amount):
        """Add credit to customer's balance."""
        if amount > 0:
            self.store_credit_balance += amount
            self.save(update_fields=["store_credit_balance", "updated_at"])

    def deduct_credit(self, amount):
        """Deduct credit from customer's balance."""
        if amount > 0 and self.store_credit_balance >= amount:
            self.store_credit_balance -= amount
            self.save(update_fields=["store_credit_balance", "updated_at"])
            return True
        return False

    class Meta:
        indexes = [
            models.Index(fields=["name"], name="customer_name_idx"),
            models.Index(fields=["phone_number"], name="customer_phone_number_idx"),
            models.Index(fields=["created_at"], name="customer_created_at_idx"),
            models.Index(fields=["store_credit_balance"], name="customer_credit_idx"),
        ]
        ordering = ["-created_at"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def save(self, *args, **kwargs):
        """Override save method to clean and format data."""
        self.phone_number = StringProcessor(self.phone_number).cleaned_string
        self.name = StringProcessor(self.name).toTitle()
        self.email = StringProcessor(self.email).toLowercase()
        self.address = StringProcessor(self.address).toTitle()

        super().save(*args, **kwargs)

    def clean(self):
        """Custom validation."""
        from django.core.exceptions import ValidationError

        # Ensure phone number is not empty
        if not self.phone_number:
            raise ValidationError("Phone number is required.")

        # Ensure name is not empty
        if not self.name:
            raise ValidationError("Customer name is required.")

        # Validate email format if provided
        if self.email and "@" not in self.email:
            raise ValidationError("Please enter a valid email address.")
