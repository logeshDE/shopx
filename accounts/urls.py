from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/',                             views.register_view,       name='register'),
    path('login/',                                views.login_view,          name='login'),
    path('logout/',                               views.logout_view,         name='logout'),
    path('resend-verification/',                  views.resend_verification, name='resend-verification'),
    path('verify-email/<uidb64>/<token>/',        views.verify_email,        name='verify-email'),
    path('profile/',                              views.profile_view,        name='profile'),
    path('profile/address/add/',                  views.add_address,         name='add-address'),
    path('profile/address/<int:pk>/edit/',        views.edit_address,        name='edit-address'),
    path('profile/address/<int:pk>/delete/',      views.delete_address,      name='delete-address'),
    path('profile/address/<int:pk>/set-default/', views.set_default_address, name='set-default-address'),
]