from django.urls import path
from . import views

app_name = "customer"

urlpatterns = [
    path("", views.home, name="home"),
    path("download/", views.download_customers, name="download"),
    path("search/", views.search_customers_ajax, name="search_ajax"),
    path("create/", views.CreateCustomer.as_view(), name="create"),
    path("<int:pk>/", views.customer_detail, name="detail"),
    path("<int:pk>/edit/", views.EditCustomer.as_view(), name="edit"),
    path("<int:pk>/delete/", views.DeleteCustomer.as_view(), name="delete"),
]
