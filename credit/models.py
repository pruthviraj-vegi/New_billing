from django.db import models
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator

User = settings.AUTH_USER_MODEL

# Create your models here.


class Credit(models.Model):
    class PaidPurchased(models.TextChoices):
        Paid = "PAID", "Paid"
        Purchased = "PURCHASED", "Purchased"

    customer = models.ForeignKey(
        "customer.Customer", on_delete=models.PROTECT, related_name="credits"
    )
    paid_purchased = models.TextField(
        max_length=20, choices=PaidPurchased.choices, default=PaidPurchased.PAID
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Enter the Amount",
    )

    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
