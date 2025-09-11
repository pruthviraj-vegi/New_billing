from .forms import ClothTypeForm, ColorForm, CategoryForm, SizeForm
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import ClothType, Category, Color, Size
from django.urls import reverse
from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.db.models import Q
from fuzzywuzzy import process
from .mixins import SizePopupMixin, ColorPopupMixin, CategoryPopupMixin, ClothTypePopupMixin


def cloth_home(request):
    """List all cloth types"""
    cloth_types = ClothType.objects.all().order_by("name")

    context = {
        "cloth_types": cloth_types,
    }

    return render(request, "inventory/cloth/home.html", context)


class CreateClothType(ClothTypePopupMixin, CreateView):
    model = ClothType
    form_class = ClothTypeForm
    template_name = "inventory/cloth/form.html"

    def get_success_url_name(self):
        return "inventory:cloth_create"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Cloth Type"
        return context


class UpdateClothType(UpdateView):
    model = ClothType
    form_class = ClothTypeForm
    template_name = "inventory/cloth/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Cloth type updated successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:cloth_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Update Cloth Type"
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)


class DeleteClothType(DeleteView):
    model = ClothType
    template_name = "inventory/cloth/delete.html"

    def get_success_url(self):
        return reverse("inventory:cloth_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Delete Cloth Type"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Cloth type deleted successfully")
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)


def color_home(request):
    """List all colors"""
    colors = Color.objects.all().order_by("name")

    context = {
        "colors": colors,
    }

    return render(request, "inventory/color/home.html", context)


class CreateColor(ColorPopupMixin, CreateView):
    model = Color
    form_class = ColorForm
    template_name = "inventory/color/form.html"

    def get_success_url_name(self):
        return "inventory:color_create"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Color"
        return context


class UpdateColor(UpdateView):
    model = Color
    form_class = ColorForm
    template_name = "inventory/color/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Color updated successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:color_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Update Color"
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)


class DeleteColor(DeleteView):
    model = Color
    template_name = "inventory/color/delete.html"

    def get_success_url(self):
        return reverse("inventory:color_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Delete Color"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Color deleted successfully")
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)


def size_home(request):
    """List all sizes"""
    sizes = Size.objects.all().order_by("name")

    context = {
        "sizes": sizes,
    }

    return render(request, "inventory/size/home.html", context)


class CreateSize(SizePopupMixin, CreateView):
    model = Size
    form_class = SizeForm
    template_name = "inventory/size/form.html"

    def get_success_url_name(self):
        return "inventory:size_create"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Size"
        return context


class UpdateSize(UpdateView):
    model = Size
    form_class = SizeForm
    template_name = "inventory/size/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Size updated successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:size_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Update Size"
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)


class DeleteSize(DeleteView):
    model = Size
    template_name = "inventory/size/delete.html"

    def get_success_url(self):
        return reverse("inventory:size_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Delete Size"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Size deleted successfully")
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)


def category_home(request):
    """Category management main page - initial load only."""
    # No need to load categories here as they'll be loaded via AJAX
    
    return render(request, "inventory/category/home.html")


class CreateCategory(CategoryPopupMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category/form.html"

    def get_success_url_name(self):
        return "inventory:category_create"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Category"
        return context


class UpdateCategory(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Category updated successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:category_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Update Category"
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)


class DeleteCategory(DeleteView):
    model = Category
    template_name = "inventory/category/delete.html"

    def get_success_url(self):
        return reverse("inventory:category_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Delete Category"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Category deleted successfully")
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)


# Constants for category management
VALID_CATEGORY_SORT_FIELDS = {
    "id", "-id", "name", "-name", "created_at", "-created_at", "updated_at", "-updated_at"
}
OBJECTS_PER_PAGE = 10


@login_required
def search_suggestions(request):
    """AJAX endpoint for category search suggestions."""
    query = request.GET.get("q", "").strip()
    
    if not query or len(query) < 2:
        return JsonResponse({"suggestions": []})

    from django.core.cache import cache

    searchable_items = cache.get("category_search_words")

    if searchable_items is None:
        # Get all unique words from category names and descriptions
        categories = Category.objects.values_list("name", "description")
        
        # Extract all words from category data
        all_words = set()
        for name, description in categories:
            # Extract words from name
            if name:
                words = name.lower().split()
                all_words.update(words)
            
            # Extract words from description
            if description:
                words = description.lower().split()
                all_words.update(words)
        
        # Convert to list for fuzzy matching
        searchable_items = list(all_words)
        cache.set("category_search_words", searchable_items, 3600)

    # Perform fuzzy matching on individual words
    fuzzy_matches = process.extract(query.lower(), searchable_items, limit=10)
    
    # Filter matches with score > 60 and return only words
    suggestions = []
    seen_words = set()
    for word, score in fuzzy_matches:
        if score > 60 and word not in seen_words:
            suggestions.append(word)
            seen_words.add(word)
            if len(suggestions) >= 5:
                break

    return JsonResponse({"suggestions": suggestions})


@login_required
def fetch_categories(request):
    """AJAX endpoint to fetch categories with search, filter, and pagination."""
    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    sort_by = request.GET.get("sort", "-created_at")

    # Apply search filter
    filters = Q()
    if search_query:
        filters &= (
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    categories = Category.objects.filter(filters)

    # Apply sorting
    if sort_by not in VALID_CATEGORY_SORT_FIELDS:
        sort_by = "-created_at"
    categories = categories.order_by(sort_by)

    # Pagination
    paginator = Paginator(categories, OBJECTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Render the HTML template
    context = {
        "page_obj": page_obj,
        "total_count": paginator.count,
        "search_query": search_query,
    }

    # Render the table content (without pagination)
    table_html = render_to_string("inventory/category/fetch.html", context, request=request)

    # Render pagination separately
    pagination_html = ""
    if page_obj and page_obj.paginator.num_pages > 1:
        pagination_html = render_to_string(
            "common/_pagination.html", context, request=request
        )

    return JsonResponse(
        {"html": table_html, "pagination": pagination_html, "success": True}
    )
