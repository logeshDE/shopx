from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('',                         views.payment_page,          name='page'),
    # Razorpay
    path('razorpay/create-order/',   views.razorpay_create_order, name='razorpay-create'),
    path('razorpay/verify/',         views.razorpay_verify,       name='razorpay-verify'),
    # COD
    path('cod/place/',               views.cod_place_order,       name='cod'),
    # Webhooks
    path('webhook/razorpay/',        views.razorpay_webhook,      name='webhook-razorpay'),
]
