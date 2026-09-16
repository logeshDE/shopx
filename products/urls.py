from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('',                         views.home_view,           name='home'),
    path('products/',                views.product_list,        name='list'),
    path('products/autocomplete/',   views.autocomplete_view,   name='autocomplete'),
    path('products/<slug:slug>/',    views.product_detail,      name='detail'),
    path('category/<slug:slug>/',    views.product_by_category,  name='by-category'),
]