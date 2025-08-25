from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, F
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import View, UpdateView, CreateView, DeleteView

from django.db import transaction, IntegrityError
from django.urls import reverse_lazy
from .services import InventoryService
from .forms import (
    ProductForm,
    VariantForm,
    StockInForm,
    AdjustmentInForm,
    AdjustmentOutForm,
    DamageForm,
)
from .models import Product, ProductVariant, InventoryLog


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
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["product_form"] = self.product_form
        context["variant_form"] = self.variant_form
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
                return redirect("inventory:product_home")
        else:
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
                messages.error(request, f"Error updating variant: {str(e)}")
    else:
        form = VariantForm(instance=variant)

    context = {
        "form": form,
        "variant": variant,
        "title": f"Update {variant.full_name}",
        "subtitle": "Update variant details and pricing",
    }
    return render(request, "inventory/variant_update.html", context)



@login_required
def supplier_invoice_tracking(request):
    """View to track inventory by supplier invoice"""
    from django.db.models import Sum, Count, Q
    from supplier.models import SupplierInvoice, Supplier

    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    supplier_filter = request.GET.get("supplier", "")
    sort_by = request.GET.get("sort", "-invoice_date")

    # Base queryset
    supplier_invoices = (
        InventoryLog.objects.filter(
            supplier_invoice__isnull=False, transaction_type__in=["STOCK_IN", "INITIAL"]
        )
        .values(
            "supplier_invoice__invoice_number",
            "supplier_invoice__supplier__name",
            "supplier_invoice__invoice_date",
            "supplier_invoice__total_amount",
        )
        .distinct()
    )

    # Apply search filter
    if search_query:
        supplier_invoices = supplier_invoices.filter(
            Q(supplier_invoice__invoice_number__icontains=search_query)
            | Q(supplier_invoice__supplier__name__icontains=search_query)
        )

    # Apply supplier filter
    if supplier_filter:
        supplier_invoices = supplier_invoices.filter(
            supplier_invoice__supplier_id=supplier_filter
        )

    # Apply sorting
    if sort_by == "supplier_name":
        supplier_invoices = supplier_invoices.order_by(
            "supplier_invoice__supplier__name"
        )
    elif sort_by == "-supplier_name":
        supplier_invoices = supplier_invoices.order_by(
            "-supplier_invoice__supplier__name"
        )
    elif sort_by == "invoice_date":
        supplier_invoices = supplier_invoices.order_by("supplier_invoice__invoice_date")
    elif sort_by == "-invoice_date":
        supplier_invoices = supplier_invoices.order_by(
            "-supplier_invoice__invoice_date"
        )
    elif sort_by == "stock_in_quantity":
        supplier_invoices = supplier_invoices.order_by("stock_in_quantity")
    elif sort_by == "-stock_in_quantity":
        supplier_invoices = supplier_invoices.order_by("-stock_in_quantity")
    else:
        supplier_invoices = supplier_invoices.order_by(
            "-supplier_invoice__invoice_date"
        )

    invoice_summaries = []
    for invoice in supplier_invoices:
        invoice_number = invoice["supplier_invoice__invoice_number"]
        supplier_name = invoice["supplier_invoice__supplier__name"]

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
                supplier_invoice__invoice_number=invoice_number, transaction_type="SALE"
            ).aggregate(total=Sum("quantity_change"))["total"]
            or 0
        )

        sales_data = InventoryLog.objects.filter(
            transaction_type="SALE", supplier_invoice__invoice_number=invoice_number
        )

        print(sales_data)

        # Get unique products in this invoice
        products_count = (
            InventoryLog.objects.filter(
                supplier_invoice__invoice_number=invoice_number,
                transaction_type__in=["STOCK_IN", "INITIAL"],
            )
            .values("variant__product__brand", "variant__product__name")
            .distinct()
            .count()
        )

        remaining = stock_in - sales

        invoice_summaries.append(
            {
                "invoice_number": invoice_number,
                "supplier_name": supplier_name,
                "invoice_date": invoice["supplier_invoice__invoice_date"],
                "total_amount": invoice["supplier_invoice__total_amount"],
                "stock_in_quantity": stock_in,
                "sales_quantity": sales,
                "remaining_quantity": remaining,
                "products_count": products_count,
            }
        )

    # Get suppliers for filter dropdown
    suppliers = Supplier.objects.filter(is_deleted=False).order_by("name")

    context = {
        "invoice_summaries": invoice_summaries,
        "title": "Supplier Invoice Tracking",
        "search_query": search_query,
        "supplier_filter": supplier_filter,
        "sort_by": sort_by,
        "suppliers": suppliers,
    }
    return render(request, "inventory/supplier_invoice_tracking.html", context)


@login_required
def supplier_invoice_details(request, invoice_number):
    """View to show detailed breakdown of a specific supplier invoice"""
    from django.db.models import Sum, Q

    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    sort_by = request.GET.get("sort", "-stock_in_quantity")

    # Get all products in this invoice
    products_in_invoice = (
        InventoryLog.objects.filter(
            supplier_invoice__invoice_number=invoice_number,
            transaction_type__in=["STOCK_IN", "INITIAL"],
        )
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
        products_in_invoice = products_in_invoice.filter(
            Q(variant__product__brand__icontains=search_query)
            | Q(variant__product__name__icontains=search_query)
            | Q(variant__barcode__icontains=search_query)
        )

    # Apply status filter
    if status_filter:
        if status_filter == "sold_out":
            # Filter products that are sold out (remaining = 0)
            pass  # Will filter after calculating remaining
        elif status_filter == "in_stock":
            # Filter products that have remaining stock
            pass  # Will filter after calculating remaining
        elif status_filter == "low_stock":
            # Filter products with low remaining stock (less than 5)
            pass  # Will filter after calculating remaining

    # Apply sorting
    if sort_by == "brand":
        products_in_invoice = products_in_invoice.order_by("variant__product__brand")
    elif sort_by == "-brand":
        products_in_invoice = products_in_invoice.order_by("-variant__product__brand")
    elif sort_by == "stock_in_quantity":
        products_in_invoice = products_in_invoice.order_by("stock_in_quantity")
    elif sort_by == "-stock_in_quantity":
        products_in_invoice = products_in_invoice.order_by("-stock_in_quantity")
    elif sort_by == "sales_quantity":
        products_in_invoice = products_in_invoice.order_by("sales_quantity")
    elif sort_by == "-sales_quantity":
        products_in_invoice = products_in_invoice.order_by("-sales_quantity")
    else:
        products_in_invoice = products_in_invoice.order_by("-stock_in_quantity")

    # Get sales for each product in this invoice
    for product in products_in_invoice:
        barcode = product["variant__barcode"]

        # Get sales for this specific product from this invoice
        sales = abs(
            InventoryLog.objects.filter(
                supplier_invoice__invoice_number=invoice_number,
                variant__barcode=barcode,
                transaction_type="SALE",
            ).aggregate(total=Sum("quantity_change"))["total"]
            or 0
        )

        product["sales_quantity"] = sales
        product["remaining_quantity"] = product["stock_in_quantity"] - sales

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

    # Get invoice info
    invoice_info = (
        InventoryLog.objects.filter(supplier_invoice__invoice_number=invoice_number)
        .values("supplier_invoice__supplier__name", "supplier_invoice__invoice_date")
        .first()
    )

    context = {
        "invoice_number": invoice_number,
        "invoice_info": invoice_info,
        "products_in_invoice": products_in_invoice,
        "title": f"Invoice {invoice_number} Details",
        "search_query": search_query,
        "status_filter": status_filter,
        "sort_by": sort_by,
    }
    return render(request, "inventory/supplier_invoice_details.html", context)


@login_required
def product_invoice_analytics(request, variant_id):
    """View to show analytics for a specific product variant by supplier invoice"""
    from django.db.models import Sum
    from django.utils import timezone

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
            variant=variant,
            supplier_invoice__invoice_number=invoice_number,
            transaction_type="SALE",
        )

        # Calculate metrics
        total_stock_in = (
            stock_in_logs.aggregate(total=Sum("quantity_change"))["total"] or 0
        )
        total_sales = abs(
            sales_logs.aggregate(total=Sum("quantity_change"))["total"] or 0
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
    from django.db.models import Sum
    from django.utils import timezone
    from supplier.models import Supplier

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
                supplier_invoice__invoice_number=invoice_number, transaction_type="SALE"
            ).aggregate(total=Sum("quantity_change"))["total"]
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
