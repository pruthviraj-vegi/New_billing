from django.shortcuts import render, get_object_or_404
from django.views import View
from cart.models import Cart
from .form import InvoiceForm
from .models import Invoice, InvoiceItem
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from inventory.services import InventoryService

# Create your views here.


def invoiceHome(request):
    template_name = "invoice/home.html"

    # Get query parameters
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    invoice_type_filter = request.GET.get("invoice_type", "")
    sort_by = request.GET.get("sort", "-created_at")

    # Base queryset
    invoices = Invoice.objects.select_related("customer", "created_by").all()

    # Apply search filter
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query)
            | Q(customer__name__icontains=search_query)
            | Q(customer__phone_number__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    # Apply status filter
    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)

    # Apply invoice type filter
    if invoice_type_filter:
        invoices = invoices.filter(invoice_type=invoice_type_filter)

    # Apply sorting
    invoices = invoices.order_by(sort_by)

    # Pagination
    paginator = Paginator(invoices, 25)  # 25 invoices per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "invoice_type_filter": invoice_type_filter,
        "sort_by": sort_by,
        "payment_status_choices": Invoice.PaymentStatus.choices,
        "invoice_type_choices": Invoice.InvoiceType.choices,
    }

    return render(request, template_name, context)


class CreateInvoice(View):
    template_name = "invoice/form.html"
    form_class = InvoiceForm

    def get(self, request, pk):
        cart = get_object_or_404(Cart, id=pk)
        form = self.form_class(
            initial={
                "invoice_type": Invoice.InvoiceType.CASH,
                "amount": cart.total_amount,
                "due_date": timezone.now() + timedelta(days=30),
            }
        )
        context = {"cart": cart, "form": form, "title": "Create Invoice"}
        return render(request, self.template_name, context)

    def post(self, request, pk):
        cart = get_object_or_404(Cart, id=pk)
        form = self.form_class(request.POST)
        if form.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.cart_no = cart.id
                invoice.amount = cart.total_amount
                invoice.modified_by = request.user

                invoice.save()

                for item in cart.cart_items.all():
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product_variant=item.product_variant,
                        quantity=item.quantity,
                        unit_price=item.price,
                        purchase_price=item.product_variant.purchase_price,
                        mrp=item.product_variant.mrp,
                    )
                    InventoryService.sale(
                        item.product_variant,
                        item.quantity,
                        request.user,
                        f"Invoice {invoice.invoice_number} - {item.product_variant.product.name}",
                        invoice,
                    )

                cart.delete()
                messages.success(request, "Invoice created successfully")
                return redirect("invoice:detail", pk=invoice.id)

        else:
            context = {"cart": cart, "form": form, "title": "Create Invoice"}
            return render(request, self.template_name, context)


class InvoiceDetail(View):
    template_name = "invoice/detail.html"

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, id=pk)
        context = {"invoice": invoice, "title": f"Invoice {invoice.invoice_number}"}
        return render(request, self.template_name, context)


class InvoiceEdit(View):
    template_name = "invoice/form.html"
    form_class = InvoiceForm

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, id=pk)
        form = self.form_class(instance=invoice)
        context = {
            "invoice": invoice,
            "form": form,
            "title": f"Edit Invoice {invoice.invoice_number}",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, id=pk)
        form = self.form_class(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, "Invoice updated successfully")
            return redirect("invoice:detail", pk=invoice.id)
        context = {
            "invoice": invoice,
            "form": form,
            "title": f"Edit Invoice {invoice.invoice_number}",
        }
        return render(request, self.template_name, context)


class InvoiceDelete(View):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, id=pk)
        invoice.delete()
        messages.success(request, "Invoice deleted successfully")
        return redirect("invoice:home")


class InvoiceDownload(View):
    def get(self, request):
        # Placeholder for download functionality
        messages.info(request, "Download functionality coming soon")
        return redirect("invoice:home")
