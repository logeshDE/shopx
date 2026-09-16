from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import OrderItem
from products.models import Product
from .forms import ReviewForm
from .models import Review, ReviewImage


# ── Helpers ────────────────────────────────────────────────────

def _has_purchased(user, product):
    return OrderItem.objects.filter(
        order__user=user,
        order__payment_status='paid',
        product=product,
    ).exists()


# ── Write review ───────────────────────────────────────────────

@login_required
def write_review(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug, is_active=True)

    # Prevent duplicate reviews
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.info(request, 'You have already reviewed this product.')
        return redirect(product.get_absolute_url())

    form = ReviewForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            review                   = form.save(commit=False)
            review.product           = product
            review.user              = request.user
            review.verified_purchase = _has_purchased(request.user, product)
            review.save()

            # Handle multiple image uploads
            for img_file in request.FILES.getlist('images'):
                ReviewImage.objects.create(review=review, image=img_file)

            messages.success(request, 'Your review has been submitted. Thank you!')
            return redirect(product.get_absolute_url())

    return render(request, 'reviews/review_form.html', {
        'form':    form,
        'product': product,
        'action':  'Write',
    })


# ── Edit review ────────────────────────────────────────────────

@login_required
def edit_review(request, review_pk):
    review  = get_object_or_404(Review, pk=review_pk, user=request.user)
    product = review.product
    form    = ReviewForm(request.POST or None, instance=review)

    if request.method == 'POST':
        if form.is_valid():
            form.save()

            # Append new images (existing ones are kept)
            for img_file in request.FILES.getlist('images'):
                ReviewImage.objects.create(review=review, image=img_file)

            messages.success(request, 'Your review has been updated.')
            return redirect(product.get_absolute_url())

    return render(request, 'reviews/review_form.html', {
        'form':          form,
        'product':       product,
        'review':        review,
        'action':        'Edit',
        'existing_images': review.images.all(),
    })


# ── Delete review ──────────────────────────────────────────────

@login_required
@require_POST
def delete_review(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk, user=request.user)
    slug   = review.product.slug
    review.delete()
    messages.success(request, 'Your review has been removed.')
    return redirect('products:detail', slug=slug)


# ── Delete review image ────────────────────────────────────────

@login_required
@require_POST
def delete_review_image(request, image_pk):
    img = get_object_or_404(ReviewImage, pk=image_pk, review__user=request.user)
    img.image.delete(save=False)   # remove file from disk
    img.delete()
    messages.success(request, 'Image removed.')
    return redirect('reviews:edit', review_pk=img.review.pk)