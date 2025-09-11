from django.urls import path
from . import views


app_name = "report"

urlpatterns = [
    path("invoice/<int:pk>/", views.createInvoice, name="invoice_pdf"),
]
