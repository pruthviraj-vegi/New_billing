from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Define the fields to display in the list view
    list_display = (
        "full_name",
        "phone_number",
        "email",
        "role",
        "is_active",
        "is_staff",
        "date_joined",
    )

    # Define the fields to display in the detail view
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        (_("Personal info"), {"fields": ("full_name", "email")}),
        (
            _("Role & Permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important dates"),
            {"fields": ("last_login", "date_joined"), "classes": ("collapse",)},
        ),
    )

    # Define the fields to display when adding a new user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "full_name",
                    "phone_number",
                    "email",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    # Define search fields
    search_fields = ("full_name", "phone_number", "email")

    # Define filters
    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )

    # Define ordering
    ordering = ("-date_joined",)

    # Define readonly fields
    readonly_fields = ("last_login", "date_joined")

    # Define actions
    actions = ["activate_users", "deactivate_users", "make_staff", "remove_staff"]

    # Custom actions
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) were successfully activated.")

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) were successfully deactivated.")

    deactivate_users.short_description = "Deactivate selected users"

    def make_staff(self, request, queryset):
        """Make selected users staff"""
        updated = queryset.update(is_staff=True)
        self.message_user(request, f"{updated} user(s) were successfully made staff.")

    make_staff.short_description = "Make selected users staff"

    def remove_staff(self, request, queryset):
        """Remove staff status from selected users"""
        updated = queryset.update(is_staff=False)
        self.message_user(
            request, f"{updated} user(s) were successfully removed from staff."
        )

    remove_staff.short_description = "Remove staff status from selected users"

    # Override save method to ensure proper password hashing
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new user
            obj.set_password(obj.password)
        elif "password" in form.changed_data:  # Password was changed
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)


# Customize admin site
admin.site.site_header = "Billing System Administration"
admin.site.site_title = "Billing Admin"
admin.site.index_title = "Welcome to Billing System Administration"
