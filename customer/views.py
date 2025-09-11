from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum
from django.contrib import messages
from .models import Customer
from invoice.models import Invoice
from django.db.models import Sum, Count, Case, When, DecimalField
import json
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .forms import CustomerForm
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.template.loader import render_to_string

VALID_SORT_FIELDS = {
    "id",
    "-id",
    "name",
    "-name",
    "email",
    "-email",
    "created_at",
    "-created_at",
    "phone_number",
    "-phone_number",
    "address",
    "-address",
}

CUSTOMERS_PER_PAGE = 20


@login_required
def home(request):
    """Customer management main page - initial load only."""
    # For initial page load, just render the template with empty data
    return render(request, "customer/home.html")


@login_required
def fetch_customers(request):
    """AJAX endpoint to fetch customers with search, filter, and pagination."""
    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    sort_by = request.GET.get("sort", "-created_at")

    # Apply search filter
    filters = Q()
    if search_query:
        filters &= (
            Q(name__icontains=search_query)
            | Q(phone_number__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(address__icontains=search_query)
        )

    # Apply status filter (active/inactive based on soft delete)
    if status_filter == "active":
        filters &= Q(is_deleted=False)
    elif status_filter == "inactive":
        filters &= Q(is_deleted=True)

    customers = Customer.objects.filter(filters)

    # Apply sorting
    if sort_by not in VALID_SORT_FIELDS:
        sort_by = "-created_at"
    customers = customers.order_by(sort_by)

    # Pagination
    paginator = Paginator(customers, CUSTOMERS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Render the HTML template
    context = {
        "page_obj": page_obj,
        "total_count": paginator.count,
        "search_query": search_query,
    }

    # Render the table content (without pagination)
    table_html = render_to_string("customer/fetch.html", context, request=request)

    # Render pagination separately
    pagination_html = ""
    if page_obj and page_obj.paginator.num_pages > 1:
        pagination_html = render_to_string(
            "common/_pagination.html", context, request=request
        )

    return JsonResponse(
        {"html": table_html, "pagination": pagination_html, "success": True}
    )


class CreateCustomer(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customer/form.html"
    success_url = reverse_lazy("customer:home")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Customer created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Customer"
        context["customer"] = None  # For breadcrumb compatibility
        return context


class EditCustomer(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customer/form.html"
    success_url = reverse_lazy("customer:home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Customer"
        context["customer"] = self.get_object()  # For breadcrumb compatibility

        return context

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Customer updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class DeleteCustomer(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = "customer/delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["customer"] = self.get_object()
        return context

    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        messages.success(request, f"Customer '{customer.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("customer:home")

    def form_valid(self, form):
        messages.success(self.request, "Customer deleted successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


@login_required
def customer_detail(request, pk):
    """View customer details."""
    customer = get_object_or_404(Customer, id=pk)
    invoices = Invoice.objects.filter(customer=customer)

    # Get customer payments (FIFO system)
    context = {
        "customer": customer,
        "invoices": invoices,
    }
    context.update(get_calculations(pk))
    return render(request, "customer/detail.html", context)


def get_calculations(pk):
    customer = get_object_or_404(Customer, id=pk)
    invoices = Invoice.objects.filter(customer=customer)

    aggregates = invoices.aggregate(
        total_invoices=Count("id"),
        invoices_amount=Sum("amount"),
        cash_amount=Sum(
            Case(
                When(payment_type="CASH", then="amount"),
                default=0,
                output_field=DecimalField(),
            )
        ),
        credit_amount=Sum(
            Case(
                When(payment_type="CREDIT", then="amount"),
                default=0,
                output_field=DecimalField(),
            )
        ),
    )

    return {
        "total_invoices": aggregates["total_invoices"] or 0,
        "invoices_amount": aggregates["invoices_amount"] or 0,
        "cash_amount": aggregates["cash_amount"] or 0,
        "credit_amount": aggregates["credit_amount"] or 0,
    }


@login_required
def customer_delete(request, customer_id):
    """Delete customer (soft delete)."""
    if request.method == "POST":
        customer = get_object_or_404(Customer, id=customer_id)
        customer.delete()  # This will use soft delete
        messages.success(request, "Customer deleted successfully!")
        return redirect("customer:home")

    return redirect("customer:home")


@login_required
def download_customers(request):
    """Download customers data as JSON."""
    customers = Customer.objects.all()
    data = []

    for customer in customers:
        data.append(
            {
                "id": customer.id,
                "name": customer.name,
                "phone_number": customer.phone_number,
                "email": customer.email,
                "address": customer.address,
                "store_credit_balance": str(customer.store_credit_balance),
                "created_at": customer.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "is_active": not customer.is_deleted,
            }
        )

    response = HttpResponse(json.dumps(data, indent=2), content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="customers.json"'
    return response


@login_required
def customer_search_api(request):
    """API endpoint for searching customers (for autocomplete)."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'customers': []})
    
    # Search customers by name or phone number
    customers = Customer.objects.filter(
        Q(name__icontains=query) | Q(phone_number__icontains=query),
        is_deleted=False
    ).exclude(
        # Exclude current customer if editing
        id=request.GET.get('exclude', -1)
    ).order_by('name')[:10]  # Limit to 10 results
    
    # Format response
    customers_data = []
    for customer in customers:
        customers_data.append({
            'id': customer.id,
            'name': customer.name or '',
            'phone_number': customer.phone_number or '',
            'email': customer.email or '',
        })
    
    return JsonResponse({'customers': customers_data})
