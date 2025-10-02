from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.views import View
from cart.models import Cart
from .form import InvoiceForm
from .models import Invoice, InvoiceItem
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator
from inventory.services import InventoryService
from datetime import timedelta, datetime, date
from invoice.views_ import resequence_invoices
from django.template.loader import render_to_string
import json
from django.core.exceptions import ValidationError
import logging
from customer.forms import CustomerForm
from decimal import Decimal

logger = logging.getLogger(__name__)

# Create your views here.

VALID_SORT_FIELDS = {
    "id",
    "-id",
    "invoice_number",
    "-invoice_number",
    "customer__name",
    "-customer__name",
    "amount",
    "-amount",
    "payment_status",
    "-payment_status",
    "payment_type",
    "-payment_type",
    "invoice_date",
    "-invoice_date",
    "due_date",
    "-due_date",
    "created_at",
    "-created_at",
}

INVOICES_PER_PAGE = 20


@login_required
def invoiceHome(request):
    """Invoice management main page - initial load only."""
    # For initial page load, just render the template with empty data

    financial_years = (
        Invoice.objects.filter(financial_year__isnull=False)
        .values_list("financial_year", flat=True)
        .distinct()
    )
    context = {
        "payment_status_choices": Invoice.PaymentStatus.choices,
        "payment_type_choices": Invoice.PaymentType.choices,
        "bill_types": Invoice.Invoice_type.choices,
        "financial_years": financial_years,
    }
    return render(request, "invoice/home.html", context)


@login_required
def fetch_invoices(request):
    """AJAX endpoint to fetch invoices with search, filter, and pagination."""
    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    payment_type_filter = request.GET.get("payment_type", "")
    sort_by = request.GET.get("sort", "-id")
    bill_types_filter = request.GET.get("bill_types", "")

    # Apply search filter
    filters = Q()
    if search_query:
        filters &= (
            Q(invoice_number__icontains=search_query)
            | Q(customer__name__icontains=search_query)
            | Q(customer__phone_number__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    # Apply status filter
    if status_filter:
        filters &= Q(payment_status=status_filter)

    # Apply payment type filter
    if payment_type_filter:
        filters &= Q(payment_type=payment_type_filter)

    # Apply bill types filter
    if bill_types_filter:
        filters &= Q(invoice_type=bill_types_filter)

    invoices = Invoice.objects.select_related("customer", "created_by").filter(filters)

    # Apply sorting
    if sort_by == "gst_bills":
        invoices = invoices.filter(invoice_type=Invoice.Invoice_type.GST).order_by(
            "-invoice_date"
        )
    elif sort_by == "cash_bills":
        invoices = invoices.filter(invoice_type=Invoice.Invoice_type.CASH).order_by(
            "-invoice_date"
        )
    elif sort_by not in VALID_SORT_FIELDS:
        sort_by = "-invoice_date"
        invoices = invoices.order_by(sort_by)
    else:
        invoices = invoices.order_by(sort_by)

    # Pagination
    paginator = Paginator(invoices, INVOICES_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Render the HTML template
    context = {
        "page_obj": page_obj,
        "total_count": paginator.count,
        "search_query": search_query,
    }

    # Render the table content (without pagination)
    table_html = render_to_string("invoice/fetch.html", context, request=request)

    # Render pagination separately
    pagination_html = ""
    if page_obj and page_obj.paginator.num_pages > 1:
        pagination_html = render_to_string(
            "common/_pagination.html", context, request=request
        )

    return JsonResponse(
        {"html": table_html, "pagination": pagination_html, "success": True}
    )


class CreateInvoice(View):
    template_name = "invoice/form.html"
    form_class = InvoiceForm

    def get(self, request, pk):
        cart = get_object_or_404(Cart, id=pk)
        if int(cart.total_amount) <= 0:
            messages.error(request, "Cart is empty")
            return redirect("cart:getCartData", pk=cart.id)
        form = self.form_class(
            initial={
                "payment_type": Invoice.PaymentType.CASH,
                "amount": cart.total_amount,
                "due_date": timezone.now() + timedelta(days=30),
            }
        )
        context = {
            "cart": cart,
            "form": form,
            "title": "Create Invoice",
            "customer_form": CustomerForm(),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        cart = get_object_or_404(Cart, id=pk)
        if int(cart.total_amount) <= 0:
            messages.error(request, "Cart is empty")
            return redirect("cart:getCartData", pk=cart.id)
        form = self.form_class(request.POST)
        if form.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.cart_no = cart.id
                invoice.amount = cart.total_amount
                invoice.modified_by = request.user
                invoice.created_by = request.user

                invoice.save()

                for item in cart.cart_items.all():
                    invoice_item = InvoiceItem.objects.create(
                        invoice=invoice,
                        product_variant=item.product_variant,
                        quantity=item.quantity,
                        unit_price=item.price,
                        purchase_price=item.product_variant.actual_purchased_price,
                        mrp=item.product_variant.mrp,
                    )
                    InventoryService.sale(
                        variant=item.product_variant,
                        quantity_sold=item.quantity,
                        user=request.user,
                        notes=f"Invoice {invoice.invoice_number} - {item.product_variant.product.name}",
                        invoice_item=invoice_item,
                    )

                cart.delete()
                messages.success(request, "Invoice created successfully")
                return render(
                    request, "intermediate_page.html", {"invoice_no": invoice.id}
                )

        else:
            context = {"cart": cart, "form": form, "title": "Create Invoice"}
            logger.error(f"Form invalid: {form.errors}")
            return render(request, self.template_name, context)


class InvoiceDetail(View):
    template_name = "invoice/detail.html"

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, id=pk)

        # Get return invoices for this invoice
        return_invoices = (
            invoice.return_invoices.select_related(
                "created_by", "approved_by", "processed_by"
            )
            .prefetch_related("return_invoice_items")
            .order_by("-created_at")
        )

        # Calculate return summary
        total_return_amount = sum(ret.refund_amount for ret in return_invoices)
        total_return_items = sum(
            len(
                [
                    item
                    for item in ret.return_invoice_items.all()
                    if item.quantity_returned > 0
                ]
            )
            for ret in return_invoices
        )

        # Add return item counts to each return invoice for template use
        for ret in return_invoices:
            ret.returned_items_count = len(
                [
                    item
                    for item in ret.return_invoice_items.all()
                    if item.quantity_returned > 0
                ]
            )

        # Get return items with details
        return_items_with_details = []
        for return_invoice in return_invoices:
            items = return_invoice.return_invoice_items.filter(
                quantity_returned__gt=0
            ).select_related("product_variant__product", "original_invoice_item")
            return_items_with_details.extend(items)

        # Calculate adjusted invoice total (original amount minus returns)
        adjusted_invoice_total = invoice.total_payable - total_return_amount

        context = {
            "invoice": invoice,
            "title": f"Invoice {invoice.invoice_number}",
            "return_invoices": return_invoices,
            "total_return_amount": total_return_amount,
            "total_return_items": total_return_items,
            "return_items_with_details": return_items_with_details,
            "adjusted_invoice_total": adjusted_invoice_total,
        }
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
            if (
                invoice.payment_type == Invoice.PaymentType.CASH
                and form.cleaned_data.get("payment_type") == Invoice.PaymentType.CREDIT
            ):
                invoice.paid_amount = 0

                raise ValidationError(
                    "Payment type cannot be changed from cash to credit"
                )
            form.save()
            messages.success(request, "Invoice updated successfully")
            return redirect("invoice:detail", pk=invoice.id)

        logger.error(f"Form invalid: {form.errors}")

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


@login_required
def download_invoices(request):
    """Download invoices data as JSON."""
    invoices = Invoice.objects.select_related("customer").all()
    data = []

    for invoice in invoices:
        data.append(
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "customer_phone": invoice.customer.phone_number,
                "amount": str(invoice.amount),
                "payment_status": invoice.payment_status,
                "payment_type": invoice.payment_type,
                "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d %H:%M:%S"),
                "due_date": (
                    invoice.due_date.strftime("%Y-%m-%d %H:%M:%S")
                    if invoice.due_date
                    else None
                ),
                "remaining_amount": str(invoice.remaining_amount),
            }
        )

    response = HttpResponse(json.dumps(data, indent=2), content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="invoices.json"'
    return response


@login_required
def search_invoices_ajax(request):
    """AJAX endpoint for real-time invoice search."""
    search_query = request.GET.get("q", "")

    if len(search_query) < 2:
        return JsonResponse({"invoices": []})

    invoices = Invoice.objects.select_related("customer").filter(
        Q(invoice_number__icontains=search_query)
        | Q(customer__name__icontains=search_query)
        | Q(customer__phone_number__icontains=search_query)
    )[
        :10
    ]  # Limit to 10 results

    data = []
    for invoice in invoices:
        data.append(
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "customer_phone": invoice.customer.phone_number,
                "amount": str(invoice.amount),
                "payment_status": invoice.payment_status,
                "payment_type": invoice.payment_type,
            }
        )

    return JsonResponse({"invoices": data})


class InvoiceDownload(View):

    def get(self, request):
        resequence_invoices("24-25", request.user)
        return JsonResponse({"message": "Invoices resequenced successfully"})


@login_required
def invoice_dashboard(request):
    """Invoice dashboard with date filtering and metrics"""

    return render(request, "invoice/dashboard.html")


@login_required
def fetch_dashboard_data(request):
    """AJAX endpoint to fetch dashboard data."""
    # Get date filter from request
    date_filter = request.GET.get("date_filter", "today")

    # Calculate date ranges
    now = timezone.now()
    today = now.date()

    if date_filter == "today":
        start_date = today
        end_date = today
    elif date_filter == "yesterday":
        yesterday = today - timedelta(days=1)
        start_date = yesterday
        end_date = yesterday
    elif date_filter == "this_month":
        start_date = today.replace(day=1)
        end_date = today
    elif date_filter == "last_month":
        first_this_month = today.replace(day=1)
        last_month = first_this_month - timedelta(days=1)
        start_date = last_month.replace(day=1)
        end_date = last_month
    elif date_filter == "this_year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        # Default to today
        start_date = today
        end_date = today

    # Filter invoices by date range
    invoices = Invoice.objects.filter(
        invoice_date__date__range=[start_date, end_date]
    ).select_related("customer")

    # Calculate metrics
    total_invoices = invoices.count()
    total_amount = invoices.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_discount = invoices.aggregate(total=Sum("discount_amount"))[
        "total"
    ] or Decimal("0")
    total_paid = invoices.aggregate(total=Sum("paid_amount"))["total"] or Decimal("0")

    # Calculate profit from invoice items
    invoice_items = InvoiceItem.objects.filter(
        invoice__invoice_date__date__range=[start_date, end_date]
    )

    total_profit = Decimal("0")
    for item in invoice_items:
        profit_per_unit = item.unit_price - item.purchase_price
        total_profit += profit_per_unit * item.quantity

    # Calculate net amount (amount - discount)
    net_amount = total_amount - total_discount

    # Calculate outstanding amount (net amount - paid amount)
    outstanding_amount = net_amount - total_paid

    # Payment status breakdown
    payment_status_breakdown = (
        invoices.values("payment_status")
        .annotate(count=Count("id"), amount=Sum("amount"))
        .order_by("payment_status")
    )

    # Payment type breakdown
    payment_type_breakdown = (
        invoices.values("payment_type")
        .annotate(count=Count("id"), amount=Sum("amount"))
        .order_by("payment_type")
    )

    # Recent invoices (last 10)
    recent_invoices = invoices.order_by("-invoice_date")[:10]

    context = {
        "date_filter": date_filter,
        "start_date": start_date,
        "end_date": end_date,
        "total_invoices": total_invoices,
        "total_amount": total_amount,
        "total_discount": total_discount,
        "total_paid": total_paid,
        "net_amount": net_amount,
        "outstanding_amount": outstanding_amount,
        "total_profit": total_profit,
        "payment_status_breakdown": payment_status_breakdown,
        "payment_type_breakdown": payment_type_breakdown,
        "recent_invoices": recent_invoices,
        "date_filter_options": [
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("this_month", "This Month"),
            ("last_month", "Last Month"),
            ("this_year", "This Year"),
        ],
    }

    return render(request, "invoice/dashboard.html", context)


@login_required
def invoice_dashboard_fetch(request):
    """AJAX endpoint to fetch dashboard data"""

    # Get date filter from request
    date_filter = request.GET.get("date_filter", "today")

    # Calculate date ranges
    now = timezone.now()
    today = now.date()

    if date_filter == "today":
        start_date = today
        end_date = today
    elif date_filter == "yesterday":
        yesterday = today - timedelta(days=1)
        start_date = yesterday
        end_date = yesterday
    elif date_filter == "this_month":
        start_date = today.replace(day=1)
        end_date = today
    elif date_filter == "last_month":
        first_this_month = today.replace(day=1)
        last_month = first_this_month - timedelta(days=1)
        start_date = last_month.replace(day=1)
        end_date = last_month
    elif date_filter == "this_year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        # Default to today
        start_date = today
        end_date = today

    # Filter invoices by date range
    invoices = Invoice.objects.filter(
        invoice_date__date__range=[start_date, end_date]
    ).select_related("customer")

    # Calculate metrics
    total_invoices = invoices.count()
    total_amount = invoices.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_discount = invoices.aggregate(total=Sum("discount_amount"))[
        "total"
    ] or Decimal("0")
    total_paid = invoices.aggregate(total=Sum("paid_amount"))["total"] or Decimal("0")

    # Calculate profit from invoice items
    invoice_items = InvoiceItem.objects.filter(
        invoice__invoice_date__date__range=[start_date, end_date]
    )

    total_profit = Decimal("0")
    for item in invoice_items:
        profit_per_unit = item.unit_price - item.purchase_price
        total_profit += profit_per_unit * item.quantity

    # Calculate net amount (amount - discount)
    net_amount = total_amount - total_discount

    # Calculate outstanding amount (net amount - paid amount)
    outstanding_amount = net_amount - total_paid

    # Payment status breakdown
    payment_status_breakdown = (
        invoices.values("payment_status")
        .annotate(count=Count("id"), amount=Sum("amount"))
        .order_by("payment_status")
    )

    # Payment type breakdown
    payment_type_breakdown = (
        invoices.values("payment_type")
        .annotate(count=Count("id"), amount=Sum("amount"))
        .order_by("payment_type")
    )

    # Recent invoices (last 10)
    recent_invoices = invoices.order_by("-invoice_date")[:10]

    # Prepare response data
    stats = {
        "total_invoices": total_invoices,
        "total_amount": float(total_amount),
        "total_discount": float(total_discount),
        "total_paid": float(total_paid),
        "net_amount": float(net_amount),
        "outstanding_amount": float(outstanding_amount),
        "total_profit": float(total_profit),
    }

    # Add percentage calculations for breakdowns
    payment_status_data = []
    for status in payment_status_breakdown:
        percentage = (
            (status["count"] / total_invoices * 100) if total_invoices > 0 else 0
        )
        payment_status_data.append(
            {
                "payment_status": status["payment_status"].title(),
                "count": status["count"],
                "amount": float(status["amount"]),
                "percentage": round(percentage, 1),
            }
        )

    payment_type_data = []
    for type_data in payment_type_breakdown:
        percentage = (
            (type_data["count"] / total_invoices * 100) if total_invoices > 0 else 0
        )
        payment_type_data.append(
            {
                "payment_type": type_data["payment_type"].title(),
                "count": type_data["count"],
                "amount": float(type_data["amount"]),
                "percentage": round(percentage, 1),
            }
        )

    # Recent invoices data
    recent_invoices_data = []
    for invoice in recent_invoices:
        recent_invoices_data.append(
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "amount": float(invoice.amount),
                "invoice_date": invoice.invoice_date.isoformat(),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "stats": stats,
            "payment_status_breakdown": payment_status_data,
            "payment_type_breakdown": payment_type_data,
            "recent_invoices": recent_invoices_data,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "filter": date_filter,
            },
        }
    )
