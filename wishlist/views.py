from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

from products.models import Product
from cart.models import CartItem
from cart.utils import get_or_create_cart
from .models import Wishlist, WishlistItem


def _get_or_create_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


@login_required
def wishlist_detail(request):
    wishlist = _get_or_create_wishlist(request.user)
    items    = wishlist.items.select_related(
        'product__brand', 'product__inventory'
    ).prefetch_related('product__images')

    # Collect product IDs already in cart for the "In Cart" badge
    cart          = get_or_create_cart(request)
    in_cart_ids   = set(
        cart.items.values_list('product_id', flat=True)
    )

    return render(request, 'wishlist/wishlist.html', {
        'wishlist':   wishlist,
        'items':      items,
        'in_cart_ids': in_cart_ids,
    })


@login_required
@require_POST
def toggle_wishlist(request, product_id):
    product  = get_object_or_404(Product, pk=product_id, is_active=True)
    wishlist = _get_or_create_wishlist(request.user)

    item, created = WishlistItem.objects.get_or_create(
        wishlist=wishlist, product=product
    )

    if not created:
        item.delete()
        in_wishlist = False
    else:
        in_wishlist = True

    return JsonResponse({
        'success':        True,
        'in_wishlist':    in_wishlist,
        'wishlist_count': wishlist.items.count(),
        'message': (
            f'"{product.name}" saved to wishlist.'
            if in_wishlist
            else f'"{product.name}" removed from wishlist.'
        ),
    })


@login_required
@require_POST
def move_to_cart(request, item_id):
    wishlist = _get_or_create_wishlist(request.user)
    w_item   = get_object_or_404(WishlistItem, pk=item_id, wishlist=wishlist)
    product  = w_item.product

    if product.stock_status == 'out_of_stock':
        messages.error(request, f'"{product.name}" is out of stock.')
    else:
        cart      = get_or_create_cart(request)
        c_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': 1}
        )
        if not created:
            c_item.quantity += 1
            c_item.save(update_fields=['quantity'])
        w_item.delete()
        messages.success(request, f'"{product.name}" moved to cart.')

    from django.shortcuts import redirect
    return redirect('wishlist:detail')