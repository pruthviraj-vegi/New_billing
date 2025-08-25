from django.urls import path
from . import views

app_name = "invoice"

urlpatterns = [
    path("", views.invoiceHome, name="home"),
    path("create-invoice/<int:pk>/", views.CreateInvoice.as_view(), name="create_invoice"),
    path("detail/<int:pk>/", views.InvoiceDetail.as_view(), name="detail"),
    path("edit/<int:pk>/", views.InvoiceEdit.as_view(), name="edit"),
    path("delete/<int:pk>/", views.InvoiceDelete.as_view(), name="delete"),
    path("download/", views.InvoiceDownload.as_view(), name="download"),
]
