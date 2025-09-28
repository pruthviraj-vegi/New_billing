from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, F, Q, Case, When, Count
from django.db.models.functions import Abs, Coalesce
from django.db import models
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.generic import View, DeleteView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from django.urls import reverse_lazy
from .services import InventoryService

from django.db import transaction

from .forms import (
    ProductForm,
    VariantForm,
    SizeForm,
    ColorForm,
    CategoryForm,
    ClothTypeForm,
    UOMForm,
    GSTHsnCodeForm,
)
from .models import Product, ProductVariant, InventoryLog, Size

from supplier.models import SupplierInvoice, Supplier

import logging

logger = logging.getLogger(__name__)


def inventory_dashboard(request):
    """Enhanced inventory dashboard with comprehensive metrics"""
    active_variants = ProductVariant.objects.filter(
        is_deleted=False, status=ProductVariant.VariantStatus.ACTIVE
    )

    # Calculate total stock in (all stock in transactions for active variants)
    total_stock_in = (
        InventoryLog.objects.filter(
            transaction_type="STOCK_IN", variant__is_deleted=False
        ).aggregate(total=Sum("quantity_change"))["total"]
        or 0
    )

    # Calculate total stock out (all stock out transactions for active variants)
    total_stock_out = (
        InventoryLog.objects.filter(
            transaction_type="SALE", variant__is_deleted=False
        ).aggregate(total=Sum("quantity_change"))["total"]
        or 0
    )

    # Calculate trending stock (items with recent stock out activity for active variants)
    trending_stock = (
        InventoryLog.objects.filter(
            transaction_type="SALE",
            variant__is_deleted=False,
            timestamp__gte=timezone.now() - timezone.timedelta(days=30),
        )
        .values("variant")
        .distinct()
        .count()
    )

    # Calculate damaged stock (items marked as damaged)
    damaged_stock = (
        ProductVariant.objects.filter(damaged_quantity__gt=0).aggregate(
            total=Sum("damaged_quantity")
        )["total"]
        or 0
    )

    # Additional metrics
    total_products = Product.objects.filter(is_deleted=False).count()
    total_variants = active_variants.count()
    low_stock_variants = active_variants.filter(
        quantity__lte=F("minimum_quantity")
    ).count()
    out_of_stock_variants = active_variants.filter(quantity=0).count()

    # Calculate total inventory value
    total_inventory_value = sum(variant.total_value for variant in active_variants)

    # Recent activities (last 7 days)
    recent_activities = InventoryLog.objects.filter(
        timestamp__gte=timezone.now() - timezone.timedelta(days=7),
        variant__is_deleted=False,
    ).order_by("-timestamp")[:10]

    # Top selling products (last 30 days)
    top_selling = (
        InventoryLog.objects.filter(
            transaction_type="SALE",
            variant__is_deleted=False,
            timestamp__gte=timezone.now() - timezone.timedelta(days=30),
        )
        .values("variant__product__brand", "variant__product__name")
        .annotate(total_sold=Sum("quantity_change"))
        .order_by("-total_sold")[:5]
    )

    # Stock alerts
    stock_alerts = active_variants.filter(quantity__lte=F("minimum_quantity")).order_by(
        "quantity"
    )[:5]

    context = {
        "total_stock_in": total_stock_in,
        "total_stock_out": total_stock_out,
        "trending_stock": trending_stock,
        "damaged_stock": damaged_stock,
        "total_products": total_products,
        "total_variants": total_variants,
        "low_stock_variants": low_stock_variants,
        "out_of_stock_variants": out_of_stock_variants,
        "total_inventory_value": total_inventory_value,
        "recent_activities": recent_activities,
        "top_selling": top_selling,
        "stock_alerts": stock_alerts,
    }

    return render(request, "inventory/dashboard.html", context)


@login_required
def low_stock_page(request):
    """Display all low stock items with pagination"""

    # Get active variants that are low on stock
    low_stock_variants = (
        ProductVariant.objects.filter(
            is_deleted=False,
            status=ProductVariant.VariantStatus.ACTIVE,
            quantity__lte=F("minimum_quantity"),
        )
        .select_related("product")
        .order_by("quantity")
    )

    # Pagination
    from django.core.paginator import Paginator

    paginator = Paginator(low_stock_variants, 20)  # 20 items per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate summary stats
    total_low_stock = low_stock_variants.count()
    out_of_stock = low_stock_variants.filter(quantity=0).count()
    critical_stock = low_stock_variants.filter(
        quantity__lt=F("minimum_quantity") * 0.5
    ).count()

    # Add critical threshold to each variant for template use
    for variant in page_obj:
        variant.critical_threshold = float(variant.minimum_quantity) * 0.5

    context = {
        "page_obj": page_obj,
        "total_low_stock": total_low_stock,
        "out_of_stock": out_of_stock,
        "critical_stock": critical_stock,
        "title": "Low Stock Items",
    }

    return render(request, "inventory/low_stock.html", context)


class CreateProduct(View):
    template_name = "inventory/product_create.html"
    title = "Create Product"
    product_form = ProductForm()
    variant_form = VariantForm()

    def get(self, request):
        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        # Remove super() call since View doesn't have get_context_data
        context = {}
        context["title"] = self.title
        context["product_form"] = self.product_form
        context["variant_form"] = self.variant_form
        context["category_form"] = CategoryForm()
        context["cloth_type_form"] = ClothTypeForm()
        context["uom_form"] = UOMForm()
        context["gst_hsn_form"] = GSTHsnCodeForm()
        context["size_form"] = SizeForm()
        context["color_form"] = ColorForm()
        return context

    def post(self, request):
        product_form = ProductForm(request.POST)
        variant_form = VariantForm(request.POST)
        if product_form.is_valid() and variant_form.is_valid():
            with transaction.atomic():
                product = product_form.save()
                variant = variant_form.save(commit=False)
                variant.product = product
                variant.created_by = request.user
                variant.save()
                InventoryService.create_initial_log(
                    variant,
                    request.user,
                    "Initial stock",
                    variant_form.cleaned_data.get("supplier_invoice"),
                )
                messages.success(request, "Product created successfully")
                return redirect("inventory_products:details", product_id=product.id)
        else:
            logger.error(f"Form invalid: {product_form.errors}, {variant_form.errors}")
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, self.get_context_data())


class DeleteProductVariant(DeleteView):
    template_name = "inventory/product_variant/delete.html"
    title = "Delete Product Variant"
    model = ProductVariant

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["variant"] = self.get_object()
        return context

    def get_success_url(self):
        # Store product ID before deletion
        product_id = (
            self.object.product.id if self.object and self.object.product else None
        )
        if product_id:
            return reverse_lazy("inventory:product_details", kwargs={"id": product_id})
        else:
            return reverse_lazy("inventory:product_home")

    def form_valid(self, form):
        # Store product ID before deletion
        product_id = (
            self.object.product.id if self.object and self.object.product else None
        )

        # Let Django handle the deletion properly
        result = super().form_valid(form)

        # Add success message
        messages.success(self.request, "Product variant deleted successfully")

        # Redirect to appropriate page
        if product_id:
            return redirect("inventory:product_details", id=product_id)
        else:
            return redirect("inventory:product_home")

    def form_invalid(self, form):
        logger.error(f"Form invalid: {form.errors}")
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


@login_required
def variant_update(request, pk):
    """Update product variant details"""
    variant = get_object_or_404(ProductVariant, pk=pk)

    if request.method == "POST":
        form = VariantForm(request.POST, instance=variant)
        if form.is_valid():
            try:
                with transaction.atomic():
                    old_purchase_price = variant.purchase_price
                    old_mrp = variant.mrp

                    # Save the updated variant
                    variant = form.save(commit=False)
                    variant.save()

                    # Create inventory log for price changes
                    if (
                        variant.purchase_price != old_purchase_price
                        or variant.mrp != old_mrp
                    ):
                        InventoryLog.objects.create(
                            variant=variant,
                            transaction_type="ADJUSTMENT_IN",
                            quantity_change=0,
                            new_quantity=variant.quantity,
                            purchase_price=variant.purchase_price,
                            mrp=variant.mrp,
                            notes=f"Price update: Purchase {old_purchase_price}→{variant.purchase_price}, Selling {old_mrp}→{variant.mrp}",
                            created_by=request.user,
                        )

                    messages.success(
                        request, f"Successfully updated {variant.full_name}"
                    )
                    return redirect("inventory:variant_details", pk=pk)
            except Exception as e:
                logger.error(f"Error updating variant: {str(e)}")
                messages.error(request, f"Error updating variant: {str(e)}")
    else:
        form = VariantForm(instance=variant)
        logger.error(f"Form invalid: {form.errors}")
        messages.error(request, "Please correct the errors below.")

    context = {
        "form": form,
        "variant": variant,
        "title": f"Update {variant.full_name}",
        "subtitle": "Update variant details and pricing",
    }
    return render(request, "inventory/variant_update.html", context)


@login_required
def supplier_invoice_tracking(request):
    """Optimized view to track inventory by supplier invoice"""

    search_query = request.GET.get("search", "")
    supplier_filter = request.GET.get("supplier", "")
    sort_by = request.GET.get("sort", "-invoice_date")

    # Base queryset: work at SupplierInvoice level instead of InventoryLog
    supplier_invoices = SupplierInvoice.objects.filter(is_deleted=False).annotate(
        stock_in=Coalesce(
            Sum(
                Case(
                    When(
                        inventory_logs__transaction_type__in=["STOCK_IN", "INITIAL"],
                        then=F("inventory_logs__quantity_change"),
                    ),
                    default=Decimal("0"),
                    output_field=models.DecimalField(),
                )
            ),
            Decimal("0"),
        ),
        sales=Coalesce(
            Sum(
                Case(
                    When(
                        inventory_logs__transaction_type="SALE",
                        then=Abs(F("inventory_logs__quantity_change")),
                    ),
                    default=Decimal("0"),
                    output_field=models.DecimalField(),
                )
            ),
            Decimal("0"),
        )
        - Coalesce(
            Sum(
                Case(
                    When(
                        inventory_logs__transaction_type="RETURN",
                        then=Abs(F("inventory_logs__quantity_change")),
                    ),
                    default=Decimal("0"),
                    output_field=models.DecimalField(),
                )
            ),
            Decimal("0"),
        )
        - Coalesce(
            Sum(
                Case(
                    When(
                        inventory_logs__transaction_type="DAMAGE",
                        then=Abs(F("inventory_logs__quantity_change")),
                    ),
                    default=Decimal("0"),
                    output_field=models.DecimalField(),
                )
            ),
            Decimal("0"),
        ),
        products_count=Count(
            "inventory_logs__variant__product",
            filter=Q(inventory_logs__transaction_type__in=["STOCK_IN", "INITIAL"]),
            distinct=True,
        ),
    )

    # Apply search filter
    if search_query:
        supplier_invoices = supplier_invoices.filter(
            Q(invoice_number__icontains=search_query)
            | Q(supplier__name__icontains=search_query)
        )

    # Apply supplier filter
    if supplier_filter:
        supplier_invoices = supplier_invoices.filter(supplier_id=supplier_filter)

    # Apply sorting
    ordering_map = {
        "supplier_name": "supplier__name",
        "-supplier_name": "-supplier__name",
        "invoice_date": "invoice_date",
        "-invoice_date": "-invoice_date",
        "stock_in_quantity": "stock_in",
        "-stock_in_quantity": "-stock_in",
        "sales_quantity": "sales",
        "-sales_quantity": "-sales",
    }
    supplier_invoices = supplier_invoices.order_by(
        ordering_map.get(sort_by, "-invoice_date")
    )

    # Prepare summaries in Python
    invoice_summaries = []
    for invoice in supplier_invoices:
        stock_in = invoice.stock_in or 0
        sales = invoice.sales or 0
        remaining = stock_in - sales
        remaining_percentage = (
            round(100 - (remaining / stock_in) * 100, 2) if stock_in > 0 else 0
        )

        invoice_summaries.append(
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "supplier_name": invoice.supplier.name,
                "invoice_date": invoice.invoice_date,
                "total_amount": invoice.total_amount,
                "stock_in_quantity": stock_in,
                "sales_quantity": sales,
                "remaining_quantity": remaining,
                "remaining_percentage": remaining_percentage,
                "products_count": invoice.products_count,
            }
        )

    suppliers = Supplier.objects.filter(is_deleted=False).order_by("name")

    return render(
        request,
        "inventory/supplier_invoice_tracking.html",
        {
            "invoice_summaries": invoice_summaries,
            "title": "Supplier Invoice Tracking",
            "search_query": search_query,
            "supplier_filter": supplier_filter,
            "sort_by": sort_by,
            "suppliers": suppliers,
        },
    )


@login_required
def supplier_invoice_details(request, invoice_id):
    """View to show detailed breakdown of a specific supplier invoice"""

    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    sort_by = request.GET.get("sort", "-stock_in_quantity")

    # Build base queryset for products in this invoice
    base_filter = {
        "supplier_invoice__id": invoice_id,
        "transaction_type__in": ["STOCK_IN", "INITIAL"],
    }

    # Get products with stock-in data
    products_query = (
        InventoryLog.objects.filter(**base_filter)
        .values(
            "variant__product__brand",
            "variant__product__name",
            "variant__size__name",
            "variant__color__name",
            "variant__barcode",
            "variant__id",
        )
        .annotate(
            stock_in_quantity=Sum("quantity_change"),
            purchase_price=Sum("purchase_price"),
        )
    )

    # Apply search filter
    if search_query:
        products_query = products_query.filter(
            Q(variant__product__brand__icontains=search_query)
            | Q(variant__product__name__icontains=search_query)
            | Q(variant__barcode__icontains=search_query)
        )

    # Apply sorting for stock-in data
    sort_mapping = {
        "brand": "variant__product__brand",
        "-brand": "-variant__product__brand",
        "stock_in_quantity": "stock_in_quantity",
        "-stock_in_quantity": "-stock_in_quantity",
    }

    order_field = sort_mapping.get(sort_by, "-stock_in_quantity")
    products_in_invoice = list(products_query.order_by(order_field))

    # Get sales data for all products in one query (including returns and damages)
    barcodes = [p["variant__barcode"] for p in products_in_invoice]
    sales_data = {}
    if barcodes:
        sales_queryset = (
            InventoryLog.objects.filter(
                supplier_invoice__id=invoice_id,
                variant__barcode__in=barcodes,
            )
            .values("variant__barcode")
            .annotate(
                total_sales=Coalesce(
                    Sum(
                        Case(
                            When(transaction_type="SALE", then=F("quantity_change")),
                            default=Decimal("0"),
                            output_field=models.DecimalField(),
                        )
                    ),
                    Decimal("0"),
                )
                + Coalesce(
                    Sum(
                        Case(
                            When(transaction_type="RETURN", then=F("quantity_change")),
                            default=Decimal("0"),
                            output_field=models.DecimalField(),
                        )
                    ),
                    Decimal("0"),
                )
                - Coalesce(
                    Sum(
                        Case(
                            When(transaction_type="DAMAGE", then=F("quantity_change")),
                            default=Decimal("0"),
                            output_field=models.DecimalField(),
                        )
                    ),
                    Decimal("0"),
                )
            )
        )
        sales_data = {
            item["variant__barcode"]: abs(item["total_sales"] or 0)
            for item in sales_queryset
        }

    # Add sales and remaining quantities to products
    for product in products_in_invoice:
        barcode = product["variant__barcode"]
        sales_quantity = sales_data.get(barcode, 0)
        product["sales_quantity"] = sales_quantity
        product["remaining_quantity"] = product["stock_in_quantity"] - sales_quantity

    # Apply status filter after calculating remaining quantities
    if status_filter == "sold_out":
        products_in_invoice = [
            p for p in products_in_invoice if p["remaining_quantity"] <= 0
        ]
    elif status_filter == "in_stock":
        products_in_invoice = [
            p for p in products_in_invoice if p["remaining_quantity"] > 0
        ]
    elif status_filter == "low_stock":
        products_in_invoice = [
            p for p in products_in_invoice if 0 < p["remaining_quantity"] <= 5
        ]

    # Apply additional sorting after calculating sales quantities
    if sort_by in [
        "sales_quantity",
        "-sales_quantity",
        "remaining_quantity",
        "-remaining_quantity",
    ]:
        reverse = sort_by.startswith("-")
        field = sort_by.lstrip("-")
        products_in_invoice.sort(key=lambda x: x[field], reverse=reverse)

    # Single query for totals using aggregation
    totals = InventoryLog.objects.filter(supplier_invoice__id=invoice_id).aggregate(
        total_sales=Coalesce(
            Sum(
                Case(
                    When(transaction_type="SALE", then=F("quantity_change")),
                    default=Decimal("0"),
                    output_field=models.DecimalField(),
                )
            )
            + Sum(
                Case(
                    When(transaction_type="RETURN", then=F("quantity_change")),
                    default=Decimal("0"),
                    output_field=models.DecimalField(),
                )
            )
            - Sum(
                Case(
                    When(transaction_type="DAMAGE", then=F("quantity_change")),
                    default=Decimal("0"),
                    output_field=models.DecimalField(),
                )
            ),
            Decimal("0"),
        ),
        total_stock_in=Coalesce(
            Sum(
                Case(
                    When(
                        transaction_type__in=["STOCK_IN", "INITIAL"],
                        then=F("quantity_change"),
                    ),
                    default=Decimal("0"),
                    output_field=models.DecimalField(),
                )
            ),
            Decimal("0"),
        ),
    )

    # Get invoice info in single query
    invoice_info = (
        InventoryLog.objects.filter(supplier_invoice__id=invoice_id)
        .select_related("supplier_invoice__supplier")
        .values(
            "supplier_invoice__supplier__name",
            "supplier_invoice__invoice_date",
            "supplier_invoice__invoice_number",
        )
        .first()
    )

    context = {
        "invoice_number": invoice_info["supplier_invoice__invoice_number"],
        "invoice_info": invoice_info,
        "products_in_invoice": products_in_invoice,
        "title": f"Invoice - {invoice_info['supplier_invoice__invoice_number']}",
        "total_sales": abs(totals["total_sales"]),
        "total_stock_in": totals["total_stock_in"],
        "total_remaining": totals["total_stock_in"] - abs(totals["total_sales"]),
        "search_query": search_query,
        "status_filter": status_filter,
        "sort_by": sort_by,
    }
    return render(request, "inventory/supplier_invoice_details.html", context)


@login_required
def product_invoice_analytics(request, variant_id):
    """View to show analytics for a specific product variant by supplier invoice"""

    variant = get_object_or_404(ProductVariant, id=variant_id)

    # Get all supplier invoices for this variant
    invoices = (
        InventoryLog.objects.filter(variant=variant, supplier_invoice__isnull=False)
        .values("supplier_invoice__invoice_number", "supplier_invoice__supplier__name")
        .distinct()
    )

    analytics = []
    for invoice in invoices:
        invoice_number = invoice["supplier_invoice__invoice_number"]
        supplier_name = invoice["supplier_invoice__supplier__name"]

        # Get stock in for this invoice
        stock_in_logs = InventoryLog.objects.filter(
            variant=variant,
            supplier_invoice__invoice_number=invoice_number,
            transaction_type__in=["STOCK_IN", "INITIAL"],
        )

        # Get sales for this invoice
        sales_logs = InventoryLog.objects.filter(
            product_variant=variant,
            supplier_invoice__invoice_number=invoice_number,
            transaction_type="SALE",
        )

        # Calculate metrics
        total_stock_in = (
            stock_in_logs.aggregate(total=Sum("quantity_change"))["total"] or 0
        )
        total_sales = abs(
            sales_logs.aggregate(total=Sum("quantity_allocated"))["total"] or 0
        )
        remaining = total_stock_in - total_sales

        # Calculate movement rate
        if stock_in_logs.exists():
            first_stock_in = stock_in_logs.order_by("timestamp").first()
            days_since_stock_in = (timezone.now() - first_stock_in.timestamp).days
            movement_rate = (
                total_sales / max(days_since_stock_in, 1)
                if days_since_stock_in > 0
                else 0
            )
        else:
            movement_rate = 0
            days_since_stock_in = 0

        analytics.append(
            {
                "invoice_number": invoice_number,
                "supplier_name": supplier_name,
                "total_stock_in": total_stock_in,
                "total_sales": total_sales,
                "remaining_quantity": remaining,
                "movement_rate": round(movement_rate, 2),
                "days_since_stock_in": days_since_stock_in,
            }
        )

    context = {
        "variant": variant,
        "analytics": analytics,
        "title": f"{variant.simple_name} - Invoice Analytics",
    }
    return render(request, "inventory/product_invoice_analytics.html", context)


@login_required
def supplier_analytics(request, supplier_id):
    """View to show analytics for a specific supplier"""

    supplier = get_object_or_404(Supplier, id=supplier_id)

    # Get all invoices for this supplier
    invoices = (
        InventoryLog.objects.filter(
            supplier_invoice__supplier=supplier,
            transaction_type__in=["STOCK_IN", "INITIAL"],
        )
        .values("supplier_invoice__invoice_number", "supplier_invoice__invoice_date")
        .distinct()
        .order_by("-supplier_invoice__invoice_date")
    )

    movement_data = []
    for invoice in invoices:
        invoice_number = invoice["supplier_invoice__invoice_number"]
        invoice_date = invoice["supplier_invoice__invoice_date"]

        # Get stock in for this invoice
        stock_in = (
            InventoryLog.objects.filter(
                supplier_invoice__invoice_number=invoice_number,
                transaction_type__in=["STOCK_IN", "INITIAL"],
            ).aggregate(total=Sum("quantity_change"))["total"]
            or 0
        )

        # Get sales for this invoice
        sales = abs(
            InventoryLog.objects.filter(
                supplier_invoice__invoice_number=invoice_number,
                transaction_type="SALE",
            ).aggregate(total=Sum("quantity_allocated"))["total"]
            or 0
        )

        # Calculate days since invoice
        days_since = (timezone.now() - invoice_date).days

        movement_data.append(
            {
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "stock_in_quantity": stock_in,
                "sales_quantity": sales,
                "remaining_quantity": stock_in - sales,
                "days_since_invoice": days_since,
                "movement_rate": sales / max(days_since, 1) if days_since > 0 else 0,
            }
        )

    context = {
        "supplier": supplier,
        "movement_data": movement_data,
        "title": f"{supplier.name} - Analytics",
    }
    return render(request, "inventory/supplier_analytics.html", context)
