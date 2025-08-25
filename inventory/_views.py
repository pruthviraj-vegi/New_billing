from .forms import ClothTypeForm, ColorForm, CategoryForm, SizeForm
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import ClothType, Category, Color, Size
from django.urls import reverse
from django.shortcuts import render
from django.contrib import messages


def cloth_home(request):
    """List all cloth types"""
    cloth_types = ClothType.objects.all().order_by("name")

    context = {
        "cloth_types": cloth_types,
    }

    return render(request, "inventory/cloth/home.html", context)


class CreateClothType(CreateView):
    model = ClothType
    form_class = ClothTypeForm
    template_name = "inventory/cloth/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Cloth type created successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:cloth_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Cloth Type"
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)


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


class CreateColor(CreateView):
    model = Color
    form_class = ColorForm
    template_name = "inventory/color/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Color created successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:color_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Color"
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)


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


class CreateSize(CreateView):
    model = Size
    form_class = SizeForm
    template_name = "inventory/size/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Size created successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:size_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Size"
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)


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
    """List all categories"""
    categories = Category.objects.all().order_by("name")

    context = {
        "categories": categories,
    }

    return render(request, "inventory/category/home.html", context)


class CreateCategory(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Category created successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventory:category_home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Category"
        return context

    def form_invalid(self, form):
        return super().form_invalid(form)


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
