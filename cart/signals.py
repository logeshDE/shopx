from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Cart, CartItem


@receiver(user_logged_in)
def merge_cart_on_login(sender, request, user, **kwargs):
    session_key = request.session.session_key
    if not session_key:
        return

    try:
        session_cart = Cart.objects.prefetch_related('items').get(
            session_key=session_key, user=None
        )
    except Cart.DoesNotExist:
        return

    if not session_cart.items.exists():
        session_cart.delete()
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for s_item in session_cart.items.all():
        u_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            product=s_item.product,
            defaults={'quantity': s_item.quantity},
        )
        if not created:
            # Cap at available inventory
            try:
                max_qty = s_item.product.inventory.quantity
            except Exception:
                max_qty = 9999
            u_item.quantity = min(u_item.quantity + s_item.quantity, max_qty)
            u_item.save(update_fields=['quantity'])

    session_cart.delete()