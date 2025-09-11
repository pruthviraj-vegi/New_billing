"""
Reusable mixins for popup functionality
"""
from django.http import JsonResponse
from django.urls import reverse


class PopupMixin:
    """
    Mixin to make any CreateView popup-compatible
    """
    popup_template = "inventory/popup_form.html"
    popup_title = "Add New Item"
    submit_text = "Create"
    param_name = "new_item"
    
    def get_template_names(self):
        # Use popup template if this is a popup request
        if self.request.GET.get('popup'):
            return [self.popup_template]
        return super().get_template_names()
    
    def form_valid(self, form):
        # Add success message
        from django.contrib import messages
        messages.success(self.request, f"{self.popup_title.replace('Add New ', '')} created successfully")

        return super().form_valid(form)
    
    def get_success_url(self):
        # Check if this is a popup request
        if self.request.GET.get('popup'):
            # For popup, redirect back to the same popup form with success message
            return reverse(self.get_success_url_name()) + "?popup=1"
        return super().get_success_url()
    
    def get_success_url_name(self):
        """Override this method to return the URL name for success redirect"""
        return f"inventory:{self.param_name}_create"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "popup_title": self.popup_title,
            "submit_text": self.submit_text,
            "param_name": self.param_name,
            "is_popup": self.request.GET.get('popup')
        })
        
        return context
    
    # No complex dispatch needed - simple popup system


class SizePopupMixin(PopupMixin):
    """Specific mixin for Size model"""
    popup_title = "Add New Size"
    submit_text = "Create Size"
    param_name = "new_size"


class ColorPopupMixin(PopupMixin):
    """Specific mixin for Color model"""
    popup_title = "Add New Color"
    submit_text = "Create Color"
    param_name = "new_color"


class CategoryPopupMixin(PopupMixin):
    """Specific mixin for Category model"""
    popup_title = "Add New Category"
    submit_text = "Create Category"
    param_name = "new_category"


class ClothTypePopupMixin(PopupMixin):
    """Specific mixin for ClothType model"""
    popup_title = "Add New Cloth Type"
    submit_text = "Create Cloth Type"
    param_name = "new_cloth_type"
