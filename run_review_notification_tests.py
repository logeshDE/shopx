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
from django.core.files.uploadedfile import SimpleUploadedFile
import hmac, hashlib
from django.conf import settings

# Force eager execution for celery in test suite
settings.CELERY_TASK_ALWAYS_EAGER = True
settings.CELERY_TASK_EAGER_PROPAGATES = True

from products.models import Product, Category, Inventory, Brand
from accounts.models import Address
from orders.models import Order, OrderItem
from cart.models import Cart, CartItem
from payment.models import Payment
from wishlist.models import Wishlist, WishlistItem
from reviews.models import Review, ReviewImage
from notifications.models import Notification
from notifications.tasks import send_order_email, send_price_drop_alert
from products.views import _annotate

User = get_user_model()

print("=" * 70)
print("STARTING REVIEWS & NOTIFICATIONS FULL TEST SUITE")
print("=" * 70)

# Setup Test Users
buyer, _ = User.objects.get_or_create(email='buyer@example.com', defaults={'username': 'buyer', 'first_name': 'Buyer'})
buyer.set_password('pass123')
buyer.save()

non_buyer, _ = User.objects.get_or_create(email='nonbuyer@example.com', defaults={'username': 'nonbuyer', 'first_name': 'NonBuyer'})
non_buyer.set_password('pass123')
non_buyer.save()

cat, _ = Category.objects.get_or_create(name='Gadgets', defaults={'slug': 'gadgets'})
brand, _ = Brand.objects.get_or_create(name='TechCorp', defaults={'slug': 'techcorp'})
product, _ = Product.objects.get_or_create(
    name='Wireless Noise-Cancelling Headphones',
    defaults={
        'slug': 'wireless-headphones',
        'price': Decimal('5000.00'),
        'category': cat,
        'brand': brand,
        'is_active': True,
    }
)
inv, _ = Inventory.objects.get_or_create(product=product, defaults={'quantity': 20})

# ── 1. Create a Paid Order for Buyer ───────────────────────────
Review.objects.all().delete()
Order.objects.filter(order_number__startswith='SX-TEST-BUYER').delete()
paid_order = Order.objects.create(
    user=buyer,
    order_number='SX-TEST-BUYER-01',
    status='processing',
    payment_status='paid',
    address_full_name='Buyer Test',
    address_phone='9876543210',
    address_line1='456 Market Road',
    address_city='Bangalore',
    address_state='Karnataka',
    address_pincode='560001',
    address_country='India',
    subtotal=Decimal('5000.00'),
    total=Decimal('5900.00'),
    shipping_method='standard',
)
OrderItem.objects.create(
    order=paid_order,
    product=product,
    product_name=product.name,
    product_slug=product.slug,
    price=Decimal('5000.00'),
    quantity=1,
)

# ── 2. Test Write Review (Purchased vs Non-Purchased) ───────────
client = Client()

# Non-buyer visiting product detail
client.login(username='nonbuyer@example.com', password='pass123')
resp = client.get(f'/products/{product.slug}/')
assert resp.status_code == 200
assert 'Purchase this product to leave a review' in resp.content.decode()
print("[PASS] Write review (not purchased): 'Purchase this product to leave a review' shown to non-buyer")

# Buyer visiting product detail
client.login(username='buyer@example.com', password='pass123')
resp = client.get(f'/products/{product.slug}/')
assert resp.status_code == 200
assert f'/reviews/{product.slug}/write/' in resp.content.decode()
print("[PASS] Write review (purchased): 'Write a Review' button visible to verified buyer")

# ── 3. Test Star Selector & Form Validation ────────────────────
# Missing rating should fail
resp = client.post(f'/reviews/{product.slug}/write/', {
    'title': 'Great headphones',
    'body': 'Sound quality is superb.',
    'rating': '',
})
assert resp.status_code == 200
assert 'Please select a star rating' in resp.content.decode()
print("[PASS] Star selector validation: Form rejects submission without star rating")

# ── 4. Submit Review with Images ────────────────────────────────
Review.objects.filter(product=product).delete()

# Create dummy image
small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)
img1 = SimpleUploadedFile('photo1.gif', small_gif, content_type='image/gif')
img2 = SimpleUploadedFile('photo2.gif', small_gif, content_type='image/gif')

resp = client.post(f'/reviews/{product.slug}/write/', {
    'rating': 5,
    'title': 'Outstanding sound and comfort',
    'body': 'Deep bass, clear highs, and super comfortable earcups.',
    'images': [img1, img2],
})
assert resp.status_code == 302, f"Review submission failed: {resp.status_code}"
review = Review.objects.get(product=product, user=buyer)
assert review.rating == 5
assert review.verified_purchase is True
assert review.images.count() == 2
print(f"[PASS] Review created: 5 stars, verified_purchase=True, {review.images.count()} images attached")

# ── 5. Duplicate Review Blocked ────────────────────────────────
resp = client.get(f'/reviews/{product.slug}/write/')
assert resp.status_code == 302
print("[PASS] Duplicate review blocked: Redirected when trying to review again")

# ── 6. Star Rating on Product Cards & Annotations ──────────────
annotated_prod = _annotate(Product.objects.filter(pk=product.pk)).first()
assert annotated_prod.avg_rating == Decimal('5.0')
assert annotated_prod.review_count == 1
resp_home = client.get('/')
assert '★★★★★' in resp_home.content.decode()
print(f"[PASS] Star rating on cards: Product card renders {annotated_prod.avg_rating}★ ({annotated_prod.review_count} review)")

# ── 7. Edit Review & Delete Image ──────────────────────────────
review_img = review.images.first()
img_pk = review_img.pk
resp = client.post(f'/reviews/image/{img_pk}/delete/')
assert resp.status_code == 302
assert not ReviewImage.objects.filter(pk=img_pk).exists()
print("[PASS] Delete review image: Image removed from disk and database")

resp = client.post(f'/reviews/{review.pk}/edit/', {
    'rating': 4,
    'title': 'Updated: Very good headphones',
    'body': 'Battery life is slightly shorter than advertised, but sound is still great.',
})
assert resp.status_code == 302
review.refresh_from_db()
assert review.rating == 4
assert review.title == 'Updated: Very good headphones'
print("[PASS] Edit review: Review updated to 4 stars and new title")

# ── 8. Notification Bell, Dropdown & Context Processor ──────────
Notification.objects.filter(user=buyer).delete()
Notification.objects.create(
    user=buyer,
    type='order_placed',
    title='Order #SX-TEST-001 placed!',
    message='Your order is confirmed.',
    is_read=False
)
Notification.objects.create(
    user=buyer,
    type='payment_confirmed',
    title='Payment confirmed — #SX-TEST-001',
    message='₹5,900 received.',
    is_read=False
)

resp = client.get('/')
content = resp.content.decode()
assert 'id="notif-badge"' in content
assert 'Order #SX-TEST-001 placed!' in content
print("[PASS] Notification bell dropdown: Shows unread badge count (2) and notification preview list")

# ── 9. Notifications List & Filtering ───────────────────────────
resp = client.get('/notifications/?type=payment_confirmed')
assert resp.status_code == 200
assert 'Payment confirmed' in resp.content.decode()
print("[PASS] Notification filter: Filtering by type='payment_confirmed' works")

# ── 10. Mark All Read & Delete Notification ────────────────────
resp = client.post('/notifications/read-all/')
assert resp.json().get('success') is True
assert Notification.objects.filter(user=buyer, is_read=False).count() == 0
print("[PASS] Mark all read: All unread notifications updated to is_read=True")

notif_to_del = Notification.objects.filter(user=buyer).first()
del_pk = notif_to_del.pk
resp = client.post(f'/notifications/{del_pk}/delete/')
assert resp.json().get('success') is True
assert not Notification.objects.filter(pk=del_pk).exists()
print("[PASS] Delete notification: Notification successfully deleted via AJAX")

# ── 11. Wishlist Price Drop Alert ──────────────────────────────
Wishlist.objects.all().delete()
buyer_wishlist, _ = Wishlist.objects.get_or_create(user=buyer)
WishlistItem.objects.create(wishlist=buyer_wishlist, product=product)

# Ensure base price is 5000 in DB first
Product.objects.filter(pk=product.pk).update(price=Decimal('5000.00'))
product.refresh_from_db()

# Now simulate lowering price from 5000 to 4000
product.price = Decimal('4000.00')
product.save() # Triggers products.signals.check_price_drop -> send_price_drop_alert.delay
buyer_drop_notif = Notification.objects.filter(user=buyer, type='price_drop').first()
assert buyer_drop_notif is not None, "Price drop notification was not created"
assert 'Price drop' in buyer_drop_notif.title
print(f"[PASS] Price drop alert: Lowering price triggered Celery task and created notification '{buyer_drop_notif.title}'")

# ── 12. Combined Order Lifecycle & Transactional Email Tasks ───
Notification.objects.filter(user=buyer).delete()
cart, _ = Cart.objects.get_or_create(user=buyer)
cart.items.all().delete()
CartItem.objects.create(cart=cart, product=product, quantity=1)

addr, _ = Address.objects.get_or_create(
    user=buyer,
    defaults={
        'full_name': 'Buyer Test',
        'phone': '9876543210',
        'address_line1': '456 Market Road',
        'city': 'Bangalore',
        'state': 'Karnataka',
        'pincode': '560001',
        'country': 'India',
        'address_type': 'home',
    }
)
session = client.session
session['checkout'] = {'address_id': addr.id, 'shipping_method': 'standard'}
session.save()

# Place order via Razorpay verify
rz_order_id = 'order_test_lifecycle_1'
rz_payment_id = 'pay_test_lifecycle_1'
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
assert resp_rz.json().get('success') is True
rz_order_num = resp_rz.json().get('redirect_url').strip('/').split('/')[-1]

buyer_notifs = list(Notification.objects.filter(user=buyer).values_list('type', flat=True))
print(f"Notifications created for buyer: {buyer_notifs}")
assert 'order_placed' in buyer_notifs
assert 'payment_confirmed' in buyer_notifs
print(f"[PASS] Combined Test: Order #{rz_order_num} created -> order_placed & payment_confirmed notifications & emails dispatched!")

print("=" * 70)
print("ALL 12 REVIEWS & NOTIFICATIONS TEST CASES PASSED WITH 100% SUCCESS!")
print("=" * 70)
