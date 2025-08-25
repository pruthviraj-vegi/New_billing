from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import  timedelta
from .models import (
    Supplier,
    SupplierInvoice,
    SupplierPayment,
    SupplierPaymentAllocation,
)
from .forms import (
    SupplierForm,
    SupplierInvoiceForm,
    SupplierPaymentForm,
    SupplierPaymentAllocationForm,
)


@login_required
def dashboard(request):
    """Supplier management dashboard with analytics and insights."""

    # Get date range filter (default to current month)
    date_filter = request.GET.get("date_filter", "current_month")

    # Calculate date ranges
    today = timezone.now().date()
    if date_filter == "current_month":
        start_date = today.replace(day=1)
        end_date = today
    elif date_filter == "last_month":
        last_month = today.replace(day=1) - timedelta(days=1)
        start_date = last_month.replace(day=1)
        end_date = today.replace(day=1) - timedelta(days=1)
    elif date_filter == "last_3_months":
        start_date = today - timedelta(days=90)
        end_date = today
    elif date_filter == "last_6_months":
        start_date = today - timedelta(days=180)
        end_date = today
    elif date_filter == "current_year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        start_date = today.replace(day=1)
        end_date = today

    # Overall Statistics
    total_suppliers = Supplier.objects.filter(is_deleted=False).count()
    active_suppliers = Supplier.objects.filter(is_deleted=False).count()
    inactive_suppliers = Supplier.objects.filter(is_deleted=True).count()

    # Financial Statistics
    total_invoiced = (
        SupplierInvoice.objects.filter(
            is_deleted=False, invoice_date__date__range=[start_date, end_date]
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    total_paid = (
        SupplierPayment.objects.filter(
            is_deleted=False, payment_date__date__range=[start_date, end_date]
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    outstanding_balance = total_invoiced - total_paid

    # Invoice Statistics
    total_invoices = SupplierInvoice.objects.filter(
        is_deleted=False, invoice_date__date__range=[start_date, end_date]
    ).count()

    paid_invoices = SupplierInvoice.objects.filter(
        is_deleted=False,
        status="PAID",
        invoice_date__date__range=[start_date, end_date],
    ).count()

    unpaid_invoices = SupplierInvoice.objects.filter(
        is_deleted=False,
        status="UNPAID",
        invoice_date__date__range=[start_date, end_date],
    ).count()

    partially_paid_invoices = SupplierInvoice.objects.filter(
        is_deleted=False,
        status="PARTIALLY_PAID",
        invoice_date__date__range=[start_date, end_date],
    ).count()

    # Payment Statistics
    total_payments = SupplierPayment.objects.filter(
        is_deleted=False, payment_date__date__range=[start_date, end_date]
    ).count()

    # Top Suppliers by Outstanding Balance
    top_suppliers_outstanding = (
        Supplier.objects.filter(is_deleted=False)
        .annotate(
            total_invoiced=Sum(
                "invoices__total_amount", filter=Q(invoices__is_deleted=False)
            ),
            total_paid=Sum(
                "payments_made__amount", filter=Q(payments_made__is_deleted=False)
            ),
        )
        .annotate(
            outstanding=Sum(
                "invoices__total_amount", filter=Q(invoices__is_deleted=False)
            )
            - Sum("payments_made__amount", filter=Q(payments_made__is_deleted=False))
        )
        .filter(outstanding__gt=0)
        .order_by("-outstanding")[:5]
    )

    # Recent Activities
    recent_invoices = (
        SupplierInvoice.objects.filter(is_deleted=False)
        .select_related("supplier")
        .order_by("-created_at")[:5]
    )

    recent_payments = (
        SupplierPayment.objects.filter(is_deleted=False)
        .select_related("supplier")
        .order_by("-created_at")[:5]
    )

    # Monthly Trends (last 6 months)
    monthly_data = []
    for i in range(6):
        month_date = today - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(
            days=1
        )

        month_invoiced = (
            SupplierInvoice.objects.filter(
                is_deleted=False, invoice_date__date__range=[month_start, month_end]
            ).aggregate(total=Sum("total_amount"))["total"]
            or 0
        )

        month_paid = (
            SupplierPayment.objects.filter(
                is_deleted=False, payment_date__date__range=[month_start, month_end]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        monthly_data.append(
            {
                "month": month_start.strftime("%b %Y"),
                "invoiced": float(month_invoiced),
                "paid": float(month_paid),
                "outstanding": float(month_invoiced - month_paid),
            }
        )

    monthly_data.reverse()  # Show oldest to newest

    # Payment Method Distribution
    payment_methods = (
        SupplierPayment.objects.filter(
            is_deleted=False, payment_date__date__range=[start_date, end_date]
        )
        .values("method")
        .annotate(count=Count("id"), total_amount=Sum("amount"))
        .order_by("-total_amount")
    )

    # Invoice Type Distribution
    invoice_types = (
        SupplierInvoice.objects.filter(
            is_deleted=False, invoice_date__date__range=[start_date, end_date]
        )
        .values("invoice_type")
        .annotate(count=Count("id"), total_amount=Sum("total_amount"))
        .order_by("-total_amount")
    )

    # GST vs Non-GST Analysis
    gst_invoices = SupplierInvoice.objects.filter(
        is_deleted=False,
        invoice_type="GST_APPLICABLE",
        invoice_date__date__range=[start_date, end_date],
    ).aggregate(
        count=Count("id"),
        total_amount=Sum("total_amount"),
        total_gst=Sum("cgst_amount") + Sum("igst_amount"),
    )

    local_invoices = SupplierInvoice.objects.filter(
        is_deleted=False,
        invoice_type="LOCAL_PURCHASE",
        invoice_date__date__range=[start_date, end_date],
    ).aggregate(count=Count("id"), total_amount=Sum("total_amount"))

    # Quick Actions Data
    suppliers_needing_attention = (
        Supplier.objects.filter(is_deleted=False)
        .annotate(
            total_invoiced=Sum(
                "invoices__total_amount", filter=Q(invoices__is_deleted=False)
            ),
            total_paid=Sum(
                "payments_made__amount", filter=Q(payments_made__is_deleted=False)
            ),
        )
        .annotate(
            outstanding=Sum(
                "invoices__total_amount", filter=Q(invoices__is_deleted=False)
            )
            - Sum("payments_made__amount", filter=Q(payments_made__is_deleted=False))
        )
        .filter(outstanding__gt=0)
        .count()
    )

    overdue_invoices = SupplierInvoice.objects.filter(
        is_deleted=False,
        status__in=["UNPAID", "PARTIALLY_PAID"],
        invoice_date__date__lt=today - timedelta(days=30),
    ).count()

    context = {
        # Date filters
        "date_filter": date_filter,
        "start_date": start_date,
        "end_date": end_date,
        # Overall statistics
        "total_suppliers": total_suppliers,
        "active_suppliers": active_suppliers,
        "inactive_suppliers": inactive_suppliers,
        # Financial statistics
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "outstanding_balance": outstanding_balance,
        # Invoice statistics
        "total_invoices": total_invoices,
        "paid_invoices": paid_invoices,
        "unpaid_invoices": unpaid_invoices,
        "partially_paid_invoices": partially_paid_invoices,
        # Payment statistics
        "total_payments": total_payments,
        # Top suppliers
        "top_suppliers_outstanding": top_suppliers_outstanding,
        # Recent activities
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
        # Charts data
        "monthly_data": monthly_data,
        "payment_methods": list(payment_methods),
        "invoice_types": list(invoice_types),
        # GST analysis
        "gst_invoices": gst_invoices,
        "local_invoices": local_invoices,
        # Quick actions
        "suppliers_needing_attention": suppliers_needing_attention,
        "overdue_invoices": overdue_invoices,
    }

    return render(request, "supplier/dashboard.html", context)


@login_required
def home(request):
    """Supplier management main page with search and filter functionality."""

    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    sort_by = request.GET.get("sort", "-created_at")

    # Start with all suppliers
    suppliers = Supplier.objects.all()

    # Apply search filter
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query)
            | Q(contact_person__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(gstin__icontains=search_query)
            | Q(address__icontains=search_query)
        )

    # Apply status filter (active/inactive based on soft delete)
    if status_filter == "active":
        suppliers = suppliers.filter(is_deleted=False)
    elif status_filter == "inactive":
        suppliers = suppliers.filter(is_deleted=True)

    # Apply sorting
    if sort_by in [
        "name",
        "-name",
        "created_at",
        "-created_at",
        "phone",
        "-phone",
        "contact_person",
        "-contact_person",
    ]:
        suppliers = suppliers.order_by(sort_by)
    else:
        suppliers = suppliers.order_by("-created_at")

    context = {
        "data": suppliers,
        "search_query": search_query,
        "status_filter": status_filter,
        "sort_by": sort_by,
    }

    return render(request, "supplier/home.html", context)


@login_required
def supplier_detail(request, pk):
    """View supplier details with invoices and payments tables."""
    supplier = get_object_or_404(Supplier, id=pk)

    # Get actual invoices from database
    invoices = supplier.invoices.all().order_by("-invoice_date")

    # Calculate invoice summary data
    total_invoice_amount = sum(invoice.total_amount for invoice in invoices)
    unpaid_invoices_count = sum(1 for invoice in invoices if invoice.status != "PAID")

    # Get actual payments from database (replace sample data later)
    payments = supplier.payments_made.all().order_by("-payment_date")

    # Calculate payment summary data
    total_payment_amount = sum(payment.amount for payment in payments)
    outstanding_amount = total_invoice_amount - total_payment_amount

    context = {
        "supplier": supplier,
        "invoices": invoices,
        "payments": payments,
        "total_invoice_amount": total_invoice_amount,
        "unpaid_invoices_count": unpaid_invoices_count,
        "total_payment_amount": total_payment_amount,
        "outstanding_amount": outstanding_amount,
    }

    return render(request, "supplier/detail.html", context)


@login_required
def delete_invoice(request, supplier_pk, invoice_pk):
    """Delete an invoice."""
    supplier = get_object_or_404(Supplier, id=supplier_pk)
    invoice = get_object_or_404(SupplierInvoice, id=invoice_pk, supplier=supplier)

    if request.method == "POST":
        invoice_number = invoice.invoice_number
        invoice.delete()
        messages.success(request, f"Invoice {invoice_number} deleted successfully!")
        return redirect("supplier:detail", pk=supplier_pk)

    context = {"supplier": supplier, "invoice": invoice}

    return render(request, "supplier/invoice/delete.html", context)


@login_required
def search_suppliers_ajax(request):
    """AJAX endpoint for real-time supplier search."""
    search_query = request.GET.get("q", "")

    if len(search_query) < 2:
        return JsonResponse({"suppliers": []})

    suppliers = Supplier.objects.filter(
        Q(name__icontains=search_query)
        | Q(contact_person__icontains=search_query)
        | Q(phone__icontains=search_query)
        | Q(email__icontains=search_query)
        | Q(gstin__icontains=search_query)
    )[
        :10
    ]  # Limit to 10 results

    data = []
    for supplier in suppliers:
        data.append(
            {
                "id": supplier.id,
                "name": supplier.name,
                "contact_person": supplier.contact_person,
                "phone": supplier.phone,
                "email": supplier.email,
                "gstin": supplier.gstin,
                "is_active": not supplier.is_deleted,
            }
        )

    return JsonResponse({"suppliers": data})


class CreateSupplier(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "supplier/form.html"
    success_url = reverse_lazy("supplier:home")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Supplier created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Supplier"
        context["supplier"] = None  # For breadcrumb compatibility
        return context


class EditSupplier(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "supplier/form.html"
    success_url = reverse_lazy("supplier:home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Supplier"
        context["supplier"] = self.get_object()  # For breadcrumb compatibility
        return context

    def form_valid(self, form):
        messages.success(self.request, "Supplier updated successfully!")
        return super().form_valid(form)


class DeleteSupplier(LoginRequiredMixin, DeleteView):
    model = Supplier
    success_url = reverse_lazy("supplier:home")
    template_name = "supplier/delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["supplier"] = self.get_object()
        return context

    def delete(self, request, *args, **kwargs):
        supplier = self.get_object()
        messages.success(request, f"Supplier '{supplier.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Payment Views
class CreatePayment(LoginRequiredMixin, CreateView):
    model = SupplierPayment
    form_class = SupplierPaymentForm
    template_name = "supplier/payment/form.html"

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.supplier.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Payment"
        context["supplier"] = self.supplier
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["supplier"] = self.supplier
        return kwargs

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        form.instance.created_by = self.request.user
        form.instance.save()
        messages.success(
            self.request,
            f"Payment of ₹{form.instance.amount} recorded successfully!",
        )
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, id=kwargs["supplier_pk"])
        return super().dispatch(request, *args, **kwargs)


class EditPayment(LoginRequiredMixin, UpdateView):
    model = SupplierPayment
    form_class = SupplierPaymentForm
    template_name = "supplier/payment/form.html"
    pk_url_kwarg = "payment_pk"

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.supplier.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Payment"
        context["supplier"] = self.supplier
        context["payment"] = self.get_object()

        # Get allocation information for warnings
        payment = self.get_object()
        total_allocated = (
            payment.allocations.aggregate(total=Sum("amount_allocated"))["total"] or 0
        )
        context["total_allocated"] = total_allocated
        context["has_allocations"] = total_allocated > 0

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["supplier"] = self.supplier
        return kwargs

    def form_valid(self, form):
        # Get the old payment amount before saving
        old_amount = self.get_object().amount
        new_amount = form.cleaned_data["amount"]

        # Save the payment
        payment = form.save()

        # Recalculate unallocated amount if payment amount changed
        if old_amount != new_amount:
            total_allocated = (
                payment.allocations.aggregate(total=Sum("amount_allocated"))["total"]
                or 0
            )
            payment.unallocated_amount = new_amount - total_allocated
            payment.save(update_fields=["unallocated_amount"])

        messages.success(
            self.request,
            f"Payment updated successfully!",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, "Invalid form submission. Please check your inputs."
        )
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, id=kwargs["supplier_pk"])
        return super().dispatch(request, *args, **kwargs)


@login_required
def delete_payment(request, supplier_pk, payment_pk):
    """Delete a payment."""
    supplier = get_object_or_404(Supplier, id=supplier_pk)
    payment = get_object_or_404(SupplierPayment, id=payment_pk, supplier=supplier)

    if request.method == "POST":
        payment_amount = payment.amount
        payment.delete()
        messages.success(request, f"Payment of ₹{payment_amount} deleted successfully!")
        return redirect("supplier:detail", pk=supplier_pk)

    context = {"supplier": supplier, "payment": payment}

    return render(request, "supplier/payment/delete.html", context)


@login_required
def payment_detail(request, supplier_pk, payment_pk):
    """View payment details."""
    supplier = get_object_or_404(Supplier, id=supplier_pk)
    payment = get_object_or_404(SupplierPayment, id=payment_pk, supplier=supplier)

    # Get payment allocations if any
    allocations = payment.allocations.all().select_related("invoice")

    context = {
        "supplier": supplier,
        "payment": payment,
        "allocations": allocations,
    }

    return render(request, "supplier/payment/detail.html", context)


# Allocation Views
class CreateAllocation(LoginRequiredMixin, CreateView):
    model = SupplierPaymentAllocation
    form_class = SupplierPaymentAllocationForm
    template_name = "supplier/allocation/form.html"

    def get_success_url(self):
        return reverse_lazy(
            "supplier:payment_detail",
            kwargs={"supplier_pk": self.supplier.pk, "payment_pk": self.payment.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Allocate Payment"
        context["supplier"] = self.supplier
        context["payment"] = self.payment
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["payment"] = self.payment
        kwargs["supplier"] = self.supplier
        return kwargs

    def form_valid(self, form):
        form.instance.payment = self.payment
        form.instance.created_by = self.request.user

        # Save the allocation
        allocation = form.save()

        # Update payment unallocated amount
        self.payment.unallocated_amount -= allocation.amount_allocated
        self.payment.save()

        # Recalculate paid amount for the invoice based on all allocations
        invoice = allocation.invoice
        total_allocated = (
            invoice.allocations.aggregate(total=Sum("amount_allocated"))["total"] or 0
        )
        invoice.paid_amount = total_allocated

        # Update invoice status
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = "PAID"
        elif invoice.paid_amount > 0:
            invoice.status = "PARTIALLY_PAID"
        else:
            invoice.status = "UNPAID"

        invoice.save()

        messages.success(
            self.request,
            f"₹{allocation.amount_allocated:,.2f} allocated to Invoice {invoice.invoice_number} successfully!",
        )
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, id=kwargs["supplier_pk"])
        self.payment = get_object_or_404(
            SupplierPayment, id=kwargs["payment_pk"], supplier=self.supplier
        )
        return super().dispatch(request, *args, **kwargs)


class EditAllocation(LoginRequiredMixin, UpdateView):
    model = SupplierPaymentAllocation
    form_class = SupplierPaymentAllocationForm
    template_name = "supplier/allocation/form.html"
    pk_url_kwarg = "allocation_pk"

    def get_success_url(self):
        return reverse_lazy(
            "supplier:payment_detail",
            kwargs={"supplier_pk": self.supplier.pk, "payment_pk": self.payment.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Allocation"
        context["supplier"] = self.supplier
        context["payment"] = self.payment
        context["allocation"] = self.get_object()

        # Calculate available amount for editing (unallocated + current allocation)
        current_allocation = self.get_object()
        available_amount = (
            self.payment.unallocated_amount + current_allocation.amount_allocated
        )
        context["available_amount"] = available_amount

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Create a temporary payment object for form validation without modifying the actual payment
        temp_payment = type(self.payment)(
            id=self.payment.id,
            amount=self.payment.amount,
            unallocated_amount=self.payment.unallocated_amount
            + self.get_object().amount_allocated,
        )
        kwargs["payment"] = temp_payment
        kwargs["supplier"] = self.supplier
        kwargs["current_allocation"] = self.get_object()
        return kwargs

    def form_valid(self, form):
        old_allocation = self.get_object()
        old_amount = old_allocation.amount_allocated
        old_invoice = old_allocation.invoice

        # Revert old allocation
        self.payment.unallocated_amount += old_amount
        self.payment.save()

        # Save new allocation
        allocation = form.save()

        # Apply new allocation
        self.payment.unallocated_amount -= allocation.amount_allocated
        self.payment.save()

        # Recalculate paid amount for the invoice based on all allocations
        invoice = allocation.invoice
        total_allocated = (
            invoice.allocations.aggregate(total=Sum("amount_allocated"))["total"] or 0
        )
        invoice.paid_amount = total_allocated

        # Update invoice status
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = "PAID"
        elif invoice.paid_amount > 0:
            invoice.status = "PARTIALLY_PAID"
        else:
            invoice.status = "UNPAID"
        invoice.save()

        messages.success(
            self.request,
            f"Allocation updated successfully!",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        print(form.errors)
        messages.error(
            self.request, "Invalid form submission. Please check your inputs."
        )
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, id=kwargs["supplier_pk"])
        self.payment = get_object_or_404(
            SupplierPayment, id=kwargs["payment_pk"], supplier=self.supplier
        )
        return super().dispatch(request, *args, **kwargs)


@login_required
def delete_allocation(request, supplier_pk, payment_pk, allocation_pk):
    """Delete an allocation."""
    supplier = get_object_or_404(Supplier, id=supplier_pk)
    payment = get_object_or_404(SupplierPayment, id=payment_pk, supplier=supplier)
    allocation = get_object_or_404(
        SupplierPaymentAllocation, id=allocation_pk, payment=payment
    )

    if request.method == "POST":
        # Revert the allocation
        payment.unallocated_amount += allocation.amount_allocated
        payment.save()

        # Recalculate paid amount for the invoice based on remaining allocations
        invoice = allocation.invoice
        allocation_amount = allocation.amount_allocated
        allocation.delete()

        # Recalculate total allocated amount after deletion
        total_allocated = (
            invoice.allocations.aggregate(total=Sum("amount_allocated"))["total"] or 0
        )
        invoice.paid_amount = total_allocated

        # Update invoice status
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = "PAID"
        elif invoice.paid_amount > 0:
            invoice.status = "PARTIALLY_PAID"
        else:
            invoice.status = "UNPAID"
        invoice.save()

        messages.success(
            request, f"Allocation of ₹{allocation_amount:,.2f} deleted successfully!"
        )
        return redirect(
            "supplier:payment_detail", supplier_pk=supplier_pk, payment_pk=payment_pk
        )

    context = {
        "supplier": supplier,
        "payment": payment,
        "allocation": allocation,
    }

    return render(request, "supplier/allocation/delete.html", context)


class CreateInvoice(LoginRequiredMixin, CreateView):
    model = SupplierInvoice
    form_class = SupplierInvoiceForm
    template_name = "supplier/invoice/form.html"

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.supplier.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Invoice"
        context["supplier"] = self.supplier
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["supplier"] = self.supplier
        return kwargs

    def form_valid(self, form):
        form.instance.supplier = self.supplier
        form.instance.created_by = self.request.user
        form.instance.total_amount = form.cleaned_data["total_amount"]
        form.instance.save()
        messages.success(
            self.request,
            f"Invoice {form.instance.invoice_number} created successfully!",
        )
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, id=kwargs["supplier_pk"])
        return super().dispatch(request, *args, **kwargs)


class EditInvoice(LoginRequiredMixin, UpdateView):
    model = SupplierInvoice
    form_class = SupplierInvoiceForm
    template_name = "supplier/invoice/form.html"
    pk_url_kwarg = "invoice_pk"  # Use invoice_pk instead of pk

    def get_success_url(self):
        return reverse_lazy("supplier:detail", kwargs={"pk": self.supplier.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Invoice"
        context["supplier"] = self.supplier
        context["invoice"] = self.get_object()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["supplier"] = self.supplier
        return kwargs

    def form_valid(self, form):
        form.instance.total_amount = form.cleaned_data["total_amount"]
        form.instance.save()
        messages.success(
            self.request,
            f"Invoice {form.instance.invoice_number} updated successfully!",
        )
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        self.supplier = get_object_or_404(Supplier, id=kwargs["supplier_pk"])
        return super().dispatch(request, *args, **kwargs)


@login_required
def supplier_report(request, pk):
    """Generate a comprehensive report showing all purchases and payments for a supplier sorted by date."""
    supplier = get_object_or_404(Supplier, id=pk)

    # Get view type parameter (timeline or table)
    view_type = request.GET.get("view", "timeline")

    # Get all invoices and payments
    invoices = supplier.invoices.all().order_by("invoice_date")
    payments = supplier.payments_made.all().order_by("payment_date")

    # Create a combined timeline of all transactions
    transactions = []

    # Add invoices to transactions
    for invoice in invoices:
        transactions.append(
            {
                "date": invoice.invoice_date,
                "type": "invoice",
                "object": invoice,
                "amount": invoice.total_amount,
                "description": f"Invoice #{invoice.invoice_number}",
                "status": invoice.status,
                "method": None,
                "reference": invoice.invoice_number,
                "gst_type": invoice.gst_type,
                "sub_total": invoice.sub_total,
                "cgst_amount": invoice.cgst_amount,
                "igst_amount": invoice.igst_amount,
                "adjustment_amount": invoice.adjustment_amount,
                "paid_amount": invoice.paid_amount,
                "notes": invoice.notes,
            }
        )

    # Add payments to transactions
    for payment in payments:
        transactions.append(
            {
                "date": payment.payment_date,
                "type": "payment",
                "object": payment,
                "amount": payment.amount,
                "description": f"Payment #{payment.id}",
                "status": "PAID",
                "method": payment.method,
                "reference": payment.transaction_id,
                "gst_type": None,
                "sub_total": None,
                "cgst_amount": None,
                "igst_amount": None,
                "adjustment_amount": None,
                "paid_amount": None,
                "notes": None,
                "unallocated_amount": payment.unallocated_amount,
            }
        )

    # Sort all transactions by date (oldest first)
    transactions.sort(key=lambda x: x["date"])

    # Calculate running balance
    running_balance = 0
    for transaction in transactions:
        if transaction["type"] == "invoice":
            running_balance += transaction["amount"]
        else:  # payment
            running_balance -= transaction["amount"]
        transaction["running_balance"] = running_balance

    # Calculate summary statistics
    total_invoiced = sum(t["amount"] for t in transactions if t["type"] == "invoice")
    total_paid = sum(t["amount"] for t in transactions if t["type"] == "payment")
    outstanding_balance = total_invoiced - total_paid

    # Get date range for filtering
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date:
        try:
            from datetime import datetime

            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            transactions = [t for t in transactions if t["date"] >= start_date]
        except ValueError:
            start_date = None

    if end_date:
        try:
            from datetime import datetime

            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            transactions = [t for t in transactions if t["date"] <= end_date]
        except ValueError:
            end_date = None

    context = {
        "supplier": supplier,
        "transactions": transactions,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "outstanding_balance": outstanding_balance,
        "start_date": start_date,
        "end_date": end_date,
        "transaction_count": len(transactions),
        "view_type": view_type,
    }

    return render(request, "supplier/report.html", context)


@login_required
def auto_reallocate(request, pk):
    """
    Auto reallocate payments using FIFO method.
    This function deletes all existing allocations and reapplies them
    in chronological order (oldest invoices first).
    """
    supplier = get_object_or_404(Supplier, id=pk)

    # Get all invoices and payments for this supplier
    invoices = supplier.invoices.filter(is_deleted=False).order_by("invoice_date")
    payments = supplier.payments_made.filter(is_deleted=False).order_by("payment_date")

    # Delete all existing allocations for this supplier
    SupplierPaymentAllocation.objects.filter(
        payment__supplier=supplier, payment__is_deleted=False
    ).delete()

    # Reset all invoice paid amounts and status
    for invoice in invoices:
        invoice.paid_amount = 0
        invoice.status = "UNPAID"
        invoice.save()

    # Reset all payment unallocated amounts
    for payment in payments:
        payment.unallocated_amount = payment.amount
        payment.save()

    # Implement FIFO allocation
    for payment in payments:
        remaining_payment_amount = payment.unallocated_amount

        # Get unpaid invoices in chronological order (FIFO)
        unpaid_invoices = invoices.filter(
            status__in=["UNPAID", "PARTIALLY_PAID"]
        ).order_by("invoice_date")

        for invoice in unpaid_invoices:
            if remaining_payment_amount <= 0:
                break

            # Calculate how much is still owed on this invoice
            amount_owed = invoice.total_amount - invoice.paid_amount

            if amount_owed > 0:
                # Calculate allocation amount (either full remaining payment or full invoice amount)
                allocation_amount = min(remaining_payment_amount, amount_owed)

                # Create allocation
                allocation = SupplierPaymentAllocation.objects.create(
                    payment=payment,
                    invoice=invoice,
                    amount_allocated=allocation_amount,
                    created_by=request.user,
                )

                # Update invoice paid amount and status
                invoice.paid_amount += allocation_amount
                if invoice.paid_amount >= invoice.total_amount:
                    invoice.status = "PAID"
                elif invoice.paid_amount > 0:
                    invoice.status = "PARTIALLY_PAID"
                invoice.save()

                # Update payment unallocated amount
                remaining_payment_amount -= allocation_amount
                payment.unallocated_amount = remaining_payment_amount
                payment.save()

    messages.success(
        request,
        f"Successfully reallocated payments for {supplier.name} using FIFO method.",
    )
    return redirect("supplier:detail", pk=pk)
