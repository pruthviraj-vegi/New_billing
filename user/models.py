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

    # --- ADDED TO FIX MIGRATION ERROR ---
    # These fields are required to avoid clashes with the default User model's
    # reverse accessors when you have a custom user model.
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="customuser_set",  # Unique related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="customuser_permissions_set",  # Unique related_name
        related_query_name="user",
    )
    # --- END OF FIX ---

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
