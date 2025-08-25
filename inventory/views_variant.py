from django.shortcuts import render, get_object_or_404
from .models import ProductVariant, InventoryLog, Product
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from .forms import VariantForm
from django.db import IntegrityError
from .services import InventoryService
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from .forms import StockInForm, AdjustmentInForm, AdjustmentOutForm, DamageForm


def variant_home(request):
    variants = ProductVariant.objects.all().order_by("-created_at")
    return render(request, "inventory/product_variant/home.html", {"data": variants})


def variant_details(request, variant_id):
    """Detailed view for a single product variant with stock management options"""
    from django.shortcuts import get_object_or_404

    variant = get_object_or_404(ProductVariant, id=variant_id)

    # Get recent activity logs for this variant (only for active variants)
    recent_logs = (
        variant.inventory_logs.filter(variant__is_deleted=False)
        .select_related("supplier_invoice", "supplier_invoice__supplier")
        .order_by("-timestamp")[:20]
    )

    # Calculate stock statistics
    stock_stats = {
        "total_quantity": variant.total_quantity,
        "available_quantity": variant.available_quantity,
        "damaged_quantity": variant.damaged_quantity,
        "damage_percentage": variant.damage_percentage,
        "stock_health": variant.stock_health,
        "profit_margin": variant.profit_margin,
        "total_value": variant.total_value,
        "damaged_value": variant.damaged_value,
    }

    context = {
        "variant": variant,
        "product": variant.product,
        "recent_logs": recent_logs,
        "stock_stats": stock_stats,
    }

    return render(request, "inventory/product_variant/details.html", context)


class CreateProductVariant(CreateView):
    template_name = "inventory/product_variant/form.html"
    form_class = VariantForm
    model = ProductVariant
    title = "Create Product Variant"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        product = Product.objects.get(id=self.kwargs["product_id"])
        context["product"] = product
        context["gst_rate"] = product.gst_percentage

        # Check if this is the first variant for this product
        existing_variants = ProductVariant.objects.filter(product=product)
        context["is_first_variant"] = (
            existing_variants.count() == 0 if existing_variants.exists() else True
        )

        # Add existing variants to context for reference
        if existing_variants.exists():
            context["existing_variants"] = existing_variants
            context["latest_variant"] = existing_variants.latest(
                "created_at"
            )  # Assuming you have a created_at field

        return context

    def get_initial(self):
        """Set initial values for the form"""
        initial = super().get_initial()

        # Get the product
        product = Product.objects.get(id=self.kwargs["product_id"])
        # Check if this is the first variant
        existing_variants = ProductVariant.objects.filter(product=product)

        if existing_variants.exists():
            # For subsequent variants, copy data from the most recent variant
            # You can change this logic to copy from a specific variant if needed
            latest_variant = existing_variants.latest(
                "created_at"
            )  # or use 'id' if no created_at field

            initial.update(
                {
                    "purchase_price": latest_variant.purchase_price,
                    "mrp": latest_variant.mrp,
                    "discount_percentage": latest_variant.discount_percentage,
                    "quantity": 0,
                }
            )

        return initial

    def form_valid(self, form):
        # Get the product
        product = Product.objects.get(id=self.kwargs["product_id"])

        # Save the variant
        variant = form.save(commit=False)
        variant.product = product
        variant.created_by = self.request.user

        try:
            variant.save()
        except IntegrityError as e:
            # Check if it's a unique constraint violation
            if "unique_product" in str(e):
                # Determine which fields are causing the conflict
                size = form.cleaned_data.get("size")
                color = form.cleaned_data.get("color")

                if size and color:
                    error_msg = f"A variant with size '{size}' and color '{color}' already exists for this product."
                elif size:
                    error_msg = (
                        f"A variant with size '{size}' already exists for this product."
                    )
                elif color:
                    error_msg = f"A variant with color '{color}' already exists for this product."
                else:
                    error_msg = "A variant without size and color already exists for this product."

                form.add_error(None, error_msg)
                return self.form_invalid(form)
            else:
                # Re-raise if it's a different integrity error
                raise

        # Create inventory log for initial stock
        InventoryService.create_initial_log(
            variant,
            self.request.user,
            "Initial stock",
            form.cleaned_data.get("supplier_invoice"),
        )

        messages.success(self.request, f"Product variant created successfully")

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy(
            "inventory_products:details", kwargs={"product_id": self.object.product.id}
        )


class EditProductVariant(UpdateView):
    template_name = "inventory/product_variant/form.html"
    form_class = VariantForm
    model = ProductVariant
    title = "Edit Product Variant"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["variant"] = self.object
        context["gst_rate"] = self.object.product.gst_percentage
        return context

    def form_valid(self, form):

        try:
            with transaction.atomic():
                variant = form.save(commit=False)
                variant.updated_by = self.request.user
                variant.save()

                InventoryService.update_initial_log(
                    variant, self.request.user, "Initial stock"
                )

            messages.success(self.request, "Product variant updated successfully")
            return super().form_valid(form)

        except IntegrityError as e:
            # Check if it's a unique constraint violation
            if "unique_product" in str(e):
                # Determine which fields are causing the conflict
                size = form.cleaned_data.get("size")
                color = form.cleaned_data.get("color")

                if size and color:
                    error_msg = f"A variant with size '{size}' and color '{color}' already exists for this product."
                elif size:
                    error_msg = (
                        f"A variant with size '{size}' already exists for this product."
                    )
                elif color:
                    error_msg = f"A variant with color '{color}' already exists for this product."
                else:
                    error_msg = "A variant without size and color already exists for this product."

                form.add_error(None, error_msg)
                return self.form_invalid(form)
            else:
                # Re-raise if it's a different integrity error
                raise

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy(
            "inventory_products:details", kwargs={"product_id": self.object.product.id}
        )


class StockInCreate(LoginRequiredMixin, CreateView):
    template_name = "inventory/product_variant/inventory_operation_form.html"
    form_class = StockInForm
    model = InventoryLog

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Stock In"
        context["operation_type"] = "stock_in"

        # Get the variant if variant_id is provided
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_deleted=False)
                context["selected_variant"] = variant
            except ProductVariant.DoesNotExist:
                messages.error(self.request, "Selected variant not found.")

        return context

    def get_initial(self):
        initial = super().get_initial()
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_deleted=False)
                initial["variant"] = variant
                initial["purchase_price"] = variant.purchase_price
                initial["mrp"] = variant.mrp
            except ProductVariant.DoesNotExist:
                messages.error(self.request, "Selected variant not found.")
        return initial

    def get_success_url(self):
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            return reverse_lazy("inventory:variant_details", kwargs={"pk": variant_id})
        else:
            # If no variant_id, redirect to products page
            messages.error(
                self.request,
                "Please select a variant from the variant details page.",
            )
            return redirect("inventory:product_home")

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Get the variant
                variant_id = self.kwargs.get("variant_id")
                if variant_id:
                    variant = get_object_or_404(
                        ProductVariant, id=variant_id, is_deleted=False
                    )
                else:
                    # If no variant_id, redirect to products page
                    messages.error(
                        self.request,
                        "Please select a variant from the variant details page.",
                    )
                    return redirect("inventory:product_home")

                # Use InventoryService instead of direct method call
                inventory_log = InventoryService.update_stock_in_log(
                    variant,
                    quantity_change=form.cleaned_data.get("quantity_change"),
                    user=self.request.user,
                    notes=form.cleaned_data.get("notes"),
                    supplier_invoice=form.cleaned_data.get("supplier_invoice"),
                    purchase_price=form.cleaned_data.get("purchase_price"),
                    mrp=form.cleaned_data.get("mrp"),
                )

                if inventory_log:
                    messages.success(
                        self.request,
                        f"Stock in entry created successfully. {form.cleaned_data.get('quantity_change')} units added to {variant.full_name}",
                    )
                    return redirect(self.get_success_url())
                else:
                    messages.error(self.request, "Failed to create stock in entry.")
                    return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error creating stock in entry: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        print(form.errors)
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class AdjustmentInCreate(LoginRequiredMixin, CreateView):
    template_name = "inventory/product_variant/inventory_operation_form.html"
    form_class = AdjustmentInForm
    model = InventoryLog

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Adjustment In"
        context["operation_type"] = "adjustment_in"

        # Get the variant if variant_id is provided
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_deleted=False)
                context["selected_variant"] = variant
            except ProductVariant.DoesNotExist:
                messages.error(self.request, "Selected variant not found.")

        return context

    def get_initial(self):
        initial = super().get_initial()
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_deleted=False)
                initial["variant"] = variant
            except ProductVariant.DoesNotExist:
                messages.error(self.request, "Selected variant not found.")
        return initial

    def get_success_url(self):
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            return reverse_lazy("inventory:variant_details", kwargs={"pk": variant_id})
        return reverse_lazy("inventory:product_home")

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Get the variant
                variant_id = self.kwargs.get("variant_id")
                if variant_id:
                    variant = get_object_or_404(
                        ProductVariant, id=variant_id, is_deleted=False
                    )
                else:
                    # If no variant_id, redirect to products page
                    messages.error(
                        self.request,
                        "Please select a variant from the variant details page.",
                    )
                    return redirect("inventory:product_home")

                # Use InventoryService instead of direct method call
                InventoryService.adjust_in_quantity(
                    variant,
                    change=form.cleaned_data.get("quantity_change"),
                    user=self.request.user,
                    notes=form.cleaned_data.get("notes"),
                )

                messages.success(
                    self.request,
                    f"Adjustment in entry created successfully. {form.cleaned_data.get('quantity_change')} units added to {variant.full_name}",
                )
                return redirect(self.get_success_url())
        except Exception as e:
            print(e)
            messages.error(
                self.request, f"Error creating adjustment in entry: {str(e)}"
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class AdjustmentOutCreate(LoginRequiredMixin, CreateView):
    template_name = "inventory/product_variant/inventory_operation_form.html"
    form_class = AdjustmentOutForm
    model = InventoryLog

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Adjustment Out"
        context["operation_type"] = "adjustment_out"

        # Get the variant if variant_id is provided
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_deleted=False)
                context["selected_variant"] = variant
            except ProductVariant.DoesNotExist:
                messages.error(self.request, "Selected variant not found.")

        return context

    def get_initial(self):
        initial = super().get_initial()
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_deleted=False)
                initial["variant"] = variant
            except ProductVariant.DoesNotExist:
                messages.error(self.request, "Selected variant not found.")
        return initial

    def get_success_url(self):
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            return reverse_lazy("inventory:variant_details", kwargs={"pk": variant_id})
        return reverse_lazy("inventory:product_home")

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Get the variant
                variant_id = self.kwargs.get("variant_id")
                if variant_id:
                    variant = get_object_or_404(
                        ProductVariant, id=variant_id, is_deleted=False
                    )
                else:
                    # If no variant_id, redirect to operations page
                    messages.error(
                        self.request,
                        "Please select a variant from the variant details page.",
                    )
                    return redirect("inventory:product_home")

                # Use InventoryService instead of direct method call
                InventoryService.adjust_out_quantity(
                    variant,
                    change=form.cleaned_data.get("quantity_change"),
                    user=self.request.user,
                    notes=form.cleaned_data.get("notes"),
                )

                messages.success(
                    self.request,
                    f"Adjustment out entry created successfully. {form.cleaned_data.get('quantity_change')} units removed from {variant.full_name}",
                )
                return redirect(self.get_success_url())
        except Exception as e:
            print(e)
            messages.error(
                self.request, f"Error creating adjustment out entry: {str(e)}"
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class DamageCreate(LoginRequiredMixin, CreateView):
    template_name = "inventory/product_variant/inventory_operation_form.html"
    form_class = DamageForm
    model = InventoryLog

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Mark as Damaged"
        context["operation_type"] = "damage"

        # Get the variant if variant_id is provided
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_deleted=False)
                context["selected_variant"] = variant
            except ProductVariant.DoesNotExist:
                messages.error(self.request, "Selected variant not found.")

        return context

    def get_initial(self):
        initial = super().get_initial()
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, is_deleted=False)
                initial["variant"] = variant
            except ProductVariant.DoesNotExist:
                messages.error(self.request, "Selected variant not found.")
        return initial

    def get_success_url(self):
        variant_id = self.kwargs.get("variant_id")
        if variant_id:
            return reverse_lazy("inventory:variant_details", kwargs={"pk": variant_id})
        return reverse_lazy("inventory:product_home")

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Get the variant
                variant_id = self.kwargs.get("variant_id")
                if variant_id:
                    variant = get_object_or_404(
                        ProductVariant, id=variant_id, is_deleted=False
                    )
                else:
                    # If no variant_id, redirect to operations page
                    messages.error(
                        self.request,
                        "Please select a variant from the variant details page.",
                    )
                    return redirect("inventory:product_home")

                # Use InventoryService instead of direct method call
                InventoryService.mark_as_damaged(
                    variant,
                    quantity_damaged=form.cleaned_data.get("quantity_change"),
                    user=self.request.user,
                    notes=form.cleaned_data.get("notes"),
                )

                messages.success(
                    self.request,
                    f"Damage entry created successfully. {form.cleaned_data.get('quantity_change')} units marked as damaged for {variant.full_name}",
                )
                return redirect(self.get_success_url())
        except Exception as e:
            print(e)
            messages.error(self.request, f"Error creating damage entry: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
