from decimal import Decimal
from django.http import JsonResponse
from orders.models import Coupon

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.models import Address
from cart.utils import get_or_create_cart
from orders.models import Order, OrderItem, Coupon
from products.models import Inventory
from .constants import SHIPPING_OPTIONS
from .forms import ShippingForm, CouponForm
from .utils import calculate_totals

CHECKOUT_STEPS = [(1, 'Address'), (2, 'Shipping'), (3, 'Review')]


def _checkout_guard(request):
    """Returns the cart if OK, else redirects. Use at start of each step."""
    cart = get_or_create_cart(request)
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return None, redirect('cart:detail')
    return cart, None


# ── Step 1: Address ────────────────────────────────────────────

@login_required
def address_step(request):
    cart, redir = _checkout_guard(request)
    if redir:
        return redir

    addresses = request.user.addresses.all()

    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        if not address_id:
            messages.error(request, 'Please select a delivery address.')
            return redirect('checkout:address')
        # Verify the address belongs to the user
        if not addresses.filter(pk=address_id).exists():
            messages.error(request, 'Invalid address selected.')
            return redirect('checkout:address')
        request.session['checkout'] = {'address_id': int(address_id)}
        return redirect('checkout:shipping')

    # Pre-select the default address if coming fresh
    checkout    = request.session.get('checkout', {})
    selected_id = checkout.get('address_id')
    if not selected_id and addresses.exists():
        default = addresses.filter(is_default=True).first() or addresses.first()
        selected_id = default.pk

    return render(request, 'checkout/address.html', {
        'addresses':      addresses,
        'selected_id':    selected_id,
        'current_step':   1,
        'checkout_steps': CHECKOUT_STEPS,
    })


# ── Step 2: Shipping ───────────────────────────────────────────

@login_required
def shipping_step(request):
    cart, redir = _checkout_guard(request)
    if redir:
        return redir

    checkout = request.session.get('checkout', {})
    if 'address_id' not in checkout:
        messages.warning(request, 'Please select a delivery address first.')
        return redirect('checkout:address')

    current_method = checkout.get('shipping_method', 'standard')
    form           = ShippingForm(
        request.POST or None,
        initial={'shipping_method': current_method}
    )

    if request.method == 'POST' and form.is_valid():
        checkout['shipping_method'] = form.cleaned_data['shipping_method']
        request.session['checkout'] = checkout
        return redirect('checkout:review')

    totals = calculate_totals(cart, current_method)

    return render(request, 'checkout/shipping.html', {
        'form':             form,
        'shipping_options': SHIPPING_OPTIONS,
        'cart':             cart,
        'totals':           totals,
        'current_step':     2,
        'checkout_steps':   CHECKOUT_STEPS,
    })


# ── Step 3: Review + Place Order ──────────────────────────────

@login_required
def review_step(request):
    cart, redir = _checkout_guard(request)
    if redir:
        return redir

    checkout = request.session.get('checkout', {})
    if 'address_id' not in checkout:
        return redirect('checkout:address')
    if 'shipping_method' not in checkout:
        return redirect('checkout:shipping')

    address         = get_object_or_404(
                          Address, pk=checkout['address_id'], user=request.user
                      )
    shipping_method = checkout['shipping_method']
    coupon_discount = Decimal(checkout.get('coupon_discount', '0'))
    coupon_code     = checkout.get('coupon_code', '')
    coupon_form     = CouponForm(initial={'coupon_code': coupon_code})
    totals          = calculate_totals(cart, shipping_method, coupon_discount)
    items           = cart.items.select_related(
                          'product__brand'
                      ).prefetch_related('product__images')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'apply_coupon':
            coupon_form = CouponForm(request.POST)
            if coupon_form.is_valid():
                code = coupon_form.cleaned_data['coupon_code']
                if not code:
                    checkout.pop('coupon_code',     None)
                    checkout.pop('coupon_discount', None)
                    request.session['checkout'] = checkout
                    messages.info(request, 'Coupon removed.')
                else:
                    try:
                        coupon = Coupon.objects.get(code=code, is_active=True)
                        valid, error = coupon.validate(
                            user=request.user, subtotal=cart.subtotal
                        )
                        if valid:
                            discount = coupon.calculate_discount(cart.subtotal)
                            checkout['coupon_code']     = code
                            checkout['coupon_discount'] = str(discount)
                            request.session['checkout'] = checkout
                            messages.success(
                                request,
                                f'"{code}" applied — you save ₹{discount:,.0f}!'
                            )
                        else:
                            messages.error(request, error)
                    except Coupon.DoesNotExist:
                        messages.error(request, f'Coupon "{code}" is invalid or does not exist.')
            return redirect('checkout:review')

        # ── Place order ────────────────────────────────────────
        elif action == 'place_order':
            # Recompute totals server-side (never trust session values alone)
            totals = calculate_totals(cart, shipping_method, coupon_discount)

            order = Order.objects.create(
                user=request.user,
                # Address snapshot
                address_full_name = address.full_name,
                address_phone     = address.phone,
                address_line1     = address.address_line1,
                address_line2     = address.address_line2,
                address_city      = address.city,
                address_state     = address.state,
                address_pincode   = address.pincode,
                address_country   = address.country,
                # Financials
                subtotal        = totals['subtotal'],
                discount_amount = totals['coupon_discount'],
                shipping_cost   = totals['shipping_cost'],
                tax_amount      = totals['tax'],
                total           = totals['total'],
                shipping_method = shipping_method,
                coupon_code     = coupon_code,
            )

            # Snapshot each cart item and reduce inventory
            for item in cart.items.select_related(
                'product__brand'
            ).prefetch_related('product__images'):
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

            # Clear cart and checkout session
            cart.items.all().delete()
            if 'checkout' in request.session:
                del request.session['checkout']

            messages.success(request, f'Order #{order.order_number} placed successfully!')
            return redirect('checkout:success', order_number=order.order_number)

    return render(request, 'checkout/review.html', {
        'address':          address,
        'items':            items,
        'shipping_option':  SHIPPING_OPTIONS[shipping_method],
        'totals':           totals,
        'coupon_form':      coupon_form,
        'coupon_code':      coupon_code,
        'current_step':     3,
        'checkout_steps':   CHECKOUT_STEPS,
    })


# ── Success ────────────────────────────────────────────────────

@login_required
def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    items = order.items.all()
    return render(request, 'checkout/success.html', {
        'order': order,
        'items': items,
    })

def validate_coupon_ajax(request):
    """Quick client-side coupon check while the user is typing."""
    code    = request.GET.get('code', '').strip().upper()
    cart    = get_or_create_cart(request)

    if not code:
        return JsonResponse({'valid': False, 'message': 'Enter a coupon code.'})

    try:
        coupon = Coupon.objects.get(code=code, is_active=True)
        valid, error = coupon.validate(
            user=request.user if request.user.is_authenticated else None,
            subtotal=cart.subtotal,
        )
        if valid:
            discount = coupon.calculate_discount(cart.subtotal)
            return JsonResponse({
                'valid':    True,
                'discount': f'₹{discount:,.0f}',
                'message':  f'"{code}" saves you ₹{discount:,.0f}!',
            })
        return JsonResponse({'valid': False, 'message': error})
    except Coupon.DoesNotExist:
        return JsonResponse({'valid': False, 'message': 'Invalid coupon code.'})