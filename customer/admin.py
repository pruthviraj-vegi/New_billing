from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from datetime import timedelta
from .models import Customer


class CustomerStatusFilter(SimpleListFilter):
    """Filter customers by their active/inactive status."""

    title = "Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("inactive", "Inactive"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(is_deleted=False)
        if self.value() == "inactive":
            return queryset.filter(is_deleted=True)


class CustomerCreditFilter(SimpleListFilter):
    """Filter customers by their credit balance."""

    title = "Credit Balance"
    parameter_name = "credit"

    def lookups(self, request, model_admin):
        return (
            ("has_credit", "Has Credit"),
            ("no_credit", "No Credit"),
            ("high_credit", "High Credit (>₹1000)"),
        )

    def queryset(self, request, queryset):
        if self.value() == "has_credit":
            return queryset.filter(store_credit_balance__gt=0)
        if self.value() == "no_credit":
            return queryset.filter(store_credit_balance=0)
        if self.value() == "high_credit":
            return queryset.filter(store_credit_balance__gt=1000)


class CustomerDateFilter(SimpleListFilter):
    """Filter customers by creation date."""

    title = "Created Date"
    parameter_name = "created_date"

    def lookups(self, request, model_admin):
        return (
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("this_week", "This Week"),
            ("this_month", "This Month"),
            ("last_month", "Last Month"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "today":
            return queryset.filter(created_at__date=now.date())
        if self.value() == "yesterday":
            yesterday = now.date() - timedelta(days=1)
            return queryset.filter(created_at__date=yesterday)
        if self.value() == "this_week":
            return queryset.filter(created_at__gte=now - timedelta(days=7))
        if self.value() == "this_month":
            return queryset.filter(
                created_at__month=now.month, created_at__year=now.year
            )
        if self.value() == "last_month":
            last_month = now.replace(day=1) - timedelta(days=1)
            return queryset.filter(
                created_at__month=last_month.month, created_at__year=last_month.year
            )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin interface for Customer model."""

    # List display configuration
    list_display = [
        "id",
        "name",
        "phone_number",
        "email_display",
        "address_display",
        "credit_balance_display",
        "status_display",
        "created_at",
        "actions_display",
    ]

    # List display links
    list_display_links = ["id", "name"]

    # Search fields
    search_fields = ["name", "phone_number", "email", "address"]

    # Filters
    list_filter = [
        CustomerStatusFilter,
        CustomerCreditFilter,
        CustomerDateFilter,
        ("created_at", admin.DateFieldListFilter),
    ]

    # Fieldsets for add/edit form
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "phone_number", "email"), "classes": ("wide",)},
        ),
        ("Address Information", {"fields": ("address",), "classes": ("wide",)}),
        (
            "Financial Information",
            {"fields": ("store_credit_balance",), "classes": ("wide",)},
        ),
        (
            "System Information",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
                "description": "System-generated information",
            },
        ),
    )

    # Read-only fields
    readonly_fields = ["created_at", "updated_at"]

    # Admin actions
    actions = [
        "activate_customers",
        "deactivate_customers",
        "reset_credit_balance",
        "add_credit_to_selected",
        "export_customer_data",
    ]

    # Pagination
    list_per_page = 25

    # Ordering
    ordering = ["-created_at"]

    # Date hierarchy
    date_hierarchy = "created_at"

    # Autocomplete fields
    autocomplete_fields = ["created_by"]

    # Save on top
    save_on_top = True

    # Custom admin site title
    def get_admin_site_title(self):
        return "Customer Management"

    # Custom methods for list display
    def email_display(self, obj):
        """Display email with proper formatting."""
        if obj.email:
            return format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email)
        return format_html('<span style="color: #999;">No Email</span>')

    email_display.short_description = "Email"
    email_display.admin_order_field = "email"

    def address_display(self, obj):
        """Display shortened address."""
        if obj.address:
            short_addr = (
                obj.address[:50] + "..." if len(obj.address) > 50 else obj.address
            )
            return format_html('<span title="{}">{}</span>', obj.address, short_addr)
        return format_html('<span style="color: #999;">No Address</span>')

    address_display.short_description = "Address"

    def credit_balance_display(self, obj):
        """Display credit balance with color coding."""
        if obj.store_credit_balance > 0:
            return format_html(
                '<span style="color: #059669; font-weight: bold;">₹{}</span>',
                obj.store_credit_balance,
            )
        return format_html('<span style="color: #6b7280;">₹0.00</span>')

    credit_balance_display.short_description = "Credit Balance"
    credit_balance_display.admin_order_field = "store_credit_balance"

    def status_display(self, obj):
        """Display status with badge."""
        if obj.is_deleted:
            return format_html(
                '<span style="background: #fef2f2; color: #dc2626; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">INACTIVE</span>'
            )
        return format_html(
            '<span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">ACTIVE</span>'
        )

    status_display.short_description = "Status"
    status_display.admin_order_field = "is_deleted"

    def actions_display(self, obj):
        """Display action buttons."""
        view_url = reverse("admin:customer_customer_change", args=[obj.id])
        delete_url = reverse("admin:customer_customer_delete", args=[obj.id])

        return format_html(
            '<a href="{}" style="margin-right: 5px; color: #3b82f6;" title="View/Edit"><i class="fas fa-edit"></i></a>'
            '<a href="{}" style="color: #ef4444;" title="Delete" onclick="return confirm(\'Are you sure?\')"><i class="fas fa-trash"></i></a>',
            view_url,
            delete_url,
        )

    actions_display.short_description = "Actions"
    actions_display.allow_tags = True

    # Admin actions
    def activate_customers(self, request, queryset):
        """Activate selected customers."""
        updated = queryset.update(is_deleted=False)
        self.message_user(
            request, f"Successfully activated {updated} customer(s).", level="SUCCESS"
        )

    activate_customers.short_description = "Activate selected customers"

    def deactivate_customers(self, request, queryset):
        """Deactivate selected customers."""
        updated = queryset.update(is_deleted=True)
        self.message_user(
            request, f"Successfully deactivated {updated} customer(s).", level="SUCCESS"
        )

    deactivate_customers.short_description = "Deactivate selected customers"

    def reset_credit_balance(self, request, queryset):
        """Reset credit balance to zero for selected customers."""
        updated = queryset.update(store_credit_balance=0)
        self.message_user(
            request,
            f"Successfully reset credit balance for {updated} customer(s).",
            level="SUCCESS",
        )

    reset_credit_balance.short_description = "Reset credit balance to zero"

    def add_credit_to_selected(self, request, queryset):
        """Add credit to selected customers."""
        # This would typically open a form to input the amount
        # For now, we'll add a fixed amount of ₹100
        for customer in queryset:
            customer.add_credit(100)
        self.message_user(
            request,
            f"Successfully added ₹100 credit to {queryset.count()} customer(s).",
            level="SUCCESS",
        )

    add_credit_to_selected.short_description = "Add ₹100 credit to selected customers"

    def export_customer_data(self, request, queryset):
        """Export customer data (placeholder for CSV export)."""
        self.message_user(
            request,
            f"Export functionality for {queryset.count()} customer(s) would be implemented here.",
            level="INFO",
        )

    export_customer_data.short_description = "Export customer data"

    # Override get_queryset to include related data
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by")

    # Custom admin site configuration
    class Media:
        css = {"all": ("admin/css/customer_admin.css",)}
        js = ("admin/js/customer_admin.js",)

    # Override change form template
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_save_and_continue"] = True
        extra_context["show_save_and_add_another"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    # Override add form template
    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_save_and_add_another"] = True
        return super().add_view(request, form_url, extra_context)


# Customize admin site
admin.site.site_header = "Billing System Administration"
admin.site.site_title = "Billing System Admin"
admin.site.index_title = "Welcome to Billing System Administration"


# Add custom admin site statistics
def get_admin_site_stats():
    """Get statistics for admin dashboard."""
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(is_deleted=False).count()
    total_credit = (
        Customer.objects.aggregate(total=Sum("store_credit_balance"))["total"] or 0
    )
    customers_with_credit = Customer.objects.filter(store_credit_balance__gt=0).count()

    return {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "total_credit": total_credit,
        "customers_with_credit": customers_with_credit,
    }
