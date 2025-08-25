from django.shortcuts import render, get_object_or_404
from .models import Product, ProductVariant, InventoryLog
from django.db.models import Sum, F
from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView, UpdateView
from .forms import ProductForm


def product_home(request):
    products = Product.objects.all()
    return render(request, "inventory/product/home.html", {"data": products})


def product_details(request, product_id):
    """Display detailed product information with variants and statistics"""

    product = get_object_or_404(Product, id=product_id)

    # Get all variants for this product
    variants = (
        ProductVariant.objects.filter(product=product)
        .select_related("size", "color")
        .order_by("size__name", "color__name")
    )

    # Calculate statistics
    total_variants = variants.count()
    active_variants = variants.filter(
        status=ProductVariant.VariantStatus.ACTIVE
    ).count()
    out_of_stock = variants.filter(
        quantity=0, status=ProductVariant.VariantStatus.ACTIVE
    ).count()
    low_stock = variants.filter(
        quantity__lte=F("minimum_quantity"),
        status=ProductVariant.VariantStatus.ACTIVE,
    ).count()

    # Calculate inventory values
    total_quantity = variants.aggregate(total=Sum("quantity"))["total"] or 0

    total_damaged = variants.aggregate(total=Sum("damaged_quantity"))["total"] or 0

    total_inventory_value = (
        variants.aggregate(total=Sum(F("quantity") * F("purchase_price")))["total"] or 0
    )

    total_damaged_value = (
        variants.aggregate(total=Sum(F("damaged_quantity") * F("purchase_price")))[
            "total"
        ]
        or 0
    )

    # Get recent inventory logs for this product (only for active variants)
    recent_logs = (
        InventoryLog.objects.filter(variant__product=product, variant__is_deleted=False)
        .select_related(
            "variant", "created_by", "supplier_invoice", "supplier_invoice__supplier"
        )
        .order_by("-timestamp")[:10]
    )

    context = {
        "product": product,
        "variants": variants,
        "total_variants": total_variants,
        "active_variants": active_variants,
        "out_of_stock": out_of_stock,
        "low_stock": low_stock,
        "total_quantity": total_quantity,
        "total_damaged": total_damaged,
        "total_inventory_value": total_inventory_value,
        "total_damaged_value": total_damaged_value,
        "recent_logs": recent_logs,
    }

    return render(request, "inventory/product/details.html", context)


class CreateProduct(CreateView):
    template_name = "inventory/product/form.html"
    form_class = ProductForm
    model = Product
    title = "Create Product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        return context

    def form_valid(self, form):
        messages.success(self.request, "Product created successfully")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("inventory_products:home")


class EditProduct(UpdateView):
    template_name = "inventory/product/form.html"
    form_class = ProductForm
    model = Product
    title = "Edit Product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        return context

    def form_valid(self, form):
        messages.success(self.request, "Product updated successfully")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse(
            "inventory_products:details", kwargs={"product_id": self.object.id}
        )
