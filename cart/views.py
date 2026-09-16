import json
from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from products.models import Product
from .models import CartItem
from .utils import get_or_create_cart


# ── Cart page ──────────────────────────────────────────────────

def cart_detail(request):
    cart  = get_or_create_cart(request)
    items = cart.items.select_related(
        'product__brand', 'product__inventory'
    ).prefetch_related('product__images')

    return render(request, 'cart/cart.html', {
        'cart':     cart,
        'items':    items,
        'subtotal': cart.subtotal,
        'savings':  cart.total_savings,
    })


# ── AJAX: Add ──────────────────────────────────────────────────

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)

    try:
        data = json.loads(request.body)
        qty  = max(1, int(data.get('quantity', 1)))
    except (json.JSONDecodeError, ValueError, TypeError):
        qty = 1

    # Inventory check
    try:
        available = product.inventory.quantity
        if available == 0:
            return JsonResponse({'success': False, 'message': 'This product is out of stock.'})
        qty = min(qty, available)
    except Exception:
        pass

    cart = get_or_create_cart(request)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product,
        defaults={'quantity': qty}
    )

    if not created:
        try:
            max_qty = product.inventory.quantity
        except Exception:
            max_qty = 9999
        item.quantity = min(item.quantity + qty, max_qty)
        item.save(update_fields=['quantity'])

    return JsonResponse({
        'success':        True,
        'cart_count':     cart.total_items,
        'already_in_cart': not created,
        'message': (
            f'"{product.name}" added to cart!'
            if created
            else f'Cart updated: {item.quantity} × "{product.name}"'
        ),
    })


# ── AJAX: Update quantity ──────────────────────────────────────

@require_POST
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    try:
        data = json.loads(request.body)
        qty  = int(data.get('quantity', 1))
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Invalid data.'}, status=400)

    if qty < 1:
        return JsonResponse({'success': False, 'message': 'Minimum quantity is 1.'}, status=400)

    # Inventory check
    try:
        available = item.product.inventory.quantity
        if qty > available:
            return JsonResponse({
                'success': False,
                'message': f'Only {available} units available.',
            }, status=400)
    except Exception:
        pass

    item.quantity = qty
    item.save(update_fields=['quantity'])

    # Recalculate totals from DB
    all_items = list(cart.items.select_related('product'))
    subtotal  = sum(i.total_price    for i in all_items)
    savings   = sum(i.discount_amount for i in all_items)
    count     = sum(i.quantity        for i in all_items)

    return JsonResponse({
        'success':    True,
        'cart_count': count,
        'item_total': f'₹{item.total_price:,.0f}',
        'subtotal':   f'₹{subtotal:,.0f}',
        'savings':    f'₹{savings:,.0f}',
        'total':      f'₹{subtotal:,.0f}',
    })


# ── AJAX: Remove ───────────────────────────────────────────────

@require_POST
def remove_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()

    all_items = list(cart.items.select_related('product'))
    subtotal  = sum(i.total_price    for i in all_items)
    savings   = sum(i.discount_amount for i in all_items)
    count     = sum(i.quantity        for i in all_items)

    return JsonResponse({
        'success':    True,
        'cart_count': count,
        'subtotal':   f'₹{subtotal:,.0f}',
        'savings':    f'₹{savings:,.0f}',
        'total':      f'₹{subtotal:,.0f}',
    })