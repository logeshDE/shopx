from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('',                              views.wishlist_detail, name='detail'),
    path('toggle/<int:product_id>/',      views.toggle_wishlist, name='toggle'),
    path('move-to-cart/<int:item_id>/',   views.move_to_cart,    name='move-to-cart'),
]