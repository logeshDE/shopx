from django.urls import path
from . import views

app_name = 'checkout'

urlpatterns = [
    path('address/',                       views.address_step,  name='address'),
    path('shipping/',                      views.shipping_step, name='shipping'),
    path('review/',                        views.review_step,   name='review'),
    path('success/<str:order_number>/',    views.order_success, name='success'),
    path('validate-coupon/', views.validate_coupon_ajax, name='validate-coupon'),
]