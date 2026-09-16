from .models import Cart


def cart_context(request):
    """Injects cart_count and wishlist_count into every template."""
    cart_count     = 0
    wishlist_count = 0

    # Cart count
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.get(user=request.user)
        else:
            key = request.session.session_key
            if key:
                cart = Cart.objects.get(session_key=key, user=None)
            else:
                return {'cart_count': 0, 'wishlist_count': 0}
        cart_count = cart.total_items
    except Cart.DoesNotExist:
        pass

    # Wishlist count (requires login)
    if request.user.is_authenticated:
        try:
            wishlist_count = request.user.wishlist.items.count()
        except Exception:
            wishlist_count = 0

    return {'cart_count': cart_count, 'wishlist_count': wishlist_count}