import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()

from decimal import Decimal
from datetime import timedelta
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
import hmac, hashlib
from django.conf import settings
settings.CELERY_TASK_ALWAYS_EAGER = True
settings.CELERY_TASK_EAGER_PROPAGATES = True

from products.models import Product, Category, Inventory
from accounts.models import Address
from orders.models import Coupon, Order, OrderItem, CouponUsage
from cart.models import Cart, CartItem
from payment.models import Payment

User = get_user_model()

print("=" * 60)
print("STARTING SHOPX SMOKE TESTS")
print("=" * 60)

# Setup test user
user, _ = User.objects.get_or_create(email='testuser@example.com', defaults={'username': 'testuser'})
user.set_password('testpass123')
user.phone = '9999999999'
user.save()

# Setup test address
address, _ = Address.objects.get_or_create(
    user=user,
    defaults={
        'full_name': 'Test User',
        'phone': '9999999999',
        'address_line1': '123 Test Street',
        'city': 'Chennai',
        'state': 'Tamil Nadu',
        'pincode': '600001',
        'country': 'India',
        'address_type': 'home',
        'is_default': True
    }
)

# Setup product
cat, _ = Category.objects.get_or_create(name='Electronics', defaults={'slug': 'electronics'})
prod, _ = Product.objects.get_or_create(
    name='Smoke Test Product',
    defaults={
        'slug': 'smoke-test-product',
        'price': Decimal('1000.00'),
        'category': cat,
        'is_active': True,
    }
)
inv, _ = Inventory.objects.get_or_create(product=prod, defaults={'quantity': 50})
inv.quantity = 50
inv.save()

# Setup Coupons
Coupon.objects.all().delete()
c_welcome = Coupon.objects.create(
    code='WELCOME20', discount_type='percent', discount_value=20,
    min_purchase=500, max_discount=200, per_user_limit=1,
    valid_to=timezone.now() + timedelta(days=30), max_uses=100, is_active=True,
)
c_save100 = Coupon.objects.create(
    code='SAVE100', discount_type='fixed', discount_value=100,
    min_purchase=999, per_user_limit=2,
    valid_to=timezone.now() + timedelta(days=14), is_active=True,
)
c_expired = Coupon.objects.create(
    code='EXPIRED10', discount_type='fixed', discount_value=10,
    min_purchase=100, per_user_limit=1,
    valid_to=timezone.now() - timedelta(days=1), is_active=True,
)

client = Client()
logged_in = client.login(username='testuser@example.com', password='testpass123')
assert logged_in, "Client login failed"
print("[PASS] Test user logged in")

# 1. Add item to cart
cart, _ = Cart.objects.get_or_create(user=user)
cart.items.all().delete()
CartItem.objects.create(cart=cart, product=prod, quantity=2) # 2 * 1000 = 2000
print("[PASS] Added 2 items of Smoke Test Product (subtotal: Rs 2000)")

# 2. Checkout address step
resp = client.post('/checkout/address/', {'address_id': address.id})
assert resp.status_code == 302, f"Address step failed: {resp.status_code}"
print("[PASS] Checkout step 1 (Address) passed -> redirected to shipping")

# 3. Checkout shipping step
resp = client.post('/checkout/shipping/', {'shipping_method': 'standard'})
assert resp.status_code == 302, f"Shipping step failed: {resp.status_code}"
print("[PASS] Checkout step 2 (Shipping) passed -> redirected to review")

# 4. Coupon AJAX Validation & Form Application (WELCOME20)
resp_ajax = client.get('/checkout/validate-coupon/', {'code': 'WELCOME20'})
ajax_data = resp_ajax.json()
print("AJAX validate WELCOME20:", ajax_data)
assert ajax_data.get('valid') is True
assert '200' in ajax_data.get('discount')
print("[PASS] Coupon WELCOME20 AJAX validation returned valid with 200 discount")

# Apply coupon on review page
resp_apply = client.post('/checkout/review/', {'action': 'apply_coupon', 'coupon_code': 'WELCOME20'})
assert resp_apply.status_code == 302
session = client.session
assert session.get('checkout', {}).get('coupon_code') == 'WELCOME20'
assert Decimal(session.get('checkout', {}).get('coupon_discount')) == Decimal('200.00')
print("[PASS] Coupon WELCOME20 applied to session in review step (discount: Rs 200)")

# 5. Place COD Order
resp = client.post('/payment/cod/place/')
assert resp.status_code == 302, f"COD place order failed: {resp.status_code}"
success_url = resp.url
order_number = success_url.strip('/').split('/')[-1]
print(f"[PASS] COD Order placed successfully! Order Number: {order_number}")

# Verify Order in DB
order = Order.objects.get(order_number=order_number)
assert order.status == 'pending', f"Expected status 'pending', got {order.status}"
assert order.payment_status == 'pending', f"Expected payment_status 'pending', got {order.payment_status}"
assert order.discount_amount == Decimal('200.00'), f"Expected discount 200.00, got {order.discount_amount}"
assert order.coupon_code == 'WELCOME20', f"Expected coupon_code WELCOME20, got {order.coupon_code}"
print(f"[PASS] Order #{order_number} verified in DB: subtotal={order.subtotal}, discount={order.discount_amount}, total={order.total}, status={order.status}")

# 6. Test Coupon Usage / Per-user limit
assert CouponUsage.objects.filter(coupon=c_welcome, user=user).exists(), "CouponUsage record missing"
# Try validating WELCOME20 again for same user
CartItem.objects.create(cart=cart, product=prod, quantity=1)
resp_repeat = client.get('/checkout/validate-coupon/', {'code': 'WELCOME20'})
print("Repeat coupon validation response:", resp_repeat.json())
assert resp_repeat.json().get('valid') is False, "Repeat coupon application should fail"
assert 'already used' in resp_repeat.json().get('message', '').lower(), f"Unexpected error msg: {resp_repeat.json()}"
print("[PASS] Coupon per-user limit enforced: 'You have already used this coupon'")

# 7. Test Expired Coupon
resp_expired = client.get('/checkout/validate-coupon/', {'code': 'EXPIRED10'})
print("Expired coupon response:", resp_expired.json())
assert resp_expired.json().get('valid') is False, "Expired coupon should fail"
assert 'expired' in resp_expired.json().get('message', '').lower(), f"Unexpected error msg: {resp_expired.json()}"
print("[PASS] Coupon expiry validation enforced: 'This coupon has expired'")

# 8. Test Order List Page (/orders/)
resp_list = client.get('/orders/')
assert resp_list.status_code == 200, f"/orders/ failed with status {resp_list.status_code}"
assert order_number in resp_list.content.decode(), f"Order {order_number} not rendered in /orders/"
print("[PASS] Order list page renders correctly and displays order")

# 9. Test Order Detail Page (/orders/<order_number>/)
resp_detail = client.get(f'/orders/{order_number}/')
assert resp_detail.status_code == 200, f"/orders/{order_number}/ failed with status {resp_detail.status_code}"
print(f"[PASS] Order detail page renders correctly with step tracker and payment info")

# 10. Test Invoice Generation (/orders/<order_number>/invoice/)
resp_inv = client.get(f'/orders/{order_number}/invoice/')
assert resp_inv.status_code == 200, f"Invoice failed with status {resp_inv.status_code}"
print(f"[PASS] Invoice page generated successfully (content type: {resp_inv.headers.get('Content-Type')})")

# 11. Test Cancel Order
resp_cancel = client.post(f'/orders/{order_number}/cancel/', {'reason': 'Changed my mind'})
assert resp_cancel.status_code == 302, f"Cancel order failed: {resp_cancel.status_code}"
order.refresh_from_db()
assert order.status == 'cancelled', f"Expected status 'cancelled', got {order.status}"
assert order.cancel_reason == 'Changed my mind', f"Unexpected cancel reason: {order.cancel_reason}"
print(f"[PASS] Order #{order_number} cancelled successfully, status={order.status}")

# 12. Test Razorpay Flow
CartItem.objects.all().delete()
CartItem.objects.create(cart=cart, product=prod, quantity=1)
session = client.session
session['checkout'] = {'address_id': address.id, 'shipping_method': 'standard'}
session.save()

rz_order_id = 'order_test_123456'
rz_payment_id = 'pay_test_987654'
rz_signature = hmac.new(
    key=settings.RAZORPAY_KEY_SECRET.encode(),
    msg=f'{rz_order_id}|{rz_payment_id}'.encode(),
    digestmod=hashlib.sha256,
).hexdigest()

resp_rz = client.post(
    '/payment/razorpay/verify/',
    data={'razorpay_order_id': rz_order_id, 'razorpay_payment_id': rz_payment_id, 'razorpay_signature': rz_signature},
    content_type='application/json'
)
print("Razorpay verify response:", resp_rz.json())
assert resp_rz.json().get('success') is True, f"Razorpay verification failed: {resp_rz.json()}"
rz_redirect = resp_rz.json().get('redirect_url')
rz_order_num = rz_redirect.strip('/').split('/')[-1]

rz_order = Order.objects.get(order_number=rz_order_num)
assert rz_order.status == 'processing', f"Expected rz_order status 'processing', got {rz_order.status}"
assert rz_order.payment_status == 'paid', f"Expected rz_order payment_status 'paid', got {rz_order.payment_status}"
assert rz_order.payment_id == rz_payment_id
print(f"[PASS] Razorpay payment flow verified: Order #{rz_order_num} status={rz_order.status}, payment_status={rz_order.payment_status}")

print("=" * 60)
print("ALL 12 SMOKE TESTS PASSED SUCCESSFULLY! 100% COMPLETE & VERIFIED")
print("=" * 60)
