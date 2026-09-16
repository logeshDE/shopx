import hashlib
import hmac
import json
from decimal import Decimal

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cart.utils import get_or_create_cart
from checkout.utils import calculate_totals
from orders.models import Order, OrderStatusHistory
from .helpers import create_order_from_checkout
from .models import Payment


# ── Internal helpers ───────────────────────────────────────────

def _razorpay():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

def _checkout_totals(request):
    cart     = get_or_create_cart(request)
    checkout = request.session.get('checkout', {})
    discount = Decimal(checkout.get('coupon_discount', '0'))
    method   = checkout.get('shipping_method', 'standard')
    return cart, calculate_totals(cart, method, discount)


# ── Payment selection page ─────────────────────────────────────

@login_required
def payment_page(request):
    checkout = request.session.get('checkout', {})
    if 'address_id' not in checkout:
        messages.warning(request, 'Please select a delivery address.')
        return redirect('checkout:address')
    if 'shipping_method' not in checkout:
        messages.warning(request, 'Please select a shipping method.')
        return redirect('checkout:shipping')

    cart, totals = _checkout_totals(request)

    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:detail')

    return render(request, 'payment/payment.html', {
        'cart':                   cart,
        'totals':                 totals,
        'razorpay_key':           settings.RAZORPAY_KEY_ID,
    })


# ══ Razorpay ══════════════════════════════════════════════════

@login_required
@require_POST
def razorpay_create_order(request):
    """Creates a Razorpay order and returns its ID to the frontend."""
    _, totals     = _checkout_totals(request)
    amount_paise  = int(totals['total'] * 100)   # Razorpay works in paise

    try:
        rz_order = _razorpay().order.create({
            'amount':          amount_paise,
            'currency':        'INR',
            'payment_capture': 1,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({
        'success':     True,
        'order_id':    rz_order['id'],
        'amount':      amount_paise,
        'currency':    'INR',
        'key':         settings.RAZORPAY_KEY_ID,
        'name':        'ShopX',
        'description': 'Order Payment',
        'prefill': {
            'name':    request.user.get_full_name() or request.user.email,
            'email':   request.user.email,
            'contact': request.user.phone or '',
        },
    })


@login_required
@require_POST
def razorpay_verify(request):
    """Verifies Razorpay signature and creates the Django order."""
    try:
        data = json.loads(request.body)
        rz_payment_id = data.get('razorpay_payment_id', '')
        rz_order_id   = data.get('razorpay_order_id',   '')
        rz_signature  = data.get('razorpay_signature',  '')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)

    # HMAC-SHA256 verification
    expected = hmac.new(
        key      = settings.RAZORPAY_KEY_SECRET.encode(),
        msg      = f'{rz_order_id}|{rz_payment_id}'.encode(),
        digestmod = hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, rz_signature):
        return JsonResponse(
            {'success': False, 'message': 'Payment signature verification failed.'},
            status=400
        )

    # Signature valid — create order
    order, error = create_order_from_checkout(request, gateway='razorpay')
    if error:
        return JsonResponse({'success': False, 'message': error}, status=400)

    Payment.objects.create(
        order              = order,
        gateway            = 'razorpay',
        gateway_order_id   = rz_order_id,
        gateway_payment_id = rz_payment_id,
        gateway_signature  = rz_signature,
        amount             = order.total,
        status             = 'completed',
    )

    order.payment_id     = rz_payment_id
    order.payment_status = 'paid'
    order.status         = 'processing'
    order.save(update_fields=['payment_id', 'payment_status', 'status'])

    OrderStatusHistory.objects.create(
        order      = order,
        status     = 'processing',
        note       = f'Payment confirmed via Razorpay (ID: {rz_payment_id}).',
        created_by = request.user,
    )

    return JsonResponse({
        'success':      True,
        'redirect_url': f'/checkout/success/{order.order_number}/',
    })

@login_required
@require_POST
def cod_place_order(request):
    order, error = create_order_from_checkout(request, gateway='cod')
    if error:
        messages.error(request, error)
        return redirect('checkout:review')

    Payment.objects.create(
        order   = order,
        gateway = 'cod',
        amount  = order.total,
        status  = 'pending',   # COD: pending until delivery
    )
    return redirect('checkout:success', order_number=order.order_number)


# ══ Webhooks (async safety net) ═══════════════════════════════

@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Razorpay calls this asynchronously on payment events.
    Acts as a safety net in case the browser closed before verify ran.
    Requires the webhook secret configured in the Razorpay dashboard.
    For local testing: use ngrok to expose your localhost.
    """
    payload   = request.body
    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')

    expected = hmac.new(
        key      = settings.RAZORPAY_KEY_SECRET.encode(),
        msg      = payload,
        digestmod = hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return HttpResponse('Bad signature', status=400)

    try:
        event   = json.loads(payload)
        etype   = event.get('event', '')

        if etype == 'payment.captured':
            pid = event['payload']['payment']['entity']['id']
            try:
                pmt = Payment.objects.get(gateway_payment_id=pid)
                if pmt.status != 'completed':
                    pmt.status = 'completed'
                    pmt.save(update_fields=['status', 'updated_at'])
                    pmt.order.payment_status = 'paid'
                    pmt.order.save(update_fields=['payment_status'])
            except Payment.DoesNotExist:
                pass

        elif etype == 'payment.failed':
            pid = event['payload']['payment']['entity']['id']
            try:
                pmt        = Payment.objects.get(gateway_payment_id=pid)
                pmt.status = 'failed'
                pmt.save(update_fields=['status', 'updated_at'])
                pmt.order.payment_status = 'failed'
                pmt.order.save(update_fields=['payment_status'])
            except Payment.DoesNotExist:
                pass

    except (json.JSONDecodeError, KeyError):
        pass

    return HttpResponse(status=200)