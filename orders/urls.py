from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('',                              views.order_list,       name='list'),
    path('<str:order_number>/',           views.order_detail,     name='detail'),
    path('<str:order_number>/cancel/',    views.cancel_order,     name='cancel'),
    path('<str:order_number>/return/',    views.return_order,     name='return'),
    path('<str:order_number>/invoice/',   views.download_invoice, name='invoice'),
]