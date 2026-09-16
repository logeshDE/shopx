from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',          admin.site.urls),
    path('accounts/',       include('accounts.urls')),
    path('cart/',           include('cart.urls')),
    path('wishlist/',       include('wishlist.urls')),
    path('checkout/',       include('checkout.urls')),
    path('payment/',        include('payment.urls')),
    path('orders/',         include('orders.urls')),
    path('reviews/',        include('reviews.urls')),
    path('notifications/',  include('notifications.urls')),  
    path('',                include('products.urls')),
    path('dashboard/', include('dashboard.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)