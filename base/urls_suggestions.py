from django.urls import path
from . import suggestions


app_name = "suggestions"

urlpatterns = [
    path("member/", suggestions.customer_all_suggestions, name="customer_all"),
    path("invoice/", suggestions.invoice_all_suggestions, name="invoice_all"),
    path("product/", suggestions.product_all_suggestions, name="product_all"),
    path("product-variant/", suggestions.product_variant_all_suggestions, name="product_variant_all"),
]
