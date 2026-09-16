from decimal import Decimal

from accounts.models import Address
from cart.utils import get_or_create_cart
from checkout.constants import SHIPPING_OPTIONS
from checkout.utils import calculate_totals
from orders.models import (
    Order, OrderItem, OrderStatusHistory,
    Coupon, CouponUsage,
)
from products.models import Inventory


def create_order_from_checkout(request, gateway='cod'):
    """
    Reads checkout session data, creates Order + OrderItems,
    decrements inventory, records coupon usage, and clears the cart.

    Returns (order, None) on success or (None, error_str) on failure.
    Idempotent: safe to call only once per checkout session.
    """
    checkout = request.session.get('checkout', {})

    if 'address_id' not in checkout:
        return None, 'No delivery address found. Please start checkout again.'
    if 'shipping_method' not in checkout:
        return None, 'No shipping method selected.'

    cart = get_or_create_cart(request)
    if not cart.items.exists():
        return None, 'Your cart is empty.'

    # ── Resolve address ────────────────────────────────────────
    try:
        address = Address.objects.get(pk=checkout['address_id'], user=request.user)
    except Address.DoesNotExist:
        return None, 'Saved address no longer exists. Please choose another.'

    # ── Totals ─────────────────────────────────────────────────
    shipping_method = checkout.get('shipping_method', 'standard')
    coupon_code     = checkout.get('coupon_code',     '')
    coupon_discount = Decimal(checkout.get('coupon_discount', '0'))
    totals          = calculate_totals(cart, shipping_method, coupon_discount)

    # ── Create Order ───────────────────────────────────────────
    order = Order.objects.create(
        user              = request.user,
        address_full_name = address.full_name,
        address_phone     = address.phone,
        address_line1     = address.address_line1,
        address_line2     = address.address_line2,
        address_city      = address.city,
        address_state     = address.state,
        address_pincode   = address.pincode,
        address_country   = address.country,
        subtotal          = totals['subtotal'],
        discount_amount   = totals['coupon_discount'],
        shipping_cost     = totals['shipping_cost'],
        tax_amount        = totals['tax'],
        total             = totals['total'],
        shipping_method   = shipping_method,
        coupon_code       = coupon_code,
        status            = 'pending',
        payment_status    = 'pending',
    )

    # ── Create OrderItems + decrement inventory ────────────────
    cart_items = cart.items.select_related(
        'product__brand'
    ).prefetch_related('product__images')

    for item in cart_items:
        img = item.product.primary_image
        OrderItem.objects.create(
            order        = order,
            product      = item.product,
            product_name = item.product.name,
            product_slug = item.product.slug,
            brand_name   = item.product.brand.name if item.product.brand else '',
            image_url    = img.image.url if img else '',
            price        = item.unit_price,
            quantity     = item.quantity,
        )
        try:
            inv          = item.product.inventory
            inv.quantity = max(0, inv.quantity - item.quantity)
            inv.save(update_fields=['quantity', 'updated_at'])
        except Inventory.DoesNotExist:
            pass

    # ── Record coupon usage ────────────────────────────────────
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            Coupon.objects.filter(pk=coupon.pk).update(
                used_count=coupon.used_count + 1
            )
            CouponUsage.objects.get_or_create(
                coupon=coupon, user=request.user, order=order
            )
        except Coupon.DoesNotExist:
            pass

    # ── First status history entry ─────────────────────────────
    OrderStatusHistory.objects.create(
        order      = order,
        status     = 'pending',
        note       = f'Order placed via {gateway.title()}.',
        created_by = request.user,
    )

    # ── Clear cart + checkout session ──────────────────────────
    cart.items.all().delete()
    request.session.pop('checkout', None)

    return order, None