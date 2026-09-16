from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('',                        views.cart_detail,      name='detail'),
    path('add/<int:product_id>/',   views.add_to_cart,      name='add'),
    path('update/<int:item_id>/',   views.update_cart_item, name='update'),
    path('remove/<int:item_id>/',   views.remove_cart_item, name='remove'),
]