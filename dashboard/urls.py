from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',                                    views.home,                  name='home'),
    path('sales/',                              views.sales_analytics,       name='sales'),
    path('products/',                           views.product_analytics,     name='products'),
    path('customers/',                          views.customer_analytics,    name='customers'),
    path('inventory/',                          views.inventory_view,        name='inventory'),
    path('inventory/<int:inventory_id>/update/', views.update_inventory,     name='update-inventory'),
    path('users/',                              views.user_management,       name='users'),
    path('users/<int:user_id>/toggle/',         views.toggle_user,           name='toggle-user'),
    path('reports/',                            views.reports_view,          name='reports'),
    path('reports/sales/pdf/',                  views.export_sales_pdf,      name='export-sales-pdf'),
    path('reports/sales/excel/',                views.export_sales_excel,    name='export-sales-excel'),
    path('reports/inventory/excel/',            views.export_inventory_excel, name='export-inventory-excel'),
    
]