from django.urls import path
from . import views


app_name = "report"

urlpatterns = [
    path("invoice/<int:pk>/", views.createInvoice, name="invoice_pdf"),
    path("estimate/<int:pk>/", views.estimate_invoice, name="estimate_pdf"),
    path("barcode/<int:pk>/", views.generate_barcode, name="barcode"),
]
