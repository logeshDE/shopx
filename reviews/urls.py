from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('<slug:product_slug>/write/',      views.write_review,       name='write'),
    path('<int:review_pk>/edit/',           views.edit_review,        name='edit'),
    path('<int:review_pk>/delete/',         views.delete_review,      name='delete'),
    path('image/<int:image_pk>/delete/',    views.delete_review_image, name='delete-image'),
]