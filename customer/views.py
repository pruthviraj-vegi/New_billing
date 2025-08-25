from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.contrib import messages
from .models import Customer
from invoice.models import Invoice
import json
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .forms import CustomerForm
from django.urls import reverse_lazy


@login_required
def home(request):
    """Member management main page with search and filter functionality."""

    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    sort_by = request.GET.get("sort", "-created_at")

    # Start with all customers
    customers = Customer.objects.all()

    # Apply search filter
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query)
            | Q(phone_number__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(address__icontains=search_query)
        )

    # Apply status filter (active/inactive based on soft delete)
    if status_filter == "active":
        customers = customers.filter(is_deleted=False)
    elif status_filter == "inactive":
        customers = customers.filter(is_deleted=True)

    # Apply sorting
    if sort_by in [
        "name",
        "-name",
        "created_at",
        "-created_at",
        "phone_number",
        "-phone_number",
    ]:
        customers = customers.order_by(sort_by)
    else:
        customers = customers.order_by("-created_at")

    context = {
        "data": customers,
        "search_query": search_query,
        "status_filter": status_filter,
        "sort_by": sort_by,
    }

    return render(request, "customer/home.html", context)


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
    return render(request, "customer/detail.html", {"customer": customer, "invoices": invoices})


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
def search_customers_ajax(request):
    """AJAX endpoint for real-time customer search."""
    search_query = request.GET.get("q", "")

    if len(search_query) < 2:
        return JsonResponse({"customers": []})

    customers = Customer.objects.filter(
        Q(name__icontains=search_query)
        | Q(phone_number__icontains=search_query)
        | Q(email__icontains=search_query)
    )[
        :10
    ]  # Limit to 10 results

    data = []
    for customer in customers:
        data.append(
            {
                "id": customer.id,
                "name": customer.name,
                "phone_number": customer.phone_number,
                "email": customer.email,
                "address": customer.short_address,
                "is_active": not customer.is_deleted,
            }
        )

    return JsonResponse({"customers": data})
