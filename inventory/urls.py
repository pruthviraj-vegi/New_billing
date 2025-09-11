from django.urls import path
from . import views, _views

app_name = "inventory"

urlpatterns = [
    # Dashboard
    path("dashboard/", views.inventory_dashboard, name="dashboard"),
    path("low-stock/", views.low_stock_page, name="low_stock"),
    path("full-product/create/", views.CreateProduct.as_view(), name="product_create"),
    path(
        "variant/<int:pk>/delete/",
        views.DeleteProductVariant.as_view(),
        name="variant_delete",
    ),
    path(
        "variant/<int:pk>/update/",
        views.variant_update,
        name="variant_update",
    ),
    # Cloth Type Management
    path("cloth/", _views.cloth_home, name="cloth_home"),
    path("cloth/create/", _views.CreateClothType.as_view(), name="cloth_create"),
    path("cloth/<int:pk>/edit/", _views.UpdateClothType.as_view(), name="cloth_edit"),
    path(
        "cloth/<int:pk>/delete/", _views.DeleteClothType.as_view(), name="cloth_delete"
    ),
    # Color Management
    path("color/", _views.color_home, name="color_home"),
    path("color/create/", _views.CreateColor.as_view(), name="color_create"),
    path("color/<int:pk>/edit/", _views.UpdateColor.as_view(), name="color_edit"),
    path("color/<int:pk>/delete/", _views.DeleteColor.as_view(), name="color_delete"),
    # Size Management
    path("size/", _views.size_home, name="size_home"),
    path("size/create/", _views.CreateSize.as_view(), name="size_create"),
    path("size/<int:pk>/edit/", _views.UpdateSize.as_view(), name="size_edit"),
    path("size/<int:pk>/delete/", _views.DeleteSize.as_view(), name="size_delete"),
    path("size/create-ajax/", views.create_size_ajax, name="size_create_ajax"),
    # Category Management
    path("category/", _views.category_home, name="category_home"),
    path("category/fetch/", _views.fetch_categories, name="category_fetch"),
    path("category/suggestions/", _views.search_suggestions, name="category_suggestions"),
    path("category/create/", _views.CreateCategory.as_view(), name="category_create"),
    path(
        "category/<int:pk>/edit/", _views.UpdateCategory.as_view(), name="category_edit"
    ),
    path(
        "category/<int:pk>/delete/",
        _views.DeleteCategory.as_view(),
        name="category_delete",
    ),
   
    # Supplier Invoice Tracking
    path(
        "supplier-invoices/",
        views.supplier_invoice_tracking,
        name="supplier_invoice_tracking",
    ),
    path(
        "supplier-invoices/<str:invoice_number>/",
        views.supplier_invoice_details,
        name="supplier_invoice_details",
    ),
    path(
        "variant/<int:variant_id>/invoice-analytics/",
        views.product_invoice_analytics,
        name="product_invoice_analytics",
    ),
    path(
        "supplier/<int:supplier_id>/analytics/",
        views.supplier_analytics,
        name="supplier_analytics",
    ),
]
